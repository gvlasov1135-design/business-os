import io

import pytest

DEMO_PAYLOAD = {
    "lead_id": "L-1001",
    "created_at": "2026-08-01T09:00:00+03:00",
    "first_contact_at": "2026-08-01T09:47:00+03:00",
    "assigned_position": "Sales Manager",
    "actual_actor": "employee-17",
}

POLICY_BYTES = (
    "Менеджер по продажам обязан связаться с новым лидом "
    "не позднее 15 минут после его создания."
).encode("utf-8")


async def _bootstrap_company(client):
    company = (await client.post("/api/v1/companies", json={"name": "Align Co"})).json()
    return company


async def _upload_extract_statement(client, company_id: str, *, confirm: bool):
    upload = await client.post(
        "/api/v1/documents",
        data={"company_id": company_id, "title": "Sales Policy"},
        files={"file": ("policy.pdf", io.BytesIO(POLICY_BYTES), "application/pdf")},
    )
    assert upload.status_code == 201
    document = upload.json()["document"]
    document_id = document["id"]
    version_id = document["versions"][0]["id"]

    extracted = await client.post(f"/api/v1/documents/{document_id}/versions/{version_id}/extract")
    assert extracted.status_code == 201
    statement = extracted.json()["statement"]
    if confirm:
        confirmed = await client.post(f"/api/v1/statements/{statement['id']}/confirm")
        assert confirmed.status_code == 200
        statement = confirmed.json()
    return document_id, statement


async def _create_source_and_fact(client, company_id: str, **payload_extra):
    import uuid as _uuid

    source = (
        await client.post(
            "/api/v1/sources",
            json={
                "company_id": company_id,
                "code": f"crm-align-{_uuid.uuid4().hex[:6]}",
                "name": "Align CRM",
                "source_type": "crm",
                "freshness_hours": 24,
            },
        )
    ).json()
    payload = {**DEMO_PAYLOAD, **payload_extra}
    imported = await client.post(
        "/api/v1/ingestion/import",
        json={"source_id": source["id"], "payload": payload},
    )
    assert imported.status_code == 200
    data = imported.json()
    assert data["fact"] is not None
    return source, data["fact"]


