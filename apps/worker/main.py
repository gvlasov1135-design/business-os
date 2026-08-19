"""Business OS Redis queue worker.

Consumes jobs from `business-os:jobs` and periodically drains the transactional outbox.
"""

from __future__ import annotations

import json
import logging
import os
import time

import httpx
import redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("business-os.worker")

QUEUE_KEY = "business-os:jobs"
API_BASE = os.getenv("API_BASE_URL", "http://api:8000").rstrip("/")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
WORKER_SECRET = os.getenv("WORKER_SECRET", "business-os-worker-secret")
OUTBOX_DRAIN_EVERY_SEC = int(os.getenv("OUTBOX_DRAIN_EVERY_SEC", "15"))


def redis_client() -> redis.Redis:
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True,
    )


def process_job(job: dict) -> None:
    job_type = job.get("type")
    headers = {"X-Worker-Key": WORKER_SECRET}
    if job_type == "extract_document":
        document_id = job["document_id"]
        version_id = job["version_id"]
        url = f"{API_BASE}/api/v1/documents/{document_id}/versions/{version_id}/extract"
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers)
            response.raise_for_status()
        logger.info("extract_document done job=%s document=%s", job.get("id"), document_id)
        return
    logger.warning("unknown job type=%s id=%s", job_type, job.get("id"))


def drain_outbox() -> None:
    headers = {"X-Worker-Key": WORKER_SECRET}
    url = f"{API_BASE}/api/v1/outbox/drain?limit=50"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    count = int(data.get("count") or 0)
    if count:
        logger.info("outbox drained count=%s", count)


def main() -> None:
    logger.info(
        "Worker started api=%s queue=%s outbox_every=%ss",
        API_BASE,
        QUEUE_KEY,
        OUTBOX_DRAIN_EVERY_SEC,
    )
    client = redis_client()
    last_outbox = 0.0
    while True:
        try:
            now = time.time()
            if now - last_outbox >= OUTBOX_DRAIN_EVERY_SEC:
                try:
                    drain_outbox()
                except Exception:  # noqa: BLE001
                    logger.exception("outbox drain error")
                last_outbox = now

            item = client.brpop(QUEUE_KEY, timeout=5)
            if not item:
                continue
            _, raw = item
            job = json.loads(raw)
            process_job(job)
        except Exception:  # noqa: BLE001
            logger.exception("worker loop error")
            time.sleep(2)


if __name__ == "__main__":
    main()
