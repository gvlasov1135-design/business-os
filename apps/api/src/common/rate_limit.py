"""Simple in-memory rate limiter for pilot (login/bootstrap)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from common.errors import AppError

_lock = Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, *, limit_per_minute: int) -> None:
    if limit_per_minute <= 0:
        return
    now = time.time()
    window = 60.0
    with _lock:
        bucket = _buckets[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit_per_minute:
            raise AppError(
                "Too many requests — try again later",
                status_code=429,
                code="rate_limited",
            )
        bucket.append(now)
