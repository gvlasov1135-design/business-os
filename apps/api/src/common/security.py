from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from common.errors import AppError
from config.settings import Settings


def hash_password(password: str, *, iterations: int = 120_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algo, iterations_s, salt_b64, digest_b64 = password_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def create_access_token(
    settings: Settings,
    *,
    user_id: str,
    company_id: str,
    email: str,
    roles: list[str],
) -> str:
    payload = {
        "sub": user_id,
        "company_id": company_id,
        "email": email,
        "roles": roles,
        "exp": int(time.time()) + settings.auth_token_ttl_seconds,
    }
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    signature = hmac.new(
        settings.auth_secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig = base64.urlsafe_b64encode(signature).decode()
    return f"{body}.{sig}"


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(
            settings.auth_secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(base64.urlsafe_b64encode(expected).decode(), sig):
            raise AppError("Invalid token", status_code=401, code="invalid_token")
        payload = json.loads(base64.urlsafe_b64decode(body.encode()))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise AppError("Token expired", status_code=401, code="token_expired")
        return payload
    except AppError:
        raise
    except Exception as exc:
        raise AppError("Invalid token", status_code=401, code="invalid_token") from exc
