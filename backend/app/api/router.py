"""Main API router that includes all sub-routers."""

from fastapi import APIRouter

from app.api import (
    auth,
    backup,
    categorization,
    contacts,
    dynamic_parsers,
    email_dedup,
    email_sync,
    export,
    health,
    ingest,
    matching,
    oauth,
    parser_health,
    planning,
    reports,
    split_bills,
    transactions,
    unrecognized_emails,
)

# Create main router
router = APIRouter()

# Include sub-routers
router.include_router(health.router)
router.include_router(transactions.router)
router.include_router(oauth.router, tags=["oauth"])
router.include_router(email_sync.router, tags=["email-sync"])
router.include_router(matching.router)
router.include_router(unrecognized_emails.router)
router.include_router(email_dedup.router, tags=["email-dedup"])
router.include_router(dynamic_parsers.router)
router.include_router(categorization.router)
router.include_router(parser_health.router)
router.include_router(contacts.router)
router.include_router(split_bills.router)
router.include_router(planning.router)
router.include_router(reports.router)
router.include_router(ingest.router)
router.include_router(auth.router)
router.include_router(backup.router)
router.include_router(export.router)

__all__ = ["router"]
