import pytest


@pytest.mark.asyncio
async def test_bootstrap_creates_identity_graph(client):
    response = await client.post("/api/v1/identity/bootstrap")
    assert response.status_code == 201
    data = response.json()

    assert data["company"]["name"] == "Demo Company"
    assert data["department"]["code"] == "sales"
    assert data["role"]["code"] == "admin"
    assert data["user"]["email"] == "admin@example.com"
    assert data["user"]["roles"][0]["code"] == "admin"

    duplicate = await client.post("/api/v1/identity/bootstrap")
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_create_company_and_list(client):
    created = await client.post("/api/v1/companies", json={"name": "Acme"})
    assert created.status_code == 201
    company = created.json()

    listed = await client.get("/api/v1/companies")
    assert listed.status_code == 200
    assert any(item["id"] == company["id"] for item in listed.json())


@pytest.mark.asyncio
async def test_create_user_rejects_unknown_department(client):
    company = (await client.post("/api/v1/companies", json={"name": "Beta"})).json()
    response = await client.post(
        "/api/v1/users",
        json={
            "company_id": company["id"],
            "email": "user@example.com",
            "full_name": "Beta User",
            "department_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "department_not_found"
