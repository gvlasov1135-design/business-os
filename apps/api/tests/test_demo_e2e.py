import pytest


@pytest.mark.asyncio
async def test_demo_run_full_vertical_path(client):
    company = (await client.post("/api/v1/companies", json={"name": "Demo E2E Co"})).json()

    response = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert response.status_code == 200
    data = response.json()

    for key in (
        "company_id",
        "document_id",
        "version_id",
        "statement_id",
        "source_id",
        "raw_record_id",
        "fact_id",
        "check_id",
        "issue_id",
        "knowledge_id",
        "analysis_id",
        "decision_id",
    ):
        assert data[key]

    assert data["company_id"] == company["id"]
    assert data["extras"]["deviation_minutes"] == 32
    assert data["extras"]["severity"] in ("high", "critical")
    assert data["extras"]["severity_from_rule"] is True
    assert data["extras"]["analysis_blocked"] is False
    assert data["recommendation_id"]
    assert data["extras"]["responsible_status"] == "accepted_deviation"
    assert data["extras"]["responsible_knowledge_id"]
    assert data["extras"]["stage_status"] == "confirmed"
    assert "квалификация" in (data["extras"]["stages_skipped"] or [])
    assert data["extras"]["kpi_statement_id"]
    assert data["extras"]["share_kpi_id"]
    assert data["extras"]["share_kpi_actual"] is not None
    assert data["extras"]["proposed_change"]
    assert data["extras"]["proposed_change"]["title"]
    assert data["extras"]["proposed_change"]["status"] == "applied"
    assert data["extras"]["applied_document_version_id"]
    assert data["extras"]["stage_proposed_change"]
    assert data["extras"]["silent_stage_skip_warned"] is True
    assert data["extras"]["justified_stage_skip_ok"] is True
    assert data["extras"]["needs_data_issue_id"]
    assert data["extras"]["needs_data_status"] == "needs_data"
    assert len(data["extras"].get("knowledge_relation_ids") or []) >= 1
    assert data["extras"].get("rule_versions")

    issue = await client.get(f"/api/v1/alignment/issues/{data['issue_id']}")
    assert issue.status_code == 200
    assert issue.json()["status"] == "confirmed"

    knowledge = await client.get(f"/api/v1/knowledge/{data['knowledge_id']}")
    assert knowledge.status_code == 200
    assert knowledge.json()["status"] == "active"

    analysis = await client.get(f"/api/v1/analyses/{data['analysis_id']}")
    assert analysis.status_code == 200
    assert analysis.json()["blocked"] is False
    assert analysis.json()["output"]["blocked"] is False

    decision = await client.get(f"/api/v1/decisions/{data['decision_id']}")
    assert decision.status_code == 200
    assert decision.json()["status"] == "accepted"
    assert decision.json()["result"] is not None
    assert decision.json()["result"]["status"] == "met"
    assert data["extras"]["decision_result_status"] == "met"


@pytest.mark.asyncio
async def test_demo_run_bootstraps_when_no_company(client):
    response = await client.post("/api/v1/demo/run", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"]
    assert data["knowledge_id"]
    assert data["analysis_id"]
    assert data["decision_id"]
