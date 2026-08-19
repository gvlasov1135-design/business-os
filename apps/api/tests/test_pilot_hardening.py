"""Pilot hardening: request id, readiness pilot flags, rate limit."""

from unittest.mock import AsyncMock, patch

import pytest

from common.rate_limit import check_rate_limit
from common.errors import AppError


@pytest.mark.asyncio
async def test_health_sets_request_id(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("x-request-id")


@pytest.mark.asyncio
async def test_readiness_includes_pilot_flags(client):
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
    pilot = response.json()["pilot"]
    assert "auth_required" in pilot
    assert "secrets_insecure" in pilot
    assert "rate_limit_per_minute" in pilot


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    await client.get("/health")
    response = await client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "business_os_http_requests_total" in body
    assert "business_os_http_request_latency_ms_avg" in body


def test_rate_limit_blocks_after_threshold():
    key = "test-rate-limit-unique-key"
    for _ in range(3):
        check_rate_limit(key, limit_per_minute=3)
    with pytest.raises(AppError) as exc:
        check_rate_limit(key, limit_per_minute=3)
    assert exc.value.status_code == 429
