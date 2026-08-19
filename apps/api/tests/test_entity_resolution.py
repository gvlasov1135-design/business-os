import pytest


@pytest.mark.asyncio
async def test_entity_resolution_candidate_confirm_and_split(client):
    company = (await client.post("/api/v1/companies", json={"name": "ER Co"})).json()
    source = (
        await client.post(
            "/api/v1/sources",
            json={
                "company_id": company["id"],
                "code": "crm-er",
                "name": "CRM ER",
                "source_type": "crm",
            },
        )
    ).json()

    first = await client.post(
        "/api/v1/ingestion/import",
        json={
            "source_id": source["id"],
            "payload": {
                "lead_id": "L-A",
                "created_at": "2026-08-01T10:00:00+03:00",
                "first_contact_at": "2026-08-01T10:10:00+03:00",
                "email": "same@example.com",
                "counterparty_name": "Acme",
            },
        },
    )
    assert first.status_code == 200
    assert first.json()["blocked"] is False

    second = await client.post(
        "/api/v1/ingestion/import",
        json={
            "source_id": source["id"],
            "payload": {
                "lead_id": "L-B",
                "created_at": "2026-08-01T11:00:00+03:00",
                "first_contact_at": "2026-08-01T11:05:00+03:00",
                "email": "same@example.com",
                "counterparty_name": "Acme",
            },
        },
    )
    assert second.status_code == 200

    gate = await client.get(f"/api/v1/data-quality/gate?company_id={company['id']}")
    assert gate.status_code == 200
    assert gate.json()["blocked"] is True
    assert any("Entity Resolution" in r for r in gate.json()["reasons"])

    candidates = (
        await client.get(
            f"/api/v1/resolution/candidates?company_id={company['id']}&status=pending"
        )
    ).json()
    assert candidates
    email_candidate = next(c for c in candidates if c["match_key"] == "email")
    assert email_candidate["requires_confirmation"] is True
    assert email_candidate["blocks_analysis"] is True

    confirmed = await client.post(
        f"/api/v1/resolution/candidates/{email_candidate['id']}/confirm",
        json={"note": "same counterparty"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    entity_id = confirmed.json()["proposed_entity_id"]
    assert entity_id

    # reject remaining soft name candidates so gate opens
    pending = (
        await client.get(
            f"/api/v1/resolution/candidates?company_id={company['id']}&status=pending"
        )
    ).json()
    for item in pending:
        if item["blocks_analysis"]:
            await client.post(f"/api/v1/resolution/candidates/{item['id']}/confirm", json={})
        else:
            await client.post(f"/api/v1/resolution/candidates/{item['id']}/reject", json={})

    gate2 = await client.get(f"/api/v1/data-quality/gate?company_id={company['id']}")
    assert gate2.json()["blocked"] is False

    memberships = (
        await client.get(f"/api/v1/resolution/entities/{entity_id}/memberships")
    ).json()
    assert len(memberships) >= 2

    split = await client.post(
        f"/api/v1/resolution/memberships/{memberships[0]['id']}/split",
        json={"note": "разделить"},
    )
    assert split.status_code == 200
    assert split.json()["id"] != entity_id

    merges = (
        await client.get(f"/api/v1/resolution/merges?company_id={company['id']}")
    ).json()
    assert any(m["event_type"] in ("merge", "split", "auto_link") for m in merges)


@pytest.mark.asyncio
async def test_demo_includes_entity_resolution(client):
    company = (await client.post("/api/v1/companies", json={"name": "ER Demo Co"})).json()
    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200
    extras = demo.json()["extras"]
    assert extras.get("entity_id")
    assert extras.get("resolution_candidate_id")
    assert extras.get("dup_raw_record_id")
    assert demo.json()["extras"]["analysis_blocked"] is False
