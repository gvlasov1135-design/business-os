import logging
import time

import redis.asyncio as redis

from config.settings import Settings

logger = logging.getLogger(__name__)


async def check_redis(settings: Settings) -> tuple[str, int | None, str | None]:
    start = time.perf_counter()
    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        decode_responses=True,
        socket_connect_timeout=5.0,
        socket_timeout=5.0,
    )
    try:
        pong = await client.ping()
        if not pong:
            return "down", None, "Redis PING returned falsy response"
        latency_ms = int((time.perf_counter() - start) * 1000)
        return "ok", latency_ms, None
    except Exception as exc:
        logger.warning("Redis check failed: %s", exc)
        return "down", None, str(exc)
    finally:
        await client.aclose()
