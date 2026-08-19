import pytest


@pytest.mark.asyncio
async def test_independent_agents_debate_and_synthesis(client):
    company = (await client.post("/api/v1/companies", json={"name": "Agents Co"})).json()
    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200
    extras = demo.json()["extras"]
    assert extras.get("agents") == ["executive", "sales", "critic"]
    assert extras.get("disagreement_count", 0) >= 1

    analysis = await client.get(f"/api/v1/analyses/{demo.json()['analysis_id']}")
    assert analysis.status_code == 200
    body = analysis.json()
    output = body["output"]
    assert "executive" in output["agent_opinions"]
    assert "sales" in output["agent_opinions"]
    assert output["agent_opinions"]["executive"]["decision_dna"]["bias"] == "confirm_before_act"
    assert output["agent_opinions"]["sales"]["decision_dna"]["bias"] == "operational_fix_now"
    # независимые рекомендации различаются
    exec_title = output["agent_opinions"]["executive"]["recommendations"][0]["title"]
    sales_title = output["agent_opinions"]["sales"]["recommendations"][0]["title"]
    assert exec_title != sales_title
    assert output["disagreements"]
    assert output["synthesis"]["method"] == "debate_then_merge"
    assert "critic" in output
    assert any("разноглас" in (r.get("title") or "").lower() or "Разноглас" in (r.get("title") or "") for r in output["recommendations"]) or any(
        d.get("topic") == "recommendation_approach" for d in output["disagreements"]
    )
