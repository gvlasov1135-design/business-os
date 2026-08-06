import logging
import time

import asyncpg

from config.settings import Settings

logger = logging.getLogger(__name__)


async def check_postgres(settings: Settings) -> tuple[str, int | None, str | None]:
    start = time.perf_counter()
    try:
        conn = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            timeout=5.0,
        )
        await conn.fetchval("SELECT 1")
        await conn.close()
        latency_ms = int((time.perf_counter() - start) * 1000)
        return "ok", latency_ms, None
    except Exception as exc:
        logger.warning("PostgreSQL check failed: %s", exc)
        return "down", None, str(exc)
