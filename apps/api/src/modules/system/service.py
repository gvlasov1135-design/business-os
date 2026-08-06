from datetime import datetime, timezone

from config.settings import Settings
from infrastructure.minio import check_minio
from infrastructure.postgres import check_postgres
from infrastructure.redis import check_redis
from modules.system.schemas import AggregateStatus, ComponentHealth, ReadinessResponse


async def get_readiness(settings: Settings) -> ReadinessResponse:
    postgres_status, postgres_latency, postgres_error = await check_postgres(settings)
    redis_status, redis_latency, redis_error = await check_redis(settings)
    minio_status, minio_latency, minio_error = check_minio(settings)

    components = {
        "api": ComponentHealth(status="ok"),
        "postgres": ComponentHealth(
            status=postgres_status,
            latency_ms=postgres_latency,
            error=postgres_error,
        ),
        "redis": ComponentHealth(
            status=redis_status,
            latency_ms=redis_latency,
            error=redis_error,
        ),
        "minio": ComponentHealth(
            status=minio_status,
            latency_ms=minio_latency,
            error=minio_error,
        ),
    }

    dependency_statuses = [
        postgres_status,
        redis_status,
        minio_status,
    ]

    if all(s == "ok" for s in dependency_statuses):
        aggregate: AggregateStatus = "ready"
    elif any(s == "ok" for s in dependency_statuses):
        aggregate = "partial"
    else:
        aggregate = "error"

    return ReadinessResponse(
        status=aggregate,
        components=components,
        checked_at=datetime.now(timezone.utc),
    )