@pytest.mark.asyncio
async def test_unconfirmed_statement_cannot_run_alignment(client):
    company = await _bootstrap_company(client)
    _, statement = await _upload_extract_statement(client, company["id"], confirm=False)
    _, fact = await _create_source_and_fact(client, company["id"])

    response = await client.post(
        "/api/v1/alignment/checks",
        json={
            "company_id": company["id"],
            "statement_id": statement["id"],
            "fact_id": fact["id"],
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "statement_unconfirmed"

    knowledge = await client.get("/api/v1/knowledge", params={"company_id": company["id"]})
    assert knowledge.status_code == 200
    assert knowledge.json() == []


@pytest.mark.asyncio
async def test_deadline_vs_fact_deviation_32_substantial(client):
    company = (await client.post("/api/v1/companies", json={"name": "Align Co 2"})).json()
    _, statement = await _upload_extract_statement(client, company["id"], confirm=True)
    _, fact = await _create_source_and_fact(client, company["id"])

    response = await client.post(
        "/api/v1/alignment/checks",
        json={
            "company_id": company["id"],
            "statement_id": statement["id"],
            "fact_id": fact["id"],
        },
    )
    assert response.status_code == 201
    issue = response.json()["issue"]
    assert issue["normative_value"]["minutes"] == 15
    assert issue["actual_value"]["minutes"] == 47
    assert issue["deviation_value"]["minutes"] == 32
    assert issue["deviation_value"]["substantial"] is True
    assert issue["severity"] in ("high", "critical")
    assert issue["status"] == "open"
    assert issue["evidence"]["statement_id"] == statement["id"]
    assert issue["evidence"]["fact_id"] == fact["id"]


@pytest.mark.asyncio
async def test_confirm_issue_creates_knowledge_record(client):
    company = (await client.post("/api/v1/companies", json={"name": "Align Co 3"})).json()
    _, statement = await _upload_extract_statement(client, company["id"], confirm=True)
    _, fact = await _create_source_and_fact(client, company["id"])

    check = await client.post(
        "/api/v1/alignment/checks",
        json={
            "company_id": company["id"],
            "statement_id": statement["id"],
            "fact_id": fact["id"],
        },
    )
    issue_id = check.json()["issue"]["id"]

    confirmed = await client.post(f"/api/v1/alignment/issues/{issue_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    knowledge = await client.get("/api/v1/knowledge", params={"company_id": company["id"]})
    assert knowledge.status_code == 200
    records = knowledge.json()
    assert len(records) == 1
    assert records[0]["status"] == "active"
    assert records[0]["alignment_issue_id"] == issue_id
    assert records[0]["statement_id"] == statement["id"]
    assert records[0]["record_type"] == "alignment"

    got = await client.get(f"/api/v1/knowledge/{records[0]['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == records[0]["id"]
    issue_body = confirmed.json()
    assert issue_body.get("proposed_change") or (issue_body.get("evidence") or {}).get(
        "proposed_change"
    )


@pytest.mark.asyncio
async def test_analysis_blocked_when_dq_gate_blocked(client):
    company = (await client.post("/api/v1/companies", json={"name": "Align Co 4"})).json()
    source = (
        await client.post(
            "/api/v1/sources",
            json={
                "company_id": company["id"],
                "code": "crm-bad",
                "name": "Bad CRM",
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
                "created_at": "2026-08-01T09:00:00+03:00",
            },
        },
    )
    assert bad.status_code == 200
    assert bad.json()["blocked"] is True

    analysis = await client.post(
        "/api/v1/analyses",
        json={"company_id": company["id"], "question": "What about L-1001?"},
    )
    assert analysis.status_code == 201
    body = analysis.json()
    assert body["blocked"] is True
    assert body["status"] == "blocked"
    assert body["block_reasons"]


@pytest.mark.asyncio
async def test_analysis_succeeds_with_structured_schema_after_knowledge(client):
    company = (await client.post("/api/v1/companies", json={"name": "Align Co 5"})).json()
    _, statement = await _upload_extract_statement(client, company["id"], confirm=True)
    _, fact = await _create_source_and_fact(client, company["id"])

    check = await client.post(
        "/api/v1/alignment/checks",
        json={
            "company_id": company["id"],
            "statement_id": statement["id"],
            "fact_id": fact["id"],
        },
    )
    issue_id = check.json()["issue"]["id"]
    await client.post(f"/api/v1/alignment/issues/{issue_id}/confirm")

    analysis = await client.post(
        "/api/v1/analyses",
        json={
            "company_id": company["id"],
            "question": "Есть ли подтвержденное нарушение срока обработки лида L-1001 и что можно сделать?",
        },
    )
    assert analysis.status_code == 201
    body = analysis.json()
    assert body["blocked"] is False
    assert body["status"] == "ready"
    output = body["output"]
    for key in (
        "facts",
        "observations",
        "hypotheses",
        "recommendations",
        "missing_data",
        "sources",
        "trust_index",
        "blocked",
    ):
        assert key in output
    assert output["blocked"] is False
    assert body["recommendations"]
    assert any("L-1001" in (r["body"] + r["title"]) for r in body["recommendations"])


@pytest.mark.asyncio
async def test_decision_and_result_with_audit_path(client):
    company = (await client.post("/api/v1/companies", json={"name": "Align Co 6"})).json()
    _, statement = await _upload_extract_statement(client, company["id"], confirm=True)
    _, fact = await _create_source_and_fact(client, company["id"])
    check = await client.post(
        "/api/v1/alignment/checks",
        json={
            "company_id": company["id"],
            "statement_id": statement["id"],
            "fact_id": fact["id"],
        },
    )
    await client.post(f"/api/v1/alignment/issues/{check.json()['issue']['id']}/confirm")
    analysis = await client.post(
        "/api/v1/analyses",
        json={"company_id": company["id"], "question": "What about lead L-1001?"},
    )
    analysis_body = analysis.json()
    recommendation_id = analysis_body["recommendations"][0]["id"]

    decision = await client.post(
        "/api/v1/decisions",
        json={
            "company_id": company["id"],
            "analysis_id": analysis_body["id"],
            "recommendation_id": recommendation_id,
            "status": "accepted",
            "rationale": "Proceed with careful SLA review",
            "owner_name": "Ops Manager",
            "checkpoint_at": "2026-08-20T12:00:00+00:00",
            "expected_result": "SLA ownership clarified",
        },
    )
    assert decision.status_code == 201
    decision_id = decision.json()["id"]

    result = await client.post(
        f"/api/v1/decisions/{decision_id}/result",
        json={
            "actual_result": "SLA ownership clarified",
            "checked_at": "2026-08-21T12:00:00+00:00",
            "comment": "Done",
        },
    )
    assert result.status_code == 201
    assert result.json()["status"] == "met"

    got = await client.get(f"/api/v1/decisions/{decision_id}")
    assert got.status_code == 200
    assert got.json()["result"]["status"] == "met"

    missed = await client.post(
        "/api/v1/decisions",
        json={
            "company_id": company["id"],
            "status": "accepted",
            "rationale": "Second decision",
            "owner_name": "Ops Manager",
            "expected_result": "Queue delay under 15 minutes",
        },
    )
    missed_id = missed.json()["id"]
    missed_result = await client.post(
        f"/api/v1/decisions/{missed_id}/result",
        json={
            "actual_result": "Average delay still 40 minutes",
            "checked_at": "2026-08-22T12:00:00+00:00",
        },
    )
    assert missed_result.json()["status"] == "missed"
    assert missed_result.json()["deviation_note"]


@pytest.mark.asyncio
async def test_responsible_vs_actor_alignment(client):
    company = await _bootstrap_company(client)
    document_id, _statement = await _upload_extract_statement(client, company["id"], confirm=False)

    statements = (await client.get(f"/api/v1/documents/{document_id}/statements")).json()
    responsible = next(item for item in statements if item["statement_type"] == "responsible")
    confirmed = await client.post(f"/api/v1/statements/{responsible['id']}/confirm")
    assert confirmed.status_code == 200

    _source, fact = await _create_source_and_fact(client, company["id"])
    check = await client.post(
        "/api/v1/alignment/checks",
        json={
            "company_id": company["id"],
            "statement_id": responsible["id"],
            "fact_id": fact["id"],
            "check_type": "responsible",
        },
    )
    assert check.status_code == 201
    issue = check.json()["issue"]
    assert issue["deviation_value"]["mismatch"] is True
    assert check.json()["check"]["rule_code"] == "lead_responsible_vs_actor"

    accepted = await client.post(f"/api/v1/alignment/issues/{issue['id']}/accept-deviation")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted_deviation"

    knowledge_list = await client.get("/api/v1/knowledge", params={"company_id": company["id"]})
    assert knowledge_list.status_code == 200
    titles = [item["title"] for item in knowledge_list.json()]
    assert any("ответствен" in t.lower() or "Принято" in t for t in titles)


@pytest.mark.asyncio
async def test_process_stage_alignment(client):
    company = await _bootstrap_company(client)
    content = (
        "Менеджер по продажам обязан связаться с новым лидом "
        "не позднее 15 минут после его создания. "
        "Обязательные этапы: создание лида → квалификация → первый контакт."
    ).encode("utf-8")
    import io

    upload = await client.post(
        "/api/v1/documents",
        data={"company_id": company["id"], "title": "Stages Policy"},
        files={"file": ("stages.pdf", io.BytesIO(content), "application/pdf")},
    )
    document = upload.json()["document"]
    version_id = document["versions"][0]["id"]
    await client.post(f"/api/v1/documents/{document['id']}/versions/{version_id}/extract")
    statements = (await client.get(f"/api/v1/documents/{document['id']}/statements")).json()
    stage = next(item for item in statements if item["statement_type"] == "process_stage")
    await client.post(f"/api/v1/statements/{stage['id']}/confirm")

    _source, fact = await _create_source_and_fact(
        client,
        company["id"],
        stages_completed=["создание лида", "первый контакт"],
        stages_skipped=["квалификация"],
    )
    check = await client.post(
        "/api/v1/alignment/checks",
        json={
            "company_id": company["id"],
            "statement_id": stage["id"],
            "fact_id": fact["id"],
            "check_type": "process_stage",
        },
    )
    assert check.status_code == 201
    issue = check.json()["issue"]
    assert issue["deviation_value"]["mismatch"] is True
    assert "квалификация" in issue["actual_value"]["stages_skipped"]

    confirmed = await client.post(f"/api/v1/alignment/issues/{issue['id']}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert (confirmed.json().get("proposed_change") or {}).get("title")


@pytest.mark.asyncio
async def test_request_data_stores_evidence(client):
    company = await _bootstrap_company(client)
    _, statement = await _upload_extract_statement(client, company["id"], confirm=True)
    _, fact = await _create_source_and_fact(client, company["id"])
    check = await client.post(
        "/api/v1/alignment/checks",
        json={
            "company_id": company["id"],
            "statement_id": statement["id"],
            "fact_id": fact["id"],
        },
    )
    issue_id = check.json()["issue"]["id"]
    requested = await client.post(f"/api/v1/alignment/issues/{issue_id}/request-data")
    assert requested.status_code == 200
    assert requested.json()["status"] == "needs_data"
    assert (requested.json()["evidence"] or {}).get("data_request", {}).get("status") == "requested"


@pytest.mark.asyncio
async def test_list_alignment_issues(client):
    company = (await client.post("/api/v1/companies", json={"name": "List Align Co"})).json()
    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200
    listed = await client.get("/api/v1/alignment/issues", params={"company_id": company["id"]})
    assert listed.status_code == 200
    assert len(listed.json()) >= 3
    confirmed = await client.get(
        "/api/v1/alignment/issues",
        params={"company_id": company["id"], "status": "confirmed"},
    )
    assert confirmed.status_code == 200
    assert all(i["status"] == "confirmed" for i in confirmed.json())
    assert any(i.get("proposed_change") for i in confirmed.json())


@pytest.mark.asyncio
async def test_apply_proposed_change_creates_document_version(client):
    company = await _bootstrap_company(client)
    document_id, statement = await _upload_extract_statement(client, company["id"], confirm=True)
    _, fact = await _create_source_and_fact(client, company["id"])
    check = await client.post(
        "/api/v1/alignment/checks",
        json={
            "company_id": company["id"],
            "statement_id": statement["id"],
            "fact_id": fact["id"],
        },
    )
    issue_id = check.json()["issue"]["id"]
    confirmed = await client.post(f"/api/v1/alignment/issues/{issue_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["proposed_change"]

    applied = await client.post(f"/api/v1/alignment/issues/{issue_id}/apply-proposed-change")
    assert applied.status_code == 200
    proposal = applied.json()["proposed_change"]
    assert proposal["status"] == "applied"
    assert proposal["applied_version_id"]

    doc = await client.get(f"/api/v1/documents/{document_id}")
    assert doc.status_code == 200
    versions = doc.json()["versions"]
    assert len(versions) >= 2
    assert any(str(v["id"]) == proposal["applied_version_id"] for v in versions)
