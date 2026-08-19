"""In-process request metrics for pilot observability."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import perf_counter

_lock = Lock()
_requests_total = 0
_by_status: dict[str, int] = defaultdict(int)
_by_method: dict[str, int] = defaultdict(int)
_latency_sum_ms = 0.0
_latency_count = 0


def observe_request(*, method: str, status_code: int, duration_ms: float) -> None:
    global _requests_total, _latency_sum_ms, _latency_count
    bucket = f"{status_code // 100}xx"
    with _lock:
        _requests_total += 1
        _by_status[bucket] += 1
        _by_method[method.upper()] += 1
        _latency_sum_ms += duration_ms
        _latency_count += 1


def render_prometheus() -> str:
    with _lock:
        lines = [
            "# HELP business_os_http_requests_total Total HTTP requests",
            "# TYPE business_os_http_requests_total counter",
            f"business_os_http_requests_total {_requests_total}",
            "# HELP business_os_http_requests_by_status HTTP requests by status class",
            "# TYPE business_os_http_requests_by_status counter",
        ]
        for status, count in sorted(_by_status.items()):
            lines.append(f'business_os_http_requests_by_status{{class="{status}"}} {count}')
        lines.extend(
            [
                "# HELP business_os_http_requests_by_method HTTP requests by method",
                "# TYPE business_os_http_requests_by_method counter",
            ]
        )
        for method, count in sorted(_by_method.items()):
            lines.append(f'business_os_http_requests_by_method{{method="{method}"}} {count}')
        avg = (_latency_sum_ms / _latency_count) if _latency_count else 0.0
        lines.extend(
            [
                "# HELP business_os_http_request_latency_ms_avg Average request latency in ms",
                "# TYPE business_os_http_request_latency_ms_avg gauge",
                f"business_os_http_request_latency_ms_avg {avg:.3f}",
            ]
        )
        return "\n".join(lines) + "\n"


class Timer:
    def __enter__(self):
        self._start = perf_counter()
        return self

    def __exit__(self, *args):
        self.duration_ms = (perf_counter() - self._start) * 1000.0
