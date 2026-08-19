import pytest

DEMO_PAYLOAD = {
    "lead_id": "L-1001",
    "created_at": "2026-08-01T09:00:00+03:00",
    "first_contact_at": "2026-08-01T09:47:00+03:00",
    "assigned_position": "Sales Manager",
    "actual_actor": "employee-17",
}


async def _bootstrap_company_and_source(client):
    company = (await client.post("/api/v1/companies", json={"name": "Ingest Co"})).json()
    source = (
        await client.post(
            "/api/v1/sources",
            json={
                "company_id": company["id"],
                "code": "crm-demo",
                "name": "Demo CRM",
                "source_type": "crm",
                "freshness_hours": 24,
            },
        )
    ).json()
    return company, source


@pytest.mark.asyncio
async def test_import_demo_crm_event_creates_fact_minutes_47(client):
    company, source = await _bootstrap_company_and_source(client)

    response = await client.post(
        "/api/v1/ingestion/import",
        json={"source_id": source["id"], "payload": DEMO_PAYLOAD},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["duplicate"] is False
    assert data["blocked"] is False
    assert data["raw_record"]["status"] == "normalized"
    assert data["fact"]["predicate"] == "actual_first_contact_minutes"
    assert data["fact"]["subject"] == "L-1001"
    assert data["fact"]["value_structured"]["minutes"] == 47
    assert float(data["fact"]["value_text"]) == 47
    assert data["fact"]["lineage"]["external_id"] == "L-1001"
    assert data["fact"]["lineage"]["source_id"] == source["id"]
    assert data["fact"]["lineage"]["raw_record_id"] == data["raw_record"]["id"]

    facts = await client.get("/api/v1/facts", params={"company_id": company["id"]})
    assert facts.status_code == 200
    assert len(facts.json()) == 1

    raw = await client.get(f"/api/v1/raw-records/{data['raw_record']['id']}")
    assert raw.status_code == 200
    assert raw.json()["external_id"] == "L-1001"


@pytest.mark.asyncio
async def test_reimport_same_payload_is_idempotent(client):
    _, source = await _bootstrap_company_and_source(client)

    first = await client.post(
        "/api/v1/ingestion/import",
        json={"source_id": source["id"], "payload": DEMO_PAYLOAD},
    )
    assert first.status_code == 200
    first_data = first.json()

    second = await client.post(
        "/api/v1/ingestion/import",
        json={"source_id": source["id"], "payload": DEMO_PAYLOAD},
    )
    assert second.status_code == 200
    second_data = second.json()
    assert second_data["duplicate"] is True
    assert second_data["raw_record"]["id"] == first_data["raw_record"]["id"]
    assert second_data["fact"]["id"] == first_data["fact"]["id"]

    facts = await client.get("/api/v1/facts", params={"company_id": source["company_id"]})
    assert len(facts.json()) == 1


@pytest.mark.asyncio
async def test_missing_first_contact_at_quarantines_and_blocks(client):
    company, source = await _bootstrap_company_and_source(client)
    bad_payload = {
        "lead_id": "L-2002",
        "created_at": "2026-08-01T09:00:00+03:00",
        "assigned_position": "Sales Manager",
        "actual_actor": "employee-17",
    }

    response = await client.post(
        "/api/v1/ingestion/import",
        json={"source_id": source["id"], "payload": bad_payload},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["blocked"] is True
    assert data["fact"] is None
    assert data["raw_record"]["status"] == "quarantine"
    assert any(issue["code"] == "missing_first_contact_at" for issue in data["issues"])

    issues = await client.get(
        "/api/v1/data-quality/issues",
        params={"company_id": company["id"], "status": "open"},
    )
    assert issues.status_code == 200
    assert any(item["code"] == "missing_first_contact_at" for item in issues.json())

    gate = await client.get("/api/v1/data-quality/gate", params={"company_id": company["id"]})
    assert gate.status_code == 200
    assert gate.json()["blocked"] is True
    assert gate.json()["reasons"]

    facts = await client.get("/api/v1/facts", params={"company_id": company["id"]})
    assert facts.json() == []


@pytest.mark.asyncio
async def test_stale_source_blocks_import(client):
    company, source = await _bootstrap_company_and_source(client)

    status_resp = await client.post(
        f"/api/v1/sources/{source['id']}/status",
        json={"status": "stale"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "stale"

    response = await client.post(
        "/api/v1/ingestion/import",
        json={"source_id": source["id"], "payload": DEMO_PAYLOAD},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["blocked"] is True
    assert data["fact"] is None
    assert data["raw_record"]["status"] == "quarantine"
    assert any(issue["code"] == "source_stale" for issue in data["issues"])

    facts = await client.get("/api/v1/facts", params={"company_id": company["id"]})
    assert facts.json() == []
