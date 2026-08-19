"""Council: общий стол + личные чаты с агентами."""

import pytest


@pytest.mark.asyncio
async def test_council_table_and_private(client):
    company = (await client.post("/api/v1/companies", json={"name": "Council Co"})).json()
    demo = await client.post("/api/v1/demo/run", json={"company_id": company["id"]})
    assert demo.status_code == 200
    analysis_id = demo.json()["analysis_id"]

    created = await client.post(
        "/api/v1/council/sessions",
        json={
            "company_id": company["id"],
            "topic": "Разбор SLA L-1001",
            "analysis_id": analysis_id,
        },
    )
    assert created.status_code == 201
    session = created.json()
    assert session["status"] == "open"
    assert session["analysis_id"] == analysis_id
    assert any(m["role"] == "system" for m in session["messages"])

    table = await client.post(
        f"/api/v1/council/sessions/{session['id']}/messages",
        json={"channel": "table", "body": "Кто виноват в срыве первого контакта?"},
    )
    assert table.status_code == 200
    replies = table.json()
    assert len(replies) == 4  # user + exec + sales + critic
    agents = {m["agent"] for m in replies if m["role"] == "agent"}
    assert agents == {"executive", "sales", "critic"}

    private = await client.post(
        f"/api/v1/council/sessions/{session['id']}/messages",
        json={
            "channel": "private",
            "agent": "data_doctor",
            "body": "Есть ли silent stage skip?",
        },
    )
    assert private.status_code == 200
    priv = private.json()
    assert len(priv) == 2
    assert priv[1]["agent"] == "data_doctor"
    assert priv[1]["channel"] == "private"

    loaded = await client.get(f"/api/v1/council/sessions/{session['id']}")
    assert loaded.status_code == 200
    assert len(loaded.json()["messages"]) >= 6

    closed = await client.post(f"/api/v1/council/sessions/{session['id']}/close")
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    denied = await client.post(
        f"/api/v1/council/sessions/{session['id']}/messages",
        json={"channel": "table", "body": "ещё раз"},
    )
    assert denied.status_code == 409


@pytest.mark.asyncio
async def test_council_list_sessions(client):
    company = (await client.post("/api/v1/companies", json={"name": "Council List Co"})).json()
    created = await client.post(
        "/api/v1/council/sessions",
        json={"company_id": company["id"], "topic": "Короткое заседание"},
    )
    assert created.status_code == 201
    listed = await client.get(f"/api/v1/council/sessions?company_id={company['id']}")
    assert listed.status_code == 200
    assert any(s["id"] == created.json()["id"] for s in listed.json())
