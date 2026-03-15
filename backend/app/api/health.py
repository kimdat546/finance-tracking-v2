"""Health check endpoints."""

from fastapi import APIRouter

from app.database import DatabaseManager

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Simple health check ping."""
    return {"status": "pong"}


@router.get("/status")
async def health_status() -> dict[str, bool | str]:
    """Get detailed health status."""
    db_healthy = await DatabaseManager.health_check()

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": db_healthy,
        "api": "ok",
    }
