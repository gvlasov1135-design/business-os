import pytest


@pytest.mark.asyncio
async def test_kpi_create_version_recalculate(client):
    company = (await client.post("/api/v1/companies", json={"name": "KPI Co"})).json()
    source = (
        await client.post(
            "/api/v1/sources",
            json={
                "company_id": company["id"],
                "code": "crm-kpi",
                "name": "CRM KPI",
                "source_type": "crm",
            },
        )
    ).json()

    for lead_id, contact in (("L-1", "10:15:00"), ("L-2", "10:20:00")):
        imported = await client.post(
            "/api/v1/ingestion/import",
            json={
                "source_id": source["id"],
                "payload": {
                    "lead_id": lead_id,
                    "created_at": "2026-08-01T10:00:00+03:00",
                    "first_contact_at": f"2026-08-01T{contact}+03:00",
                    "email": f"{lead_id.lower()}@example.com",
                },
            },
        )
        assert imported.status_code == 200
        assert imported.json()["fact"] is not None

    bad = await client.post(
        "/api/v1/kpis",
        json={
            "company_id": company["id"],
            "code": "bad",
            "name": "Bad",
            "owner_name": "Owner",
            "formula": {"op": "eval('hack')"},
            "source_mapping": {"predicate": "x"},
        },
    )
    assert bad.status_code == 400

    created = await client.post(
        "/api/v1/kpis",
        json={
            "company_id": company["id"],
            "code": "first_contact_avg",
            "name": "Среднее время контакта",
            "owner_name": "Sales Lead",
            "unit": "minutes",
            "formula": {"op": "avg_fact_minutes"},
            "source_mapping": {"predicate": "actual_first_contact_minutes"},
            "target_value": 15,
        },
    )
    assert created.status_code == 201
    kpi = created.json()
    assert kpi["current_version_id"]

    versions = (await client.get(f"/api/v1/kpis/{kpi['id']}/versions")).json()
    assert len(versions) == 1
    assert "AVG" in versions[0]["formula_text"]
    assert versions[0]["source_mapping"]["predicate"] == "actual_first_contact_minutes"

    snap = await client.post(
        f"/api/v1/kpis/{kpi['id']}/recalculate",
        json={
            "period_start": "2026-08-01T00:00:00+00:00",
            "period_end": "2026-08-31T23:59:59+00:00",
        },
    )
    assert snap.status_code == 200
    body = snap.json()
    assert body["actual_value"] == 17.5  # (15+20)/2
    assert body["target_value"] == 15
    assert body["lineage"]["reproducible"] is True
    assert len(body["sources"]) == 2

    v2 = await client.post(
        f"/api/v1/kpis/{kpi['id']}/versions",
        json={
            "formula": {"op": "count_facts"},
            "source_mapping": {"predicate": "actual_first_contact_minutes"},
            "target_value": 10,
            "change_reason": "сменить на count",
        },
    )
    assert v2.status_code == 201
    assert v2.json()["version_number"] == 2
    assert v2.json()["status"] == "active"

    versions2 = (await client.get(f"/api/v1/kpis/{kpi['id']}/versions")).json()
    assert len(versions2) == 2
    assert versions2[1]["status"] == "superseded"

    snap2 = await client.post(
        f"/api/v1/kpis/{kpi['id']}/recalculate",
        json={
            "period_start": "2026-08-01T00:00:00+00:00",
            "period_end": "2026-08-31T23:59:59+00:00",
        },
    )
    assert snap2.json()["actual_value"] == 2.0

    listed = (await client.get(f"/api/v1/kpis/{kpi['id']}/snapshots")).json()
    assert len(listed) >= 2


@pytest.mark.asyncio
async def test_demo_includes_kpi(client):
    company = (await client.post("/api/v1/companies", json={"name": "KPI Demo Co"})).json()
    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200
    extras = demo.json()["extras"]
    assert extras.get("kpi_id")
    assert extras.get("kpi_actual") is not None
    assert extras.get("kpi_target") == 15
    assert extras.get("kpi_formula")
    assert extras.get("share_kpi_id")
    assert extras.get("share_kpi_actual") is not None
    assert extras.get("proposed_change")

    analysis = await client.get(f"/api/v1/analyses/{demo.json()['analysis_id']}")
    assert analysis.status_code == 200
    ctx = analysis.json()["context_snapshot"]
    assert ctx.get("kpis")
    assert len(ctx["kpis"]) >= 2
    assert ctx["kpis"][0]["formula_text"]


@pytest.mark.asyncio
async def test_share_within_target_kpi(client):
    company = (await client.post("/api/v1/companies", json={"name": "Share KPI Co"})).json()
    source = (
        await client.post(
            "/api/v1/sources",
            json={
                "company_id": company["id"],
                "code": "crm-share",
                "name": "CRM Share",
                "source_type": "crm",
            },
        )
    ).json()
    for lead_id, contact in (("L-1", "10:10:00"), ("L-2", "10:40:00")):
        imported = await client.post(
            "/api/v1/ingestion/import",
            json={
                "source_id": source["id"],
                "payload": {
                    "lead_id": lead_id,
                    "created_at": "2026-08-01T10:00:00+03:00",
                    "first_contact_at": f"2026-08-01T{contact}+03:00",
                    "email": f"{lead_id.lower()}@example.com",
                },
            },
        )
        assert imported.status_code == 200

    created = await client.post(
        "/api/v1/kpis",
        json={
            "company_id": company["id"],
            "code": "sla_share",
            "name": "Доля в SLA",
            "owner_name": "Sales",
            "unit": "%",
            "formula": {"op": "share_within_target", "threshold_minutes": 15},
            "source_mapping": {"predicate": "actual_first_contact_minutes"},
            "target_value": 90,
        },
    )
    assert created.status_code == 201
    snap = await client.post(
        f"/api/v1/kpis/{created.json()['id']}/recalculate",
        json={
            "period_start": "2026-08-01T00:00:00+00:00",
            "period_end": "2026-08-31T23:59:59+00:00",
        },
    )
    assert snap.status_code == 200
    # 10 min OK, 40 min miss → 50%
    assert snap.json()["actual_value"] == 50.0
