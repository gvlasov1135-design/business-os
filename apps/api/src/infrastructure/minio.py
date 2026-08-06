import logging
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from config.settings import Settings

logger = logging.getLogger(__name__)


def check_minio(settings: Settings) -> tuple[str, int | None, str | None]:
    start = time.perf_counter()
    try:
        client = boto3.client(
            "s3",
            endpoint_url=_endpoint_url(settings),
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name="us-east-1",
        )
        client.head_bucket(Bucket=settings.minio_bucket)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return "ok", latency_ms, None
    except (BotoCoreError, ClientError, Exception) as exc:
        logger.warning("MinIO check failed: %s", exc)
        return "down", None, str(exc)


def _endpoint_url(settings: Settings) -> str:
    scheme = "https" if settings.minio_secure else "http"
    return f"{scheme}://{settings.minio_endpoint}"
