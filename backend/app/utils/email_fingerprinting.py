"""Email fingerprinting utilities for deduplication of bank notification emails."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import Email

logger = logging.getLogger(__name__)


def generate_email_fingerprint(
    sender: str,
    amount: float,
    date: datetime | str,
    merchant: str | None,
    user_id: str,
) -> str:
    """Generate a SHA-256 fingerprint from email transaction data.

    The fingerprint is deterministic: the same inputs always produce the same
    hash. Components are joined with ``|`` in the order:
    ``sender|amount|date_normalized|merchant_normalized|user_id``.

    Date is normalised to ``YYYY-MM-DD`` (date-only) to absorb timezone
    differences between otherwise identical emails.  Merchant is lower-cased
    and stripped of leading/trailing whitespace.

    Args:
        sender: Email sender address.
        amount: Transaction amount as a float.
        date: Transaction date as a :class:`datetime` or an ISO-format string.
        merchant: Optional merchant/counterparty name.
        user_id: ID of the owning user.

    Returns:
        64-character lowercase hex SHA-256 digest.
    """
    # Normalise date to YYYY-MM-DD string
    if isinstance(date, datetime):
        date_normalized = date.date().isoformat()
    else:
        # Accept ISO strings like "2026-03-15T10:30:00" or plain "2026-03-15"
        try:
            date_normalized = datetime.fromisoformat(str(date)).date().isoformat()
        except ValueError:
            date_normalized = str(date)[:10]

    # Normalise merchant: lowercase, strip, collapse spaces
    if merchant:
        merchant_normalized = " ".join(merchant.lower().split())
    else:
        merchant_normalized = ""

    key = f"{sender.lower()}|{amount:.2f}|{date_normalized}|{merchant_normalized}|{user_id}"
    return hashlib.sha256(key.encode()).hexdigest()


def generate_raw_fingerprint(raw_content: str, sender: str, user_id: str) -> str:
    """Generate a fingerprint from raw email content (fallback).

    Use this when amount or merchant cannot be extracted from the email.

    Args:
        raw_content: Raw email body content.  Only the first 500 characters
            are used to keep the key deterministic even if trailing content
            varies.
        sender: Email sender address.
        user_id: ID of the owning user.

    Returns:
        64-character lowercase hex SHA-256 digest.
    """
    key = f"{sender.lower()}|{raw_content[:500]}|{user_id}"
    return hashlib.sha256(key.encode()).hexdigest()


def is_within_dedup_window(
    existing_time: datetime,
    new_time: datetime,
    window_hours: int = 24,
) -> bool:
    """Check whether two email timestamps fall within a deduplication window.

    Args:
        existing_time: Timestamp of the already-stored email.
        new_time: Timestamp of the candidate email.
        window_hours: Maximum allowable gap in hours (default 24).

    Returns:
        ``True`` if the absolute difference is strictly less than
        *window_hours* × 3600 seconds.
    """
    delta = abs((new_time - existing_time).total_seconds())
    return delta < window_hours * 3600


class EmailDeduplicator:
    """Service for detecting and managing duplicate bank-notification emails.

    All database operations are performed asynchronously via SQLAlchemy's
    async session.

    Args:
        session: An active :class:`~sqlalchemy.ext.asyncio.AsyncSession`.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the deduplicator with a database session."""
        self._session = session

    async def check_duplicate(
        self,
        fingerprint: str,
        user_id: str,
        received_at: datetime,
    ) -> bool:
        """Check whether an email with this fingerprint already exists.

        Looks for a non-duplicate :class:`~app.models.email.Email` row that
        shares the same ``fingerprint`` and ``user_id`` and whose
        ``received_at`` timestamp is within the 24-hour deduplication window.

        Args:
            fingerprint: SHA-256 fingerprint to look up.
            user_id: ID of the owning user.
            received_at: Timestamp of the candidate email.

        Returns:
            ``True`` if a matching record is found within the window.
        """
        stmt = select(Email).where(
            (Email.fingerprint == fingerprint)
            & (Email.user_id == user_id)
            & (Email.is_duplicate == False)  # noqa: E712
        )
        result = await self._session.execute(stmt)
        existing_emails = result.scalars().all()

        for email in existing_emails:
            if email.received_at and is_within_dedup_window(email.received_at, received_at):
                return True

        return False

    async def mark_as_duplicate(self, email_id: str) -> None:
        """Mark a specific email record as a duplicate.

        Args:
            email_id: Primary-key ID of the :class:`~app.models.email.Email`
                row to mark.
        """
        stmt = select(Email).where(Email.id == email_id)
        result = await self._session.execute(stmt)
        email = result.scalar_one_or_none()

        if email is not None:
            email.is_duplicate = True
            await self._session.commit()
            logger.debug("Marked email %s as duplicate", email_id)
        else:
            logger.warning("Attempted to mark non-existent email %s as duplicate", email_id)

    async def get_duplicate_count(self, user_id: str) -> int:
        """Count duplicate emails for a given user.

        Args:
            user_id: ID of the owning user.

        Returns:
            Number of emails where ``is_duplicate`` is ``True``.
        """
        stmt = select(func.count()).select_from(Email).where(
            (Email.user_id == user_id) & (Email.is_duplicate == True)  # noqa: E712
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def cleanup_old_duplicates(
        self,
        user_id: str,
        older_than_days: int = 30,
    ) -> int:
        """Delete duplicate emails older than the specified number of days.

        Args:
            user_id: ID of the owning user.
            older_than_days: Emails created more than this many days ago are
                eligible for deletion (default 30).

        Returns:
            Number of rows deleted.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        # Count first so we can return how many were deleted
        count_stmt = select(func.count()).select_from(Email).where(
            (Email.user_id == user_id)
            & (Email.is_duplicate == True)  # noqa: E712
            & (Email.created_at < cutoff)
        )
        count_result = await self._session.execute(count_stmt)
        count = count_result.scalar() or 0

        if count > 0:
            del_stmt = delete(Email).where(
                (Email.user_id == user_id)
                & (Email.is_duplicate == True)  # noqa: E712
                & (Email.created_at < cutoff)
            )
            await self._session.execute(del_stmt)
            await self._session.commit()
            logger.info("Deleted %d old duplicate emails for user %s", count, user_id)

        return count
