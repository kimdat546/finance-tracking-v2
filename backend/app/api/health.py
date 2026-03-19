"""Health check endpoints."""

import platform
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.database import DatabaseManager
from app.middleware.request_counter import get_metrics_snapshot

router = APIRouter(prefix="/health", tags=["health"])

_start_time = time.time()


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Simple health check ping."""
    return {"status": "pong"}


@router.get("/status")
async def health_status() -> dict:
    """Detailed health status including uptime and DB connectivity."""
    db_healthy = await DatabaseManager.health_check()

    uptime_seconds = int(time.time() - _start_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return {
        "status": "healthy" if db_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "uptime_seconds": uptime_seconds,
        "components": {
            "database": "healthy" if db_healthy else "unhealthy",
            "api": "healthy",
        },
        "python_version": platform.python_version(),
        "platform": platform.system(),
    }


@router.get("/metrics")
async def get_metrics() -> dict:
    """API request metrics snapshot (counts, error rates, latency)."""
    return get_metrics_snapshot()


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Kubernetes-style readiness probe."""
    db_healthy = await DatabaseManager.health_check()
    if not db_healthy:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database not ready")
    return {"status": "ready"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Kubernetes-style liveness probe."""
    return {"status": "alive"}
