from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

import redis

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

QUEUE_KEY = "business-os:jobs"


def _client(settings: Settings | None = None) -> redis.Redis:
    settings = settings or get_settings()
    password = settings.redis_password or None
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=password,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def enqueue_job(job_type: str, payload: dict[str, Any], *, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    job_id = str(uuid4())
    body = {"id": job_id, "type": job_type, **payload}
    client = _client(settings)
    client.lpush(QUEUE_KEY, json.dumps(body, default=str))
    logger.info("enqueued job %s type=%s", job_id, job_type)
    return job_id


def enqueue_extraction(
    *,
    document_id: str,
    version_id: str,
    settings: Settings | None = None,
) -> str:
    return enqueue_job(
        "extract_document",
        {"document_id": document_id, "version_id": version_id},
        settings=settings,
    )
