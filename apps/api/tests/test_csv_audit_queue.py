import pytest


@pytest.mark.asyncio
async def test_csv_import_creates_fact(client):
    company = (await client.post("/api/v1/companies", json={"name": "CSV Co"})).json()
    source = (
        await client.post(
            "/api/v1/sources",
            json={
                "company_id": company["id"],
                "code": "crm-csv",
                "name": "CSV CRM",
                "source_type": "csv",
                "freshness_hours": 24,
            },
        )
    ).json()

    csv_body = (
        "lead_id,created_at,first_contact_at,assigned_position,actual_actor\n"
        "L-CSV-1,2026-08-01T09:00:00+03:00,2026-08-01T09:47:00+03:00,Sales Manager,employee-17\n"
    ).encode("utf-8")

    response = await client.post(
        "/api/v1/ingestion/import-csv",
        data={"source_id": source["id"]},
        files={"file": ("leads.csv", csv_body, "text/csv")},
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["duplicate"] is False
    assert rows[0]["blocked"] is False
    assert rows[0]["fact"]["subject"] == "L-CSV-1"
    assert float(rows[0]["fact"]["value_structured"]["minutes"]) == 47.0


@pytest.mark.asyncio
async def test_audit_lists_events_after_bootstrap(client):
    await client.post("/api/v1/identity/bootstrap")
    response = await client.get("/api/v1/audit/events?limit=20")
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    assert any(item["action"].startswith("user.") or item["action"].startswith("company.") for item in events)


@pytest.mark.asyncio
async def test_extract_async_enqueues_job(client, monkeypatch):
    company = (await client.post("/api/v1/companies", json={"name": "Queue Co"})).json()
    upload = await client.post(
        "/api/v1/documents",
        data={"company_id": company["id"], "title": "Policy"},
        files={"file": ("policy.pdf", b"%PDF-1.4 deadline 15 minutes", "application/pdf")},
    )
    assert upload.status_code == 201
    document = upload.json()["document"]
    version_id = document["versions"][0]["id"]

    captured: dict[str, str] = {}

    def fake_enqueue(*, document_id: str, version_id: str, settings=None):  # noqa: ANN001
        captured["document_id"] = document_id
        captured["version_id"] = version_id
        return "job-123"

    monkeypatch.setattr("modules.documents.router.enqueue_extraction", fake_enqueue)

    response = await client.post(
        f"/api/v1/documents/{document['id']}/versions/{version_id}/extract-async"
    )
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] == "job-123"
    assert body["type"] == "extract_document"
    assert captured["document_id"] == document["id"]
