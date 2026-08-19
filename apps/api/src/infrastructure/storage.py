from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from common.errors import AppError
from config.settings import Settings, get_settings


ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx"}


class ObjectStorage(Protocol):
    def put_bytes(self, key: str, data: bytes, content_type: str) -> None: ...

    def get_bytes(self, key: str) -> bytes: ...


class LocalObjectStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get_bytes(self, key: str) -> bytes:
        path = self.root / key
        if not path.exists():
            raise AppError("Stored file not found", status_code=404, code="file_not_found")
        return path.read_bytes()


class MinioObjectStorage:
    def __init__(self, settings: Settings) -> None:
        scheme = "https" if settings.minio_secure else "http"
        self.bucket = settings.minio_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=f"{scheme}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name="us-east-1",
        )

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise AppError(
                f"Failed to store file: {exc}",
                status_code=502,
                code="storage_error",
            ) from exc

    def get_bytes(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            raise AppError(
                f"Failed to read file: {exc}",
                status_code=502,
                code="storage_error",
            ) from exc


def get_storage(settings: Settings | None = None) -> ObjectStorage:
    cfg = settings or get_settings()
    if cfg.storage_backend == "minio":
        return MinioObjectStorage(cfg)
    return LocalObjectStorage(cfg.local_storage_path)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_upload(filename: str, content_type: str | None) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise AppError(
            "Unsupported file type. Allowed: PDF, DOCX, XLSX",
            status_code=400,
            code="unsupported_file_type",
        )

    normalized = content_type or ""
    if normalized not in ALLOWED_CONTENT_TYPES:
        # browsers sometimes send octet-stream; fall back by extension
        for mime, ext in ALLOWED_CONTENT_TYPES.items():
            if ext == suffix:
                return mime, suffix
        raise AppError(
            "Unsupported content type",
            status_code=400,
            code="unsupported_content_type",
        )
    if ALLOWED_CONTENT_TYPES[normalized] != suffix:
        raise AppError(
            "Filename extension does not match content type",
            status_code=400,
            code="content_type_mismatch",
        )
    return normalized, suffix
