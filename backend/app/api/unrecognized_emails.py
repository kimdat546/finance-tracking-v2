"""API endpoints for the unrecognized-email queue."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.unrecognized_email import (
    AnalyticsResponse,
    BulkDeleteRequest,
    BulkUpdateRequest,
    CategorizeRequest,
    ExportRequest,
    RuleSuggestionsResponse,
    UnrecognizedEmailDetailSchema,
    UnrecognizedEmailSchema,
    UnrecognizedListResponse,
)
from app.services.unrecognized_email_service import UnrecognizedEmailService

# Auth is implemented in WBS-007; hard-code user ID for now.
_HARDCODED_USER_ID = "00000000-0000-0000-0000-000000000001"

router = APIRouter(prefix="/unrecognized-emails", tags=["unrecognized-emails"])


def _get_service(db: AsyncSession = Depends(get_db)) -> UnrecognizedEmailService:
    """Dependency: resolve :class:`UnrecognizedEmailService`."""
    return UnrecognizedEmailService(db)


# ------------------------------------------------------------------
# Collection endpoints
# ------------------------------------------------------------------


@router.get("", response_model=UnrecognizedListResponse)
async def list_unrecognized_emails(
    status: str | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    service: UnrecognizedEmailService = Depends(_get_service),
) -> UnrecognizedListResponse:
    """List unrecognized emails with optional status filter and pagination."""
    items, total = await service.list_unrecognized(
        user_id=_HARDCODED_USER_ID,
        status=status,
        page=page,
        page_size=page_size,
    )
    return UnrecognizedListResponse(
        items=[UnrecognizedEmailSchema.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    service: UnrecognizedEmailService = Depends(_get_service),
) -> AnalyticsResponse:
    """Return analytics stats for unrecognized emails."""
    data = await service.get_analytics(user_id=_HARDCODED_USER_ID)
    return AnalyticsResponse(**data)


@router.post("/bulk-update", response_model=dict)
async def bulk_update_status(
    body: BulkUpdateRequest,
    service: UnrecognizedEmailService = Depends(_get_service),
) -> dict:
    """Bulk-update the status of multiple unrecognized email records."""
    updated = await service.bulk_update_status(
        user_id=_HARDCODED_USER_ID,
        email_ids=body.email_ids,
        status=body.status,
    )
    return {"updated": updated}


@router.post("/bulk-delete", response_model=dict)
async def bulk_delete_emails(
    body: BulkDeleteRequest,
    service: UnrecognizedEmailService = Depends(_get_service),
) -> dict:
    """Bulk-delete unrecognized email records by their IDs."""
    deleted = await service.delete_by_ids(
        user_id=_HARDCODED_USER_ID,
        email_ids=body.email_ids,
    )
    return {"deleted": deleted}


@router.post("/export", response_model=dict)
async def export_emails(
    body: ExportRequest,
    service: UnrecognizedEmailService = Depends(_get_service),
) -> dict:
    """Export unrecognized emails as a JSON or CSV string."""
    content = await service.export_emails(
        user_id=_HARDCODED_USER_ID,
        format=body.format,
        status=body.status,
    )
    return {"format": body.format, "content": content}


# ------------------------------------------------------------------
# Item endpoints (must come after fixed-path endpoints)
# ------------------------------------------------------------------


@router.get("/{unrecognized_id}", response_model=UnrecognizedEmailDetailSchema)
async def get_unrecognized_email(
    unrecognized_id: str,
    service: UnrecognizedEmailService = Depends(_get_service),
) -> UnrecognizedEmailDetailSchema:
    """Get detailed information about a single unrecognized email record."""
    record = await service.get_by_id(unrecognized_id, _HARDCODED_USER_ID)
    if record is None:
        raise HTTPException(status_code=404, detail="Unrecognized email not found")
    return UnrecognizedEmailDetailSchema.from_orm_with_truncation(record)


@router.post("/{unrecognized_id}/categorize", response_model=UnrecognizedEmailSchema)
async def categorize_email(
    unrecognized_id: str,
    body: CategorizeRequest,
    service: UnrecognizedEmailService = Depends(_get_service),
) -> UnrecognizedEmailSchema:
    """Manually categorize an unrecognized email."""
    record = await service.mark_as_categorized(
        email_id=unrecognized_id,
        user_id=_HARDCODED_USER_ID,
        category=body.category,
        amount=body.amount,
        notes=body.notes,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Unrecognized email not found")
    return UnrecognizedEmailSchema.model_validate(record)


@router.post("/{unrecognized_id}/suggest-rules", response_model=RuleSuggestionsResponse)
async def suggest_rules(
    unrecognized_id: str,
    service: UnrecognizedEmailService = Depends(_get_service),
) -> RuleSuggestionsResponse:
    """Suggest parser rules based on the content of an unrecognized email."""
    # Verify the record exists and belongs to the user
    record = await service.get_by_id(unrecognized_id, _HARDCODED_USER_ID)
    if record is None:
        raise HTTPException(status_code=404, detail="Unrecognized email not found")

    suggestions_raw = await service.suggest_parser_rules(unrecognized_id, _HARDCODED_USER_ID)
    return RuleSuggestionsResponse(
        email_id=unrecognized_id,
        suggestions=suggestions_raw,
    )


@router.post("/{unrecognized_id}/ignore", response_model=UnrecognizedEmailSchema)
async def ignore_email(
    unrecognized_id: str,
    service: UnrecognizedEmailService = Depends(_get_service),
) -> UnrecognizedEmailSchema:
    """Mark an unrecognized email as ignored."""
    record = await service.mark_as_ignored(unrecognized_id, _HARDCODED_USER_ID)
    if record is None:
        raise HTTPException(status_code=404, detail="Unrecognized email not found")
    return UnrecognizedEmailSchema.model_validate(record)
