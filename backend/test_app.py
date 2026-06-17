from fastapi.testclient import TestClient

from main import app, reset_demo_state


client = TestClient(app)


def setup_function():
    reset_demo_state()


def test_ai_check_returns_matrix_driven_summary():
    response = client.post("/api/ai/check/c002")
    assert response.status_code == 200
    data = response.json()
    assert data["overallStatus"] == "red"
    assert data["summary"]["missing"] == 4
    assert "Flag CDC I/10 (Marshall Islands)" in data["matrixDocuments"]


def test_batch_portal_verification_resolves_pending_documents():
    before = client.get("/api/crew/c003/documents").json()
    assert before["summary"]["pendingVerification"] == 3

    batch = client.post("/api/crew/c003/verify-portal-batch")
    assert batch.status_code == 200
    assert batch.json()["verifiedCount"] == 3

    after = client.get("/api/crew/c003/documents").json()
    assert after["summary"]["pendingVerification"] == 0

    ai = client.post("/api/ai/check/c003").json()
    assert ai["overallStatus"] == "green"


def test_remark_and_override_are_logged():
    remark = client.post(
        "/api/crew/c002/documents/6/remark",
        json={"remark": "OPS approved temporary handling", "actor": "Shital Patil"},
    )
    assert remark.status_code == 200
    assert remark.json()["item"]["remark"] == "OPS approved temporary handling"

    override = client.post(
        "/api/crew/c002/documents/6/override",
        json={"status": "green", "reason": "Temporary flag waiver approved", "actor": "Shital Patil"},
    )
    assert override.status_code == 200
    assert override.json()["item"]["aiStatus"] == "green"

    audit = client.get("/api/crew/c002/audit-log").json()
    assert any(entry["action"] == "override" for entry in audit)


def test_self_service_submission_updates_confirmation():
    sent = client.post("/api/crew/c002/self-service/send", json={"sentBy": "RC Team"})
    assert sent.status_code == 200
    token = sent.json()["token"]

    packet = client.get(f"/api/self-service/{token}")
    assert packet.status_code == 200
    assert packet.json()["status"] == "sent"

    submit = client.post(
        f"/api/self-service/{token}/submit",
        json={
            "seafarerName": "Francis Zamani Duniya",
            "items": [
                {"srNo": 1, "verifyCrew": True, "seafarerRemark": "Received"},
                {"srNo": 2, "verifyCrew": False, "seafarerRemark": "Need updated flag document"},
            ],
        },
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "submitted"

    confirmation = client.get("/api/crew/c002/confirmation").json()
    assert confirmation[0]["verifyCrew"] is True
    assert confirmation[1]["seafarerRemark"] == "Need updated flag document"


def test_export_pdf_returns_pdf_document():
    response = client.get("/api/crew/c001/export-checklist")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 500
