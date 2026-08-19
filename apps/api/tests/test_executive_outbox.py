import pytest


@pytest.mark.asyncio
async def test_executive_readiness_and_outbox(client):
    company = (await client.post("/api/v1/companies", json={"name": "Exec Co"})).json()
    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200

    ready = await client.get(f"/api/v1/executive/readiness?company_id={company['id']}")
    assert ready.status_code == 200
    body = ready.json()
    assert body["analysis_ready"] is True
    assert body["completeness"]["score"] > 0.5
    assert body["trust_index"]["score"] > 0
    assert body["alignment_score"]["score"] > 0
    assert body["document_health"]["score"] > 0
    assert body["kpi_health"]["score"] > 0
    assert body["counts"]["facts"] >= 1
    assert body["counts"]["knowledge"] >= 1
    assert body["latest_analysis_id"]
    assert body["evidence_preview"]
    assert body["sla_axes"]["deadline"] >= 1
    assert body["sla_axes"]["responsible"] >= 1
    assert body["sla_axes"]["stages"] >= 1
    assert body["sla_axes"]["proposed_changes"] >= 1
    assert any(e.get("type") == "sla_axis" for e in body["evidence_preview"])

    events = await client.get(
        f"/api/v1/outbox/events?company_id={company['id']}&status=pending"
    )
    assert events.status_code == 200
    pending = events.json()
    assert any(e["event_type"] == "analysis.ready" for e in pending)
    assert any(e["event_type"] == "decision.created" for e in pending)

    first = pending[0]
    published = await client.post(f"/api/v1/outbox/events/{first['id']}/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    left = await client.get(
        f"/api/v1/outbox/events?company_id={company['id']}&status=pending"
    )
    assert all(e["id"] != first["id"] for e in left.json())
