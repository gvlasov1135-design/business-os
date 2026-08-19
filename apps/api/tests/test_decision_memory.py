import pytest


@pytest.mark.asyncio
async def test_decision_memory_tasks_review_lessons(client):
    company = (await client.post("/api/v1/companies", json={"name": "DM Co"})).json()
    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200
    extras = demo.json()["extras"]
    assert extras["decision_task_count"] >= 1
    assert extras["decision_lesson_count"] >= 1
    assert extras["decision_reviewed"] is True
    assert extras.get("decision_selected_option")

    decision_id = demo.json()["decision_id"]
    detail = await client.get(f"/api/v1/decisions/{decision_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["selected_option"]
    assert body["tasks"]
    assert body["tasks"][0]["status"] == "done"  # met result closes tasks
    assert body["result"]["status"] == "met"
    assert body["result"]["reviewed_at"]
    assert body["result"]["review_notes"]
    assert body["lessons"]
    assert body["result"]["deviation_note"] is None

    # second company path: create decision + miss result + review
    company2 = (await client.post("/api/v1/companies", json={"name": "DM2"})).json()
    created = await client.post(
        "/api/v1/decisions",
        json={
            "company_id": company2["id"],
            "status": "accepted",
            "selected_option": "Проверить очередь",
            "rationale": "Нужен контроль",
            "owner_name": "Owner",
            "expected_result": "Очередь закрыта за сутки",
            "checkpoint_at": "2026-08-20T12:00:00+00:00",
        },
    )
    assert created.status_code == 201
    assert created.json()["tasks"]
    did = created.json()["id"]

    missed = await client.post(
        f"/api/v1/decisions/{did}/result",
        json={
            "actual_result": "Очередь всё ещё открыта",
            "checked_at": "2026-08-21T12:00:00+00:00",
            "comment": "не успели",
        },
    )
    assert missed.status_code == 201
    assert missed.json()["status"] == "missed"
    assert missed.json()["deviation_note"]

    reviewed = await client.post(
        f"/api/v1/decisions/{did}/review",
        json={
            "review_notes": "Нужен запас мощности",
            "lesson_body": "Не ставить checkpoint без резерва слотов",
            "lesson_category": "capacity",
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["reviewed_at"]

    drain = await client.post("/api/v1/outbox/drain?limit=50")
    assert drain.status_code == 200
    assert drain.json()["count"] >= 1
