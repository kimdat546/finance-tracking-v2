"""FastAPI router for email synchronisation endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.email import Email, EmailAccount
from app.models.system import EmailSyncLog
from app.schemas.email import (
    EmailListResponse,
    EmailSchema,
    EmailSyncRequest,
    EmailSyncResponse,
)
from app.services.email_sync_service import EmailSyncService
from app.services.gmail_service import GmailService
from app.services.oauth_service import OAuthService
from app.utils.encryption import EncryptionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-sync")

# ---------------------------------------------------------------------------
# Temporary hard-coded user until WBS-007 implements authentication.
# ---------------------------------------------------------------------------
_TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_encryption() -> EncryptionService:
    """Return a configured :class:`~app.utils.encryption.EncryptionService`."""
    return EncryptionService()


def _get_oauth_service(
    session: AsyncSession = Depends(get_db),
    encryption: EncryptionService = Depends(_get_encryption),
) -> OAuthService:
    """Build an :class:`~app.services.oauth_service.OAuthService` dependency.

    Args:
        session: Injected async SQLAlchemy session.
        encryption: Injected encryption service.

    Returns:
        A configured :class:`~app.services.oauth_service.OAuthService`.
    """
    return OAuthService(session=session, encryption=encryption)


async def _get_active_email_account(
    user_id: str,
    session: AsyncSession,
) -> EmailAccount:
    """Return the first active email account for *user_id*.

    Args:
        user_id: The user whose accounts are searched.
        session: Async SQLAlchemy session.

    Returns:
        An active :class:`~app.models.email.EmailAccount`.

    Raises:
        :class:`~fastapi.HTTPException` 404: When no active account exists.
    """
    stmt = select(EmailAccount).where(
        EmailAccount.user_id == user_id,
        EmailAccount.is_active.is_(True),
    )
    result = await session.execute(stmt)
    account = result.scalars().first()
    if account is None:
        raise HTTPException(
            status_code=404,
            detail="No active email account found. Please connect a Gmail account via OAuth.",
        )
    return account


async def _build_sync_service(
    session: AsyncSession,
    oauth_service: OAuthService,
    email_account_id: str,
) -> EmailSyncService:
    """Build an :class:`~app.services.email_sync_service.EmailSyncService`.

    Retrieves valid credentials and constructs the Gmail API wrapper.

    Args:
        session: Async SQLAlchemy session.
        oauth_service: OAuth token management service.
        email_account_id: ID of the email account whose credentials to use.

    Returns:
        A ready-to-use :class:`~app.services.email_sync_service.EmailSyncService`.

    Raises:
        :class:`~fastapi.HTTPException` 401: When credentials cannot be obtained.
    """
    credentials = await oauth_service.ensure_valid_token(email_account_id)
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Could not obtain valid Gmail credentials. Please re-authorise.",
        )
    gmail_service = GmailService(credentials=credentials)
    return EmailSyncService(
        session=session,
        gmail_service=gmail_service,
        oauth_service=oauth_service,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/trigger", response_model=EmailSyncResponse, summary="Trigger email sync")
async def trigger_sync(
    request: EmailSyncRequest,
    session: AsyncSession = Depends(get_db),
    oauth_service: OAuthService = Depends(_get_oauth_service),
) -> EmailSyncResponse:
    """Trigger an email synchronisation run for the current user.

    Performs an incremental sync using the stored Gmail ``historyId`` when
    available.  Pass ``trigger_full_sync=true`` to force a complete re-fetch.

    Args:
        request: Sync options (full-sync flag, label and sender filters).
        session: Injected DB session.
        oauth_service: Injected OAuth service.

    Returns:
        Summary of the sync run.
    """
    user_id = _TEST_USER_ID
    account = await _get_active_email_account(user_id=user_id, session=session)
    sync_service = await _build_sync_service(
        session=session,
        oauth_service=oauth_service,
        email_account_id=account.id,
    )

    sync_log = await sync_service.sync_emails(
        user_id=user_id,
        email_account_id=account.id,
        labels=request.labels or None,
        senders=request.senders or None,
        force_full_sync=request.trigger_full_sync,
    )

    # emails_with_errors is used to track duplicates in the service layer
    return EmailSyncResponse(
        sync_log_id=sync_log.id,
        emails_fetched=sync_log.emails_fetched,
        emails_new=sync_log.emails_processed,
        emails_duplicate=sync_log.emails_with_errors,
        status=sync_log.status,
        message=(
            f"Sync {sync_log.status}. "
            f"Fetched {sync_log.emails_fetched}, "
            f"new {sync_log.emails_processed}, "
            f"duplicate {sync_log.emails_with_errors}."
        ),
    )


@router.get("/status", summary="Get last sync status")
async def get_sync_status(
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Return the most recent :class:`~app.models.system.EmailSyncLog` for the user.

    Args:
        session: Injected DB session.

    Returns:
        A dict with sync log fields, or a message if no sync has been run.
    """
    user_id = _TEST_USER_ID
    stmt = (
        select(EmailSyncLog)
        .where(EmailSyncLog.user_id == user_id)
        .order_by(EmailSyncLog.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    log: EmailSyncLog | None = result.scalar_one_or_none()

    if log is None:
        return {"status": "no_sync", "message": "No sync has been run yet."}

    return {
        "id": log.id,
        "sync_type": log.sync_type,
        "sync_start_time": log.sync_start_time,
        "sync_end_time": log.sync_end_time,
        "emails_fetched": log.emails_fetched,
        "emails_new": log.emails_processed,
        "emails_duplicate": log.emails_with_errors,
        "status": log.status,
        "error_message": log.error_message,
        "history_id_start": log.history_id_start,
        "history_id_end": log.history_id_end,
    }


@router.get("/emails", response_model=EmailListResponse, summary="List fetched emails")
async def list_emails(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    parsed_only: bool = Query(default=False, description="Return only parsed emails"),
    session: AsyncSession = Depends(get_db),
) -> EmailListResponse:
    """Return a paginated list of emails fetched for the current user.

    Args:
        page: 1-indexed page number.
        page_size: Number of items per page (max 100).
        parsed_only: Filter to only emails where ``parsed=True``.
        session: Injected DB session.

    Returns:
        Paginated email list.
    """
    user_id = _TEST_USER_ID

    # We build the query directly here to avoid requiring a GmailService instance
    from sqlalchemy import func  # noqa: PLC0415

    base_stmt = select(Email).where(Email.user_id == user_id)
    count_stmt = select(func.count()).select_from(Email).where(Email.user_id == user_id)

    if parsed_only:
        base_stmt = base_stmt.where(Email.parsed.is_(True))
        count_stmt = count_stmt.where(Email.parsed.is_(True))

    base_stmt = (
        base_stmt.order_by(Email.received_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    total_result = await session.execute(count_stmt)
    total: int = total_result.scalar_one()

    items_result = await session.execute(base_stmt)
    emails = list(items_result.scalars().all())

    return EmailListResponse(
        items=[EmailSchema.model_validate(e) for e in emails],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/emails/{email_id}", response_model=EmailSchema, summary="Get single email")
async def get_email(
    email_id: str,
    session: AsyncSession = Depends(get_db),
) -> EmailSchema:
    """Return a single email by its database ID.

    Args:
        email_id: Database primary key of the email.
        session: Injected DB session.

    Returns:
        The :class:`~app.schemas.email.EmailSchema` for the email.

    Raises:
        :class:`~fastapi.HTTPException` 404: When the email does not exist or
            belongs to a different user.
    """
    user_id = _TEST_USER_ID
    stmt = select(Email).where(Email.id == email_id, Email.user_id == user_id)
    result = await session.execute(stmt)
    email: Email | None = result.scalar_one_or_none()

    if email is None:
        raise HTTPException(status_code=404, detail="Email not found.")

    return EmailSchema.model_validate(email)


@router.post(
    "/emails/{email_id}/reprocess",
    summary="Re-trigger parsing for an email",
)
async def reprocess_email(
    email_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Reset the parse flags for an email so it will be re-parsed on the next run.

    Args:
        email_id: Database primary key of the email to reprocess.
        session: Injected DB session.

    Returns:
        Confirmation dict.

    Raises:
        :class:`~fastapi.HTTPException` 404: When the email does not exist or
            belongs to a different user.
    """
    user_id = _TEST_USER_ID
    stmt = select(Email).where(Email.id == email_id, Email.user_id == user_id)
    result = await session.execute(stmt)
    email: Email | None = result.scalar_one_or_none()

    if email is None:
        raise HTTPException(status_code=404, detail="Email not found.")

    email.parsed = False
    email.parse_attempted = False
    await session.commit()

    logger.info("Email %s queued for reprocessing by user %s", email_id, user_id)
    return {
        "id": email_id,
        "status": "queued",
        "message": "Email has been queued for re-parsing.",
    }
