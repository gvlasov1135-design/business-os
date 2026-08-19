import pytest


@pytest.mark.asyncio
async def test_data_doctor_explains_without_unblocking(client):
    company = (await client.post("/api/v1/companies", json={"name": "DQ Co"})).json()
    source = (
        await client.post(
            "/api/v1/sources",
            json={
                "company_id": company["id"],
                "code": "crm-dq",
                "name": "CRM DQ",
                "source_type": "crm",
            },
        )
    ).json()
    bad = await client.post(
        "/api/v1/ingestion/import",
        json={
            "source_id": source["id"],
            "payload": {
                "lead_id": "L-BAD",
                "created_at": "2026-08-01T10:00:00+03:00",
                "first_contact_at": "2026-08-01T09:00:00+03:00",
            },
        },
    )
    assert bad.status_code == 200
    assert bad.json()["blocked"] is True
    issues = (
        await client.get(f"/api/v1/data-quality/issues?company_id={company['id']}")
    ).json()
    assert issues
    issue_id = issues[0]["id"]

    explained = await client.post(f"/api/v1/data-quality/issues/{issue_id}/explain")
    assert explained.status_code == 200
    body = explained.json()
    assert body["read_only"] is True
    assert body["can_unblock_analysis"] is False
    assert body["explanation"]

    gate = await client.get(f"/api/v1/data-quality/gate?company_id={company['id']}")
    assert gate.status_code == 200
    assert gate.json()["blocked"] is True


@pytest.mark.asyncio
async def test_knowledge_search_and_relation(client):
    # seed via demo path pieces
    company = (await client.post("/api/v1/companies", json={"name": "Know Co"})).json()
    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200
    knowledge_id = demo.json()["knowledge_id"]

    search = await client.get(
        f"/api/v1/knowledge/search?company_id={company['id']}&q=контакта"
    )
    assert search.status_code == 200
    assert any(item["id"] == knowledge_id for item in search.json()["results"])

    # create second knowledge via another confirm path is heavy; relate record to itself forbidden
    bad = await client.post(
        "/api/v1/knowledge/relations",
        json={
            "company_id": company["id"],
            "from_record_id": knowledge_id,
            "to_record_id": knowledge_id,
            "relation_type": "relates_to",
        },
    )
    assert bad.status_code == 400

    # list relations empty ok
    listed = await client.get(f"/api/v1/knowledge/relations?company_id={company['id']}")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1


@pytest.mark.asyncio
async def test_analysis_uses_llm_gateway_context(client):
    company = (await client.post("/api/v1/companies", json={"name": "AI Co"})).json()
    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200
    analysis_id = demo.json()["analysis_id"]
    analysis = await client.get(f"/api/v1/analyses/{analysis_id}")
    assert analysis.status_code == 200
    body = analysis.json()
    assert body["blocked"] is False
    assert body["context_snapshot"]["access_policy"]["raw_crm_allowed"] is False
    assert "critic" in (body.get("output") or {})
    assert "agent_opinions" in (body.get("output") or {})
    assert "sales" in body["output"]["agent_opinions"]
