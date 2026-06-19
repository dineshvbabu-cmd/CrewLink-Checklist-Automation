import os

from fastapi.testclient import TestClient

import main
from main import app, reset_demo_state


client = TestClient(app)


def setup_function():
    os.environ["PORTAL_LIVE_CHECKS"] = "0"
    reset_demo_state()


def auth_headers(username: str = "admin", password: str = "CrewlinkAdmin!23") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_healthcheck_is_public():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_ai_check_returns_matrix_driven_summary():
    response = client.post("/api/ai/check/c002", headers=auth_headers("rc", "CrewlinkRC!23"))
    assert response.status_code == 200
    data = response.json()
    assert data["overallStatus"] == "red"
    assert data["summary"]["missing"] == 4
    assert "Flag CDC I/10 (Marshall Islands)" in data["matrixDocuments"]


def test_batch_portal_verification_resolves_pending_documents():
    headers = auth_headers("ops", "CrewlinkOps!23")
    before = client.get("/api/crew/c003/documents", headers=headers).json()
    assert before["summary"]["pendingVerification"] == 4
    assert before["summary"]["portalPending"] == 4

    batch = client.post("/api/crew/c003/verify-portal-batch", headers=headers)
    assert batch.status_code == 200
    assert batch.json()["manualCount"] == 1
    assert batch.json()["failedCount"] == 3

    after = client.get("/api/crew/c003/documents", headers=headers).json()
    assert after["summary"]["pendingVerification"] == 4
    assert after["summary"]["portalPending"] == 4

    ai = client.post("/api/ai/check/c003", headers=headers).json()
    assert ai["overallStatus"] == "yellow"


