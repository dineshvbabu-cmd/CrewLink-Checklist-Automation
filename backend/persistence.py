from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Iterable, Iterator, Optional
from urllib.parse import urlparse

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - optional locally when SQLite is used.
    psycopg = None
    dict_row = None


STATE_KEYS = (
    "vessel",
    "crew",
    "documents",
    "confirmation",
    "audit_logs",
    "self_service_links",
    "latest_link_by_crew",
    "learning_feedback",
)

EMPTY_STATE_DEFAULTS = {
    "vessel": {},
    "crew": [],
    "documents": {},
    "confirmation": {},
    "audit_logs": {},
    "self_service_links": {},
    "latest_link_by_crew": {},
    "learning_feedback": {},
}

PBKDF2_ITERATIONS = 120_000


def utc_iso_now() -> str:
    return datetime.now(UTC).isoformat()


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    # psycopg3 requires the postgresql:// scheme; Railway often provides postgres://
    if url.lower().startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def using_postgres() -> bool:
    return database_url().lower().startswith("postgresql://")


def _redacted_database_url() -> str:
    parsed = urlparse(database_url())
    if not parsed.scheme:
        return ""
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    if parsed.username:
        netloc = f"{parsed.username}:***@{netloc}"
    return parsed._replace(netloc=netloc).geturl()


def data_dir() -> str:
    root = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(__file__), "storage")
    os.makedirs(root, exist_ok=True)
    return root


def uploads_dir() -> str:
    path = os.path.join(data_dir(), "uploads")
    os.makedirs(path, exist_ok=True)
    return path


def db_path() -> str:
    if using_postgres():
        return _redacted_database_url()
    return os.path.join(data_dir(), "crewlink.db")


def _sql(query: str) -> str:
    if not using_postgres():
        return query
    return query.replace("?", "%s")


@contextmanager
def connect() -> Iterator[Any]:
    if using_postgres():
        if psycopg is None:
            raise RuntimeError("psycopg is required when DATABASE_URL points to PostgreSQL.")
        connection = psycopg.connect(database_url(), row_factory=dict_row, connect_timeout=10)
    else:
        connection = sqlite3.connect(db_path(), check_same_thread=False)
        connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _execute(connection: Any, query: str, params: tuple[Any, ...] = ()) -> Any:
    return connection.execute(_sql(query), params)


