"""Email deduplication API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.email import Email
from app.utils.email_fingerprinting import EmailDeduplicator

router = APIRouter(prefix="/emails", tags=["email-dedup"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DuplicateEmailResponse(BaseModel):
    """Summary representation of a duplicate email record."""

    id: str = Field(description="Email record ID")
    user_id: str = Field(description="Owning user ID")
    sender: str | None = Field(description="Email sender address")
    subject: str | None = Field(description="Email subject")
    received_at: datetime | None = Field(description="When the email was received")
    fingerprint: str | None = Field(description="Deduplication fingerprint")
    is_duplicate: bool = Field(description="Whether email is marked as duplicate")

    model_config = {"from_attributes": True}


class DuplicateListResponse(BaseModel):
    """Paginated list of duplicate emails."""

    items: list[DuplicateEmailResponse]
    total: int = Field(description="Total number of duplicate emails")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total pages")


class DeduplicateResponse(BaseModel):
    """Result of running a deduplication job."""

    status: str = Field(default="success")
    duplicates_found: int = Field(description="Number of new duplicate emails detected")
    message: str = Field(description="Human-readable summary")


class DuplicateStatsResponse(BaseModel):
    """Deduplication statistics for a user."""

    user_id: str = Field(description="Owning user ID")
    total_duplicates: int = Field(description="Total emails marked as duplicate")
    total_emails: int = Field(description="Total emails for this user")
    duplicate_rate: float = Field(description="Fraction of emails that are duplicates (0–1)")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/duplicates", response_model=DuplicateListResponse)
async def list_duplicate_emails(
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> DuplicateListResponse:
    """List duplicate emails for a user, paginated.

    Returns all emails where ``is_duplicate`` is ``True`` for the given user,
    sorted by ``received_at`` descending.
    """
    base_filter = (Email.user_id == user_id) & (Email.is_duplicate == True)  # noqa: E712

    # Total count
    count_stmt = select(func.count()).select_from(Email).where(base_filter)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginated rows
    offset = (page - 1) * page_size
    stmt = (
        select(Email)
        .where(base_filter)
        .order_by(Email.received_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    emails = result.scalars().all()

    total_pages = max(1, (total + page_size - 1) // page_size)

    return DuplicateListResponse(
        items=[DuplicateEmailResponse.model_validate(e) for e in emails],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/deduplicate", response_model=DeduplicateResponse)
async def run_deduplication(
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> DeduplicateResponse:
    """Run deduplication over all un-processed emails for a user.

    Scans emails that share the same ``fingerprint`` and ``user_id`` and marks
    the later arrivals as duplicates (keeping the earliest one).  Returns the
    count of newly marked duplicates.
    """
    # Find all fingerprints that appear more than once for this user
    dup_fp_stmt = (
        select(Email.fingerprint)
        .where(
            (Email.user_id == user_id)
            & (Email.fingerprint != None)  # noqa: E711
        )
        .group_by(Email.fingerprint)
        .having(func.count(Email.id) > 1)
    )
    dup_fp_result = await db.execute(dup_fp_stmt)
    duplicate_fingerprints: list[str] = [row[0] for row in dup_fp_result.all()]

    newly_marked = 0

    for fp in duplicate_fingerprints:
        # Fetch all emails with this fingerprint ordered oldest-first
        emails_stmt = (
            select(Email)
            .where(
                (Email.user_id == user_id)
                & (Email.fingerprint == fp)
            )
            .order_by(Email.received_at.asc())
        )
        emails_result = await db.execute(emails_stmt)
        emails = emails_result.scalars().all()

        # Keep the first (oldest), mark the rest as duplicates
        for email in emails[1:]:
            if not email.is_duplicate:
                email.is_duplicate = True
                newly_marked += 1

    if newly_marked:
        await db.commit()

    return DeduplicateResponse(
        status="success",
        duplicates_found=newly_marked,
        message=f"Deduplication complete. {newly_marked} duplicate(s) marked.",
    )


@router.delete("/duplicates", response_model=dict[str, int | str])
async def delete_all_duplicates(
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    """Delete all emails marked as duplicate for a user.

    Returns the number of rows deleted.
    """
    # Count first
    count_stmt = select(func.count()).select_from(Email).where(
        (Email.user_id == user_id) & (Email.is_duplicate == True)  # noqa: E712
    )
    count = (await db.execute(count_stmt)).scalar() or 0

    if count > 0:
        del_stmt = delete(Email).where(
            (Email.user_id == user_id) & (Email.is_duplicate == True)  # noqa: E712
        )
        await db.execute(del_stmt)
        await db.commit()

    return {
        "status": "success",
        "deleted": count,
        "message": f"Deleted {count} duplicate email(s).",
    }


@router.get("/duplicates/stats", response_model=DuplicateStatsResponse)
async def get_duplicate_stats(
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> DuplicateStatsResponse:
    """Return deduplication statistics for a user.

    Includes total email count, duplicate count, and duplicate rate.
    """
    total_stmt = select(func.count()).select_from(Email).where(Email.user_id == user_id)
    total = (await db.execute(total_stmt)).scalar() or 0

    dup_stmt = select(func.count()).select_from(Email).where(
        (Email.user_id == user_id) & (Email.is_duplicate == True)  # noqa: E712
    )
    duplicates = (await db.execute(dup_stmt)).scalar() or 0

    rate = duplicates / total if total > 0 else 0.0

    return DuplicateStatsResponse(
        user_id=user_id,
        total_duplicates=duplicates,
        total_emails=total,
        duplicate_rate=rate,
    )
