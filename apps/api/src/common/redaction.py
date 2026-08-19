"""Redaction for LLM Gateway context — strip sensitive CRM fields before AI sees them."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "email",
        "phone",
        "inn",
        "passport",
        "password",
        "password_hash",
        "token",
        "access_token",
        "secret",
        "card_number",
        "actual_actor",  # person id — keep role-level only in AI context
    }
)

REDACTED = "[REDACTED]"


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS or any(
                s in str(key).lower() for s in ("password", "secret", "token")
            ):
                out[key] = REDACTED
            else:
                out[key] = redact_value(item)
        return out
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def redact_context(context: dict[str, Any] | None) -> dict[str, Any]:
    if not context:
        return {}
    return redact_value(deepcopy(context))
