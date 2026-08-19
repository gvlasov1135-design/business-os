"""P1 AI: redaction + versioned DNA/prompts."""

import pytest

from common.redaction import REDACTED, redact_context


def test_redact_context_masks_sensitive_fields():
    ctx = {
        "facts": [
            {
                "subject": "L-1001",
                "value_structured": {
                    "minutes": 47,
                    "email": "lead@example.com",
                    "actual_actor": "employee-17",
                },
            }
        ],
        "nested": {"password": "secret", "ok": 1},
    }
    out = redact_context(ctx)
    assert out["facts"][0]["value_structured"]["minutes"] == 47
    assert out["facts"][0]["value_structured"]["email"] == REDACTED
    assert out["facts"][0]["value_structured"]["actual_actor"] == REDACTED
    assert out["nested"]["password"] == REDACTED
    assert out["nested"]["ok"] == 1
    assert ctx["nested"]["password"] == "secret"


def test_gateway_redacts_before_mock():
    from modules.llm.gateway import AgentProfile, LLMGateway, LLMRequest

    gw = LLMGateway()
    resp = gw.complete(
        LLMRequest(
            agent=AgentProfile.sales,
            prompt="лид L-1001 SLA",
            context={
                "facts": [
                    {
                        "id": "1",
                        "subject": "L-1001",
                        "predicate": "actual_first_contact_minutes",
                        "value_structured": {"minutes": 47, "email": "x@y.z"},
                        "trust_index": 0.7,
                    }
                ],
                "knowledge": [],
                "kpis": [],
                "alignment_issues": {
                    "verified": [],
                    "accepted_deviations": [],
                    "unverified_evidence": [],
                },
            },
        )
    )
    assert "recommendations" in resp.content or resp.content.get("agent") == "sales"


@pytest.mark.asyncio
async def test_analysis_includes_rule_versions(client):
    company = (await client.post("/api/v1/companies", json={"name": "P1 AI Co"})).json()
    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200
    analysis = await client.get(f"/api/v1/analyses/{demo.json()['analysis_id']}")
    assert analysis.status_code == 200
    versions = analysis.json()["output"]["rule_versions"]
    assert versions["prompt_executive"]["rule_code"] == "prompt_executive"
    assert versions["dna_sales"]["rule_version_id"]
    assert demo.json()["extras"].get("job_document_id")
    assert demo.json()["extras"].get("responsible_from_job_description") is True
    assert demo.json()["extras"].get("silent_stage_skip_warned") is True
    assert demo.json()["extras"].get("justified_stage_skip_ok") is True
    assert demo.json()["extras"].get("needs_data_issue_id")
    assert demo.json()["extras"].get("needs_data_status") == "needs_data"
    assert len(demo.json()["extras"].get("knowledge_relation_ids") or []) >= 1
    missing = demo.json()["extras"].get("analysis_missing_data") or []
    assert any("дополнительн" in str(m).lower() or "crm" in str(m).lower() for m in missing)


@pytest.mark.asyncio
async def test_silent_stage_skip_warning(client):
    company = (await client.post("/api/v1/companies", json={"name": "Skip DQ Co"})).json()
    source = (
        await client.post(
            "/api/v1/sources",
            json={
                "company_id": company["id"],
                "code": "crm-skip",
                "name": "CRM Skip",
                "source_type": "crm",
            },
        )
    ).json()
    imported = await client.post(
        "/api/v1/ingestion/import",
        json={
            "source_id": source["id"],
            "payload": {
                "lead_id": "L-SKIP",
                "created_at": "2026-08-01T09:00:00+03:00",
                "first_contact_at": "2026-08-01T09:10:00+03:00",
                "stages_skipped": ["квалификация"],
            },
        },
    )
    assert imported.status_code == 200
    assert imported.json()["fact"] is not None
    assert any(i["code"] == "silent_stage_skip" for i in imported.json()["issues"])
    assert all(i["blocks_analysis"] is False for i in imported.json()["issues"])


@pytest.mark.asyncio
async def test_justified_stage_skip_and_resolve(client):
    company = (await client.post("/api/v1/companies", json={"name": "Justify DQ Co"})).json()
    source = (
        await client.post(
            "/api/v1/sources",
            json={
                "company_id": company["id"],
                "code": "crm-just",
                "name": "CRM Just",
                "source_type": "crm",
            },
        )
    ).json()
    ok = await client.post(
        "/api/v1/ingestion/import",
        json={
            "source_id": source["id"],
            "payload": {
                "lead_id": "L-OK",
                "created_at": "2026-08-01T09:00:00+03:00",
                "first_contact_at": "2026-08-01T09:10:00+03:00",
                "stages_skipped": ["квалификация"],
                "stage_skip_reason": "Повторное обращение",
            },
        },
    )
    assert ok.status_code == 200
    assert not any(i["code"] == "silent_stage_skip" for i in ok.json()["issues"])

    silent = await client.post(
        "/api/v1/ingestion/import",
        json={
            "source_id": source["id"],
            "payload": {
                "lead_id": "L-SILENT",
                "created_at": "2026-08-01T10:00:00+03:00",
                "first_contact_at": "2026-08-01T10:10:00+03:00",
                "stages_skipped": ["квалификация"],
            },
        },
    )
    assert silent.status_code == 200
    issue = next(i for i in silent.json()["issues"] if i["code"] == "silent_stage_skip")
    resolved = await client.post(
        f"/api/v1/data-quality/issues/{issue['id']}/resolve",
        json={"reason": "Квалификация уже в карточке"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    blocking = await client.post(
        "/api/v1/ingestion/import",
        json={
            "source_id": source["id"],
            "payload": {
                "lead_id": "L-BAD",
                "created_at": "2026-08-01T11:00:00+03:00",
                "first_contact_at": "2026-08-01T10:00:00+03:00",
            },
        },
    )
    assert blocking.status_code == 200
    bad_id = blocking.json()["issues"][0]["id"]
    denied = await client.post(
        f"/api/v1/data-quality/issues/{bad_id}/resolve",
        json={"reason": "нельзя"},
    )
    assert denied.status_code == 409


@pytest.mark.asyncio
async def test_needs_data_in_analysis_context(client):
    company = (await client.post("/api/v1/companies", json={"name": "Needs Data Co"})).json()
    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200
    analysis = await client.get(f"/api/v1/analyses/{demo.json()['analysis_id']}")
    assert analysis.status_code == 200
    ctx = analysis.json()["context_snapshot"]
    assert ctx["alignment_issues"]["needs_data"]
    assert ctx["pending_data_requests"]
    assert analysis.json()["blocked"] is False
    assert analysis.json()["output"]["missing_data"]