def _json_dump(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _json_load(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt, PBKDF2_ITERATIONS)
    return f"{base64.b64encode(actual_salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_b64, digest_b64 = stored_hash.split("$", 1)
    except ValueError:
        return False

    salt = base64.b64decode(salt_b64.encode())
    expected = base64.b64decode(digest_b64.encode())
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(expected, actual)


def init_database(seed_state: Dict[str, Any], seed_users: Iterable[Dict[str, str]]) -> None:
    with connect() as connection:
        _execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS state_store (
                store_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """,
        )
        _execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
            """,
        )
        _execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """,
        )
        _execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS attachments (
                file_id TEXT PRIMARY KEY,
                crew_id TEXT NOT NULL,
                sr_no INTEGER NOT NULL,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                content_type TEXT NOT NULL,
                uploaded_by TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            )
            """,
        )

        existing_keys = {
            row["store_key"]
            for row in _execute(connection, "SELECT store_key FROM state_store").fetchall()
        }
        if not existing_keys:
            for key, payload in seed_state.items():
                _execute(
                    connection,
                    "INSERT INTO state_store (store_key, payload) VALUES (?, ?)",
                    (key, _json_dump(payload)),
                )

        existing_users = {
            row["username"]
            for row in _execute(connection, "SELECT username FROM users").fetchall()
        }
        for user in seed_users:
            if user["username"] in existing_users:
                continue
            _execute(
                connection,
                """
                INSERT INTO users (user_id, username, full_name, role, password_hash, active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (
                    user["user_id"],
                    user["username"],
                    user["full_name"],
                    user["role"],
                    hash_password(user["password"]),
                ),
            )


def load_state() -> Dict[str, Any]:
    with connect() as connection:
        rows = _execute(connection, "SELECT store_key, payload FROM state_store").fetchall()
    payloads = {row["store_key"]: _json_load(row["payload"], None) for row in rows}
    return {key: payloads.get(key, EMPTY_STATE_DEFAULTS[key]) for key in STATE_KEYS}


def save_state(state: Dict[str, Any]) -> None:
    with connect() as connection:
        for key in STATE_KEYS:
            _execute(
                connection,
                """
                INSERT INTO state_store (store_key, payload)
                VALUES (?, ?)
                ON CONFLICT(store_key) DO UPDATE SET payload = excluded.payload
                """,
                (key, _json_dump(state[key])),
            )


def reset_state(seed_state: Dict[str, Any]) -> None:
    with connect() as connection:
        _execute(connection, "DELETE FROM state_store")
        _execute(connection, "DELETE FROM attachments")
        _execute(connection, "DELETE FROM sessions")
        for key, payload in seed_state.items():
            _execute(
                connection,
                "INSERT INTO state_store (store_key, payload) VALUES (?, ?)",
                (key, _json_dump(payload)),
            )

    for entry in os.scandir(uploads_dir()):
        if entry.is_file():
            os.remove(entry.path)


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    with connect() as connection:
        row = _execute(
            connection,
            """
            SELECT user_id, username, full_name, role, password_hash, active
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
    if not row or not row["active"]:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return {
        "id": row["user_id"],
        "username": row["username"],
        "fullName": row["full_name"],
        "role": row["role"],
    }


def create_session(user_id: str, duration_hours: int = 12) -> str:
    token = secrets.token_urlsafe(24)
    created_at = utc_iso_now()
    expires_at = (datetime.now(UTC) + timedelta(hours=duration_hours)).isoformat()
    with connect() as connection:
        _execute(
            connection,
            """
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, created_at, expires_at),
        )
    return token


def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    with connect() as connection:
        row = _execute(
            connection,
            """
            SELECT sessions.token, sessions.expires_at, users.user_id, users.username, users.full_name, users.role, users.active
            FROM sessions
            JOIN users ON users.user_id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at < datetime.now(UTC):
            _execute(connection, "DELETE FROM sessions WHERE token = ?", (token,))
            return None
        if not row["active"]:
            return None
        return {
            "id": row["user_id"],
            "username": row["username"],
            "fullName": row["full_name"],
            "role": row["role"],
            "token": token,
        }


def delete_session(token: str) -> None:
    with connect() as connection:
        _execute(connection, "DELETE FROM sessions WHERE token = ?", (token,))


def save_attachment(
    crew_id: str,
    sr_no: int,
    original_name: str,
    content_type: str,
    content: bytes,
    uploaded_by: str,
) -> Dict[str, Any]:
    file_id = secrets.token_hex(8)
    extension = os.path.splitext(original_name)[1] or ".bin"
    stored_name = f"{file_id}{extension}"
    absolute_path = os.path.join(uploads_dir(), stored_name)
    with open(absolute_path, "wb") as file_handle:
        file_handle.write(content)

    record = {
        "fileId": file_id,
        "crewId": crew_id,
        "srNo": sr_no,
        "originalName": original_name,
        "storedName": stored_name,
        "contentType": content_type or "application/octet-stream",
        "uploadedBy": uploaded_by,
        "uploadedAt": utc_iso_now(),
        "absolutePath": absolute_path,
    }
    with connect() as connection:
        _execute(
            connection,
            """
            INSERT INTO attachments (
                file_id, crew_id, sr_no, original_name, stored_name, content_type, uploaded_by, uploaded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["fileId"],
                record["crewId"],
                record["srNo"],
                record["originalName"],
                record["storedName"],
                record["contentType"],
                record["uploadedBy"],
                record["uploadedAt"],
            ),
        )
    return record


def get_attachment(file_id: str) -> Optional[Dict[str, Any]]:
    with connect() as connection:
        row = _execute(
            connection,
            """
            SELECT file_id, crew_id, sr_no, original_name, stored_name, content_type, uploaded_by, uploaded_at
            FROM attachments
            WHERE file_id = ?
            """,
            (file_id,),
        ).fetchone()
    if not row:
        return None
    absolute_path = os.path.join(uploads_dir(), row["stored_name"])
    if not os.path.exists(absolute_path):
        return None
    return {
        "fileId": row["file_id"],
        "crewId": row["crew_id"],
        "srNo": row["sr_no"],
        "originalName": row["original_name"],
        "storedName": row["stored_name"],
        "contentType": row["content_type"],
        "uploadedBy": row["uploaded_by"],
        "uploadedAt": row["uploaded_at"],
        "absolutePath": absolute_path,
    }
