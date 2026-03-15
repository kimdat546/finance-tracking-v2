"""Main API router that includes all sub-routers."""

from fastapi import APIRouter

from app.api import health, transactions

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(health.router)
router.include_router(transactions.router)

__all__ = ["router"]
