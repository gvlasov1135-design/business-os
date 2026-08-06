from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_readiness_all_ok(client):
    with (
        patch(
            "modules.system.service.check_postgres",
            new=AsyncMock(return_value=("ok", 2, None)),
        ),
        patch(
            "modules.system.service.check_redis",
            new=AsyncMock(return_value=("ok", 1, None)),
        ),
        patch(
            "modules.system.service.check_minio",
            return_value=("ok", 3, None),
        ),
    ):
        response = await client.get("/api/v1/system/readiness")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["components"]["api"]["status"] == "ok"
    assert data["components"]["postgres"]["status"] == "ok"
    assert data["components"]["redis"]["status"] == "ok"
    assert data["components"]["minio"]["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_postgres_down_is_partial(client):
    with (
        patch(
            "modules.system.service.check_postgres",
            new=AsyncMock(return_value=("down", None, "connection refused")),
        ),
        patch(
            "modules.system.service.check_redis",
            new=AsyncMock(return_value=("ok", 1, None)),
        ),
        patch(
            "modules.system.service.check_minio",
            return_value=("ok", 3, None),
        ),
    ):
        response = await client.get("/api/v1/system/readiness")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "partial"
    assert data["components"]["postgres"]["status"] == "down"
    assert data["components"]["postgres"]["error"] == "connection refused"


@pytest.mark.asyncio
async def test_readiness_all_down_returns_error(client):
    with (
        patch(
            "modules.system.service.check_postgres",
            new=AsyncMock(return_value=("down", None, "postgres down")),
        ),
        patch(
            "modules.system.service.check_redis",
            new=AsyncMock(return_value=("down", None, "redis down")),
        ),
        patch(
            "modules.system.service.check_minio",
            return_value=("down", None, "minio down"),
        ),
    ):
        response = await client.get("/api/v1/system/readiness")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
