import pytest


@pytest.mark.asyncio
async def test_login_after_bootstrap(client):
    bootstrap = await client.post("/api/v1/identity/bootstrap")
    assert bootstrap.status_code == 201

    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )
    assert bad.status_code == 401

    ok = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "demo-admin"},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["access_token"]
    assert body["user"]["email"] == "admin@example.com"
    assert "admin" in body["user"]["roles"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["full_name"] == "Demo Admin"


@pytest.mark.asyncio
async def test_auth_required_blocks_writes(client, monkeypatch):
    from config.settings import get_settings

    monkeypatch.setenv("AUTH_REQUIRED", "true")
    get_settings.cache_clear()

    blocked = await client.post("/api/v1/companies", json={"name": "Locked Co"})
    assert blocked.status_code == 401

    bootstrap = await client.post("/api/v1/identity/bootstrap")
    assert bootstrap.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "demo-admin"},
    )
    token = login.json()["access_token"]

    allowed = await client.post(
        "/api/v1/companies",
        json={"name": "Unlocked Co"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert allowed.status_code == 201

    get_settings.cache_clear()
