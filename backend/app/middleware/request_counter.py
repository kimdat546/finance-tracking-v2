"""Request counter middleware for tracking API usage metrics."""

import logging
import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# In-memory counters (suitable for single-process deployments; use Redis for multi-process)
_request_counts: dict[str, int] = defaultdict(int)
_error_counts: dict[str, int] = defaultdict(int)
_latency_samples: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
_total_requests = 0
_total_errors = 0


class RequestCounterMiddleware(BaseHTTPMiddleware):
    """Counts requests, errors, and tracks latency per endpoint."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        global _total_requests, _total_errors

        path = request.url.path
        method = request.method
        key = f"{method} {path}"

        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        _total_requests += 1
        _request_counts[key] += 1
        _latency_samples[key].append(elapsed_ms)

        if response.status_code >= 500:
            _total_errors += 1
            _error_counts[key] += 1

        if elapsed_ms > 2000:
            logger.warning("Slow request %s %s — %.0fms", method, path, elapsed_ms)

        return response


def get_metrics_snapshot() -> dict:
    """Return a snapshot of current in-memory metrics."""
    endpoint_stats = {}
    for key in _request_counts:
        samples = list(_latency_samples[key])
        avg_ms = sum(samples) / len(samples) if samples else 0.0
        endpoint_stats[key] = {
            "count": _request_counts[key],
            "errors": _error_counts.get(key, 0),
            "avg_latency_ms": round(avg_ms, 2),
        }

    return {
        "total_requests": _total_requests,
        "total_errors": _total_errors,
        "error_rate": round(_total_errors / _total_requests * 100, 2) if _total_requests else 0.0,
        "endpoints": endpoint_stats,
    }
