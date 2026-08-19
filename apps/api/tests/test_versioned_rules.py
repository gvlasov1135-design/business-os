import pytest


@pytest.mark.asyncio
async def test_versioned_alignment_rules(client):
    company = (await client.post("/api/v1/companies", json={"name": "Rules Co"})).json()
    boot = await client.post(f"/api/v1/rules/bootstrap?company_id={company['id']}")
    assert boot.status_code == 200
    assert "lead_first_contact_deadline" in boot.json()["codes"]

    rules = (await client.get(f"/api/v1/rules?company_id={company['id']}")).json()
    align = next(r for r in rules if r["code"] == "lead_first_contact_deadline")
    versions = (await client.get(f"/api/v1/rules/{align['id']}/versions")).json()
    assert versions[0]["version_number"] == 1
    assert versions[0]["status"] == "active"

    v2 = await client.post(
        f"/api/v1/rules/{align['id']}/versions",
        json={
            "body": {
                "predicate": "actual_first_contact_minutes",
                "substantial_deviation_minutes": 10,
            },
            "change_reason": "ужесточить порог",
        },
    )
    assert v2.status_code == 201
    assert v2.json()["version_number"] == 2

    versions2 = (await client.get(f"/api/v1/rules/{align['id']}/versions")).json()
    assert versions2[1]["status"] == "superseded"

    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200
    issue = await client.get(f"/api/v1/alignment/issues/{demo.json()['issue_id']}")
    assert issue.status_code == 200
    evidence = issue.json().get("evidence") or {}
    assert evidence.get("rule_version_id")
    assert evidence.get("rule_version_number") == 2
