"""Service for managing emails that could not be parsed by any parser."""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import UnrecognizedEmail


class UnrecognizedEmailService:
    """Service for managing emails that couldn't be parsed."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: Async SQLAlchemy session.
        """
        self._session = session

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def record_unrecognized(
        self,
        user_id: str,
        email_id: str,
        sender: str,
        subject: str,
        received_at: str,
        raw_body: str | None = None,
        parse_error: str | None = None,
        parsed_attempt: dict | None = None,
    ) -> UnrecognizedEmail:
        """Record an email that couldn't be parsed.

        If the combination of ``email_id`` + ``user_id`` already exists the
        existing record is updated rather than creating a duplicate.

        Args:
            user_id: Owner of the email.
            email_id: Unique identifier of the original email.
            sender: Sender address.
            subject: Email subject line.
            received_at: ISO-formatted date/time the email was received.
            raw_body: Full email body text.
            parse_error: Human-readable reason the email could not be parsed.
            parsed_attempt: Partial extraction result as a Python dict.

        Returns:
            The created or updated :class:`UnrecognizedEmail` record.
        """
        parsed_attempt_str: str | None = None
        if parsed_attempt is not None:
            parsed_attempt_str = json.dumps(parsed_attempt)

        existing = await self.get_by_email_id(email_id, user_id)
        if existing is not None:
            existing.sender = sender
            existing.subject = subject
            existing.received_at = received_at
            if raw_body is not None:
                existing.raw_body = raw_body
            if parse_error is not None:
                existing.parse_error = parse_error
            if parsed_attempt_str is not None:
                existing.parsed_attempt = parsed_attempt_str
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        record = UnrecognizedEmail(
            user_id=user_id,
            email_id=email_id,
            sender=sender,
            subject=subject,
            received_at=received_at,
            raw_body=raw_body,
            parse_error=parse_error,
            parsed_attempt=parsed_attempt_str,
            status="pending",
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def mark_as_ignored(
        self, email_id: str, user_id: str
    ) -> UnrecognizedEmail | None:
        """Mark an unrecognized email as ignored.

        Args:
            email_id: Record ID (primary key).
            user_id: Owner of the record.

        Returns:
            Updated record, or ``None`` if not found.
        """
        record = await self.get_by_id(email_id, user_id)
        if record is None:
            return None
        record.status = "ignored"
        record.is_processed = True
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def mark_as_categorized(
        self,
        email_id: str,
        user_id: str,
        category: str,
        amount: str | None = None,
        notes: str | None = None,
    ) -> UnrecognizedEmail | None:
        """Manually categorize an unrecognized email.

        Sets ``status`` to ``'categorized'`` and persists the supplied
        ``manual_category``, ``manual_amount`` and ``notes``.

        Args:
            email_id: Record ID (primary key).
            user_id: Owner of the record.
            category: Category name to assign.
            amount: Optional manually-entered amount string.
            notes: Optional free-text notes.

        Returns:
            Updated record, or ``None`` if not found.
        """
        record = await self.get_by_id(email_id, user_id)
        if record is None:
            return None
        record.status = "categorized"
        record.is_processed = True
        record.manual_category = category
        if amount is not None:
            record.manual_amount = amount
        if notes is not None:
            record.notes = notes
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def bulk_update_status(
        self,
        user_id: str,
        email_ids: list[str],
        status: str,
    ) -> int:
        """Bulk update the status of multiple unrecognized email records.

        Args:
            user_id: Owner of the records.
            email_ids: Primary-key IDs of records to update.
            status: New status value.

        Returns:
            Number of rows actually updated.
        """
        if not email_ids:
            return 0
        stmt = (
            update(UnrecognizedEmail)
            .where(
                UnrecognizedEmail.user_id == user_id,
                UnrecognizedEmail.id.in_(email_ids),
            )
            .values(status=status)
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount  # type: ignore[return-value]

    async def delete_by_ids(self, user_id: str, email_ids: list[str]) -> int:
        """Delete unrecognized email records by their IDs.

        Args:
            user_id: Owner of the records.
            email_ids: Primary-key IDs of records to delete.

        Returns:
            Number of rows deleted.
        """
        if not email_ids:
            return 0
        stmt = delete(UnrecognizedEmail).where(
            UnrecognizedEmail.user_id == user_id,
            UnrecognizedEmail.id.in_(email_ids),
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_by_id(
        self, email_id: str, user_id: str
    ) -> UnrecognizedEmail | None:
        """Fetch a single unrecognized email record by its primary-key ID.

        Args:
            email_id: Record primary-key ID.
            user_id: Owner of the record.

        Returns:
            The record, or ``None`` if not found.
        """
        stmt = select(UnrecognizedEmail).where(
            UnrecognizedEmail.id == email_id,
            UnrecognizedEmail.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_id(
        self, email_id: str, user_id: str
    ) -> UnrecognizedEmail | None:
        """Fetch a record by its original email ID (not the PK).

        Args:
            email_id: Value of the ``email_id`` column.
            user_id: Owner of the record.

        Returns:
            The record, or ``None`` if not found.
        """
        stmt = select(UnrecognizedEmail).where(
            UnrecognizedEmail.email_id == email_id,
            UnrecognizedEmail.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_unrecognized(
        self,
        user_id: str,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[UnrecognizedEmail], int]:
        """List unrecognized emails with optional status filtering.

        Args:
            user_id: Owner of the records.
            status: Optional status to filter by.
            page: 1-based page number.
            page_size: Number of items per page.

        Returns:
            A tuple of ``(items, total_count)``.
        """
        base_where = [UnrecognizedEmail.user_id == user_id]
        if status is not None:
            base_where.append(UnrecognizedEmail.status == status)

        count_stmt = select(func.count()).select_from(UnrecognizedEmail).where(*base_where)
        total: int = (await self._session.execute(count_stmt)).scalar() or 0

        offset = (page - 1) * page_size
        items_stmt = (
            select(UnrecognizedEmail)
            .where(*base_where)
            .order_by(UnrecognizedEmail.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = await self._session.execute(items_stmt)
        items = list(rows.scalars().all())
        return items, total

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_analytics(self, user_id: str) -> dict:
        """Get analytics about unrecognized emails for a given user.

        Returns a dictionary with the following keys:

        - ``total``: Total number of unrecognized email records.
        - ``by_status``: Mapping of status value to count.
        - ``by_sender``: List of ``{"sender": str, "count": int}`` dicts,
          sorted descending by count (top 20 senders).
        - ``rate_last_7_days``: Approximate unrecognized rate calculated as
          ``emails_created_in_last_7_days / 100.0``.

        Args:
            user_id: Owner of the records.

        Returns:
            Analytics dictionary.
        """
        # Total
        total_stmt = (
            select(func.count())
            .select_from(UnrecognizedEmail)
            .where(UnrecognizedEmail.user_id == user_id)
        )
        total: int = (await self._session.execute(total_stmt)).scalar() or 0

        # By status
        status_stmt = (
            select(UnrecognizedEmail.status, func.count().label("cnt"))
            .where(UnrecognizedEmail.user_id == user_id)
            .group_by(UnrecognizedEmail.status)
        )
        status_rows = (await self._session.execute(status_stmt)).all()
        by_status: dict[str, int] = {
            "pending": 0,
            "ignored": 0,
            "categorized": 0,
            "rule_created": 0,
        }
        for row in status_rows:
            by_status[row[0]] = row[1]

        # By sender (top 20)
        sender_stmt = (
            select(UnrecognizedEmail.sender, func.count().label("cnt"))
            .where(UnrecognizedEmail.user_id == user_id)
            .group_by(UnrecognizedEmail.sender)
            .order_by(func.count().desc())
            .limit(20)
        )
        sender_rows = (await self._session.execute(sender_stmt)).all()
        by_sender = [{"sender": row[0], "count": row[1]} for row in sender_rows]

        # Rate last 7 days (simple approximation)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent_stmt = (
            select(func.count())
            .select_from(UnrecognizedEmail)
            .where(
                UnrecognizedEmail.user_id == user_id,
                UnrecognizedEmail.created_at >= cutoff,
            )
        )
        recent_count: int = (await self._session.execute(recent_stmt)).scalar() or 0
        rate_last_7_days: float = recent_count / 100.0

        return {
            "total": total,
            "by_status": by_status,
            "by_sender": by_sender,
            "rate_last_7_days": rate_last_7_days,
        }

    # ------------------------------------------------------------------
    # Rule suggestions
    # ------------------------------------------------------------------

    async def suggest_parser_rules(
        self,
        unrecognized_id: str,
        user_id: str,
    ) -> list[dict]:
        """Suggest parser rules based on email content.

        Analyses the ``sender``, ``subject`` and ``raw_body`` of the
        unrecognized email and returns a list of candidate rules.

        Each suggestion has the shape::

            {"field": str, "pattern": str, "confidence": float}

        Args:
            unrecognized_id: Primary-key ID of the unrecognized email record.
            user_id: Owner of the record.

        Returns:
            List of rule suggestion dicts, or an empty list if the record is
            not found.
        """
        record = await self.get_by_id(unrecognized_id, user_id)
        if record is None:
            return []

        suggestions: list[dict] = []

        # --- Sender rule ---
        if record.sender:
            # Escape the literal sender for use as a regex pattern
            escaped = re.escape(record.sender)
            suggestions.append(
                {"field": "sender", "pattern": escaped, "confidence": 0.95}
            )

        # --- Subject keyword rule ---
        if record.subject:
            # Extract words ≥ 4 chars from the subject as candidate keywords
            keywords = re.findall(r"[A-Za-z]{4,}", record.subject)
            if keywords:
                keyword_pattern = "|".join(re.escape(k) for k in keywords[:5])
                suggestions.append(
                    {
                        "field": "subject",
                        "pattern": keyword_pattern,
                        "confidence": 0.75,
                    }
                )

        # --- Amount patterns from raw_body ---
        body = record.raw_body or ""
        if body:
            # Common amount formats: 1,234.56 / 1.234,56 / 1234
            amount_pattern = r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)"
            if re.search(amount_pattern, body):
                suggestions.append(
                    {
                        "field": "amount",
                        "pattern": amount_pattern,
                        "confidence": 0.8,
                    }
                )

            # Date-like patterns
            date_pattern = r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"
            if re.search(date_pattern, body):
                suggestions.append(
                    {
                        "field": "date",
                        "pattern": date_pattern,
                        "confidence": 0.7,
                    }
                )

            # Reference / transaction ID patterns
            ref_pattern = r"(?:ref|id|transaction)[^\w]*([A-Z0-9]{6,})"
            if re.search(ref_pattern, body, re.IGNORECASE):
                suggestions.append(
                    {
                        "field": "reference",
                        "pattern": ref_pattern,
                        "confidence": 0.65,
                    }
                )

        return suggestions

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def export_emails(
        self,
        user_id: str,
        format: str = "json",
        status: str | None = None,
    ) -> str:
        """Export unrecognized email records as a JSON or CSV string.

        All matching records are retrieved (no pagination limit) and serialised
        to the requested format.

        Args:
            user_id: Owner of the records.
            format: ``'json'`` (default) or ``'csv'``.
            status: Optional status filter.

        Returns:
            Serialised string in the requested format.
        """
        # Fetch all matching records (no page limit for export)
        base_where = [UnrecognizedEmail.user_id == user_id]
        if status is not None:
            base_where.append(UnrecognizedEmail.status == status)

        stmt = (
            select(UnrecognizedEmail)
            .where(*base_where)
            .order_by(UnrecognizedEmail.created_at.desc())
        )
        rows = await self._session.execute(stmt)
        records = list(rows.scalars().all())

        if format == "csv":
            return self._to_csv(records)
        return self._to_json(records)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _record_to_dict(record: UnrecognizedEmail) -> dict:
        """Serialise an :class:`UnrecognizedEmail` to a plain dictionary."""
        return {
            "id": record.id,
            "user_id": record.user_id,
            "email_id": record.email_id,
            "sender": record.sender,
            "subject": record.subject,
            "received_at": record.received_at,
            "status": record.status,
            "parse_error": record.parse_error,
            "manual_category": record.manual_category,
            "manual_amount": record.manual_amount,
            "notes": record.notes,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

    def _to_json(self, records: list[UnrecognizedEmail]) -> str:
        """Serialise records to a JSON string."""
        return json.dumps([self._record_to_dict(r) for r in records], ensure_ascii=False)

    def _to_csv(self, records: list[UnrecognizedEmail]) -> str:
        """Serialise records to a CSV string."""
        if not records:
            return ""
        fieldnames = list(self._record_to_dict(records[0]).keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(self._record_to_dict(r))
        return buf.getvalue()