def test_verify_portal_returns_official_route_details():
    response = client.post(
        "/api/crew/c003/verify-portal",
        json={
            "docName": "Certificate of Competency (Chief Officer)",
            "docNo": "IND-COC-CO-2018",
            "issueAuthority": "India",
        },
        headers=auth_headers("ops", "CrewlinkOps!23"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["verificationMode"] == "auto"
    assert data["portal"] == "DG Shipping India"
    assert "DG Shipping" in data["message"]
    assert data["autoCapable"] is True
    assert data["eligible"] is True


def test_documents_payload_includes_portal_route_metadata():
    response = client.get("/api/crew/c003/documents", headers=auth_headers("ops", "CrewlinkOps!23"))

    assert response.status_code == 200
    competency = next(
        item
        for section in response.json()["sections"]
        for item in section["items"]
        if item["name"] == "Certificate of Competency (Chief Officer)"
    )
    assert competency["portalRoute"]["portal"] == "DG Shipping India"
    assert competency["portalRoute"]["autoCapable"] is True

    company_form = next(
        item
        for section in response.json()["sections"]
        for item in section["items"]
        if item["name"] == "Interview Sheet (FP01D)"
    )
    assert company_form["portalRoute"]["verificationMode"] == "review"
    assert company_form["portalRoute"]["eligible"] is False


def test_verify_portal_applies_automated_result(monkeypatch):
    os.environ["PORTAL_LIVE_CHECKS"] = "1"

    async def fake_official_check(route, crew_id, doc_name, doc_no):
        return {
            "docName": doc_name,
            "verified": True,
            "message": "Verified automatically through a mocked official portal.",
            "portal": route["portal"],
            "portalLabel": route["portalLabel"],
            "portalUrl": route["portalUrl"],
            "verificationMode": "auto",
            "requiredInputs": route["requiredInputs"],
            "recommendedAiStatus": "green",
            "checklistStatus": "good",
        }

    monkeypatch.setattr(main, "_run_official_portal_check", fake_official_check)

    response = client.post(
        "/api/crew/c003/verify-portal",
        json={
            "docName": "Certificate of Competency (Chief Officer)",
            "docNo": "IND-COC-CO-2018",
            "issueAuthority": "India",
        },
        headers=auth_headers("ops", "CrewlinkOps!23"),
    )
    assert response.status_code == 200
    assert response.json()["verified"] is True
    assert response.json()["recommendedAiStatus"] == "green"

    after = client.get("/api/crew/c003/documents", headers=auth_headers("ops", "CrewlinkOps!23")).json()
    competency = next(
        item
        for section in after["sections"]
        for item in section["items"]
        if item["name"] == "Certificate of Competency (Chief Officer)"
    )
    assert competency["portalVerified"] is True
    assert competency["aiStatus"] == "green"
    assert "mocked official portal" in competency["systemNote"]


def test_remark_and_override_are_logged():
    rc_headers = auth_headers("rc", "CrewlinkRC!23")
    remark = client.post(
        "/api/crew/c002/documents/6/remark",
        json={"remark": "OPS approved temporary handling", "actor": "Shital Patil"},
        headers=rc_headers,
    )
    assert remark.status_code == 200
    assert remark.json()["item"]["remark"] == "OPS approved temporary handling"

    ops_headers = auth_headers("ops", "CrewlinkOps!23")
    override = client.post(
        "/api/crew/c002/documents/6/override",
        json={"status": "green", "reason": "Temporary flag waiver approved", "actor": "Shital Patil"},
        headers=ops_headers,
    )
    assert override.status_code == 200
    assert override.json()["item"]["overrideStatus"] == "green"
    assert override.json()["item"]["overrideReason"] == "Temporary flag waiver approved"
    assert override.json()["item"]["missing"] is False
    assert override.json()["item"]["portalVerified"] is False

    audit = client.get("/api/crew/c002/audit-log", headers=ops_headers).json()
    assert any(entry["action"] == "override" for entry in audit)


def test_documents_payload_exposes_distinct_checklist_and_portal_statuses():
    response = client.get("/api/crew/c003/documents", headers=auth_headers("ops", "CrewlinkOps!23"))

    assert response.status_code == 200
    competency = next(
        item
        for section in response.json()["sections"]
        for item in section["items"]
        if item["name"] == "Certificate of Competency (Chief Officer)"
    )
    interview_sheet = next(
        item
        for section in response.json()["sections"]
        for item in section["items"]
        if item["name"] == "Interview Sheet (FP01D)"
    )

    assert competency["checklistStatus"] == "good"
    assert competency["portalStatus"] == "pending"
    assert interview_sheet["checklistStatus"] == "good"
    assert interview_sheet["portalStatus"] == "not_applicable"


def test_self_service_submission_updates_confirmation():
    sent = client.post(
        "/api/crew/c002/self-service/send",
        json={"sentBy": "RC Team"},
        headers={
            **auth_headers("rc", "CrewlinkRC!23"),
            "x-forwarded-proto": "https",
            "x-forwarded-host": "crewlink-checklist-automation-production.up.railway.app",
        },
    )
    assert sent.status_code == 200
    token = sent.json()["token"]
    assert sent.json()["url"] == (
        "https://crewlink-checklist-automation-production.up.railway.app"
        f"/approval/{token}"
    )

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

    confirmation = client.get(
        "/api/crew/c002/confirmation",
        headers=auth_headers("ops", "CrewlinkOps!23"),
    ).json()
    assert confirmation[0]["verifyCrew"] is True
    assert confirmation[1]["seafarerRemark"] == "Need updated flag document"


def test_export_pdf_returns_pdf_document():
    response = client.get("/api/crew/c001/export-checklist", headers=auth_headers())
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 500


def test_crewlink_checklist_item_marks_ops_review_as_pending():
    item = main._crewlink_item_from_checklist(
        1,
        "flag",
        {
            "docname": "Flag CDC I/10",
            "docNo": "MH 1204609",
            "type": "I/10",
            "issueDate": "2026-05-28T00:00:00",
            "expiryDate": "2031-05-27T00:00:00",
            "filePath": "https://example.com/flag-cdc.pdf",
            "remark1": "To be review by OPS",
            "firstVerification": 1185,
            "secondVerification": 1185,
        },
    )

    assert item["required"] is True
    assert item["missing"] is False
    assert item["aiStatus"] == "yellow"
    assert item["verifiedOps"] is False
    assert item["portalVerified"] is False
    assert "review by OPS" in item["remark"]


def test_crewlink_checklist_item_treats_na_placeholder_as_missing():
    item = main._crewlink_item_from_checklist(
        5,
        "medical",
        {
            "docname": "Psychometric Test (PF-16)",
            "docNo": "NA",
            "type": "",
            "issueDate": "1900-01-01T00:00:00",
            "expiryDate": "1900-01-01T00:00:00",
            "filePath": "",
            "remark1": "NA",
        },
    )

    assert item["required"] is True
    assert item["missing"] is True
    assert item["aiStatus"] == "red"


def test_crewlink_checklist_item_marks_missing_mandatory_course_red():
    item = main._crewlink_item_from_checklist(
        12,
        "course",
        {
            "docname": "M : FRAMO Pumps Training",
            "docNo": "",
            "type": "Vessel Specific",
            "issueDate": None,
            "expiryDate": None,
            "filePath": None,
            "remark1": "Will check",
            "level": "Mandatory",
        },
    )

    assert item["required"] is True
    assert item["missing"] is True
    assert item["aiStatus"] == "red"


def test_indian_master_fg_document_routes_to_dg_shipping_coc_checker():
    route = main._resolve_portal_route("c003", "Master F.G. II/2", "IF008168", "India")

    assert route["portal"] == "DG Shipping India"
    assert route["strategy"] == "dg_coc"
    assert route["eligible"] is True


def test_psychometric_document_does_not_route_to_watchkeeping_checker():
    route = main._resolve_portal_route("c003", "Psychometric Test (PF-16)", "", "India")

    assert route["portal"] == "Crewlink AI"
    assert route["eligible"] is False


def test_verify_portal_review_only_document_stays_good():
    response = client.post(
        "/api/crew/c003/verify-portal",
        json={
            "docName": "Interview Sheet (FP01D)",
            "docNo": "FP01D-A0806-2026",
            "issueAuthority": "Company",
        },
        headers=auth_headers("ops", "CrewlinkOps!23"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["verificationMode"] == "review"
    assert data["eligible"] is False
    assert data["recommendedAiStatus"] == "green"

    after = client.get("/api/crew/c003/documents", headers=auth_headers("ops", "CrewlinkOps!23")).json()
    interview_sheet = next(
        item
        for section in after["sections"]
        for item in section["items"]
        if item["name"] == "Interview Sheet (FP01D)"
    )
    assert interview_sheet["aiStatus"] == "green"
    assert "supported public verification portal" in interview_sheet["systemNote"]
