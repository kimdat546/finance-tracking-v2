"""Email synchronisation service – fetch, filter and persist Gmail messages."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from googleapiclient.errors import HttpError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.models.email import Email, EmailAccount
from app.models.system import EmailSyncLog
from app.services.gmail_service import GmailService
from app.services.oauth_service import OAuthService
from app.utils.email_utils import (
    extract_body_from_payload,
    extract_email_query,
    get_header_value,
    parse_gmail_date,
)

logger = logging.getLogger(__name__)


class EmailSyncService:
    """Email synchronisation service using the Gmail API.

    Uses ``historyId`` for incremental sync (only fetches messages added since the
    last recorded ``historyId``).  Falls back to a full label/sender search when
    ``historyId`` is absent or invalid.

    Attributes:
        DEFAULT_LABELS: Gmail labels searched by default.
        DEFAULT_BATCH_SIZE: Messages requested per Gmail API page.
        MAX_EMAILS_PER_SYNC: Hard cap on messages processed in one sync run.
    """

    DEFAULT_LABELS: list[str] = ["Finance/Cake", "Finance/VPBank"]
    DEFAULT_BATCH_SIZE: int = 100
    MAX_EMAILS_PER_SYNC: int = 5000

    def __init__(
        self,
        session: AsyncSession,
        gmail_service: GmailService,
        oauth_service: OAuthService,
    ) -> None:
        """Initialise the service.

        Args:
            session: Async SQLAlchemy session for all DB operations.
            gmail_service: Pre-authenticated Gmail API wrapper.
            oauth_service: OAuth token management service.
        """
        self._session = session
        self._gmail = gmail_service
        self._oauth = oauth_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def sync_emails(
        self,
        user_id: str,
        email_account_id: str,
        labels: list[str] | None = None,
        senders: list[str] | None = None,
        force_full_sync: bool = False,
    ) -> EmailSyncLog:
        """Synchronise emails for one email account.

        Creates an :class:`~app.models.system.EmailSyncLog` record, runs either
        an incremental or a full sync, and updates the log with the results.

        Args:
            user_id: Owning user's ID.
            email_account_id: ID of the :class:`~app.models.email.EmailAccount` to sync.
            labels: Gmail labels to filter by.  Defaults to :attr:`DEFAULT_LABELS`.
            senders: Sender addresses to filter by.  No sender filter when ``None``.
            force_full_sync: When ``True``, ignore the stored ``historyId`` and
                perform a full search-based sync.

        Returns:
            The completed :class:`~app.models.system.EmailSyncLog` record.
        """
        effective_labels = labels if labels is not None else self.DEFAULT_LABELS
        effective_senders = senders or []

        sync_start_time = datetime.now(timezone.utc).isoformat()
        sync_log = EmailSyncLog(
            user_id=user_id,
            sync_start_time=sync_start_time,
            sync_end_time=None,
            emails_fetched=0,
            emails_processed=0,
            emails_with_errors=0,
            status="running",
        )
        self._session.add(sync_log)
        await self._session.flush()  # get sync_log.id

        try:
            # Fetch the email account to inspect its historyId
            stmt = select(EmailAccount).where(EmailAccount.id == email_account_id)
            result = await self._session.execute(stmt)
            account: EmailAccount | None = result.scalar_one_or_none()

            if account is None:
                raise ValueError(f"EmailAccount {email_account_id} not found")

            history_id = account.history_id
            use_incremental = bool(history_id) and not force_full_sync

            sync_log.sync_type = "incremental" if use_incremental else "full"
            sync_log.history_id_start = history_id

            if use_incremental:
                logger.info(
                    "Starting incremental sync for account %s (historyId=%s)",
                    email_account_id,
                    history_id,
                )
                fetched, new_count, duplicate_count = await self._incremental_sync(
                    user_id=user_id,
                    email_account_id=email_account_id,
                    history_id=history_id,  # type: ignore[arg-type]
                    sync_log_id=sync_log.id,
                )
            else:
                logger.info(
                    "Starting full sync for account %s", email_account_id
                )
                fetched, new_count, duplicate_count = await self._full_sync(
                    user_id=user_id,
                    email_account_id=email_account_id,
                    labels=effective_labels,
                    senders=effective_senders,
                    sync_log_id=sync_log.id,
                )

            # Persist the new historyId from Gmail profile
            try:
                profile = await self._gmail.get_profile()
                new_history_id: str | None = profile.get("historyId")
                if new_history_id:
                    await self._update_history_id(email_account_id, new_history_id)
                    sync_log.history_id_end = new_history_id
            except Exception:
                logger.warning(
                    "Could not refresh historyId for account %s", email_account_id
                )

            sync_log.emails_fetched = fetched
            sync_log.emails_processed = new_count
            sync_log.emails_with_errors = duplicate_count
            sync_log.status = "completed"
            sync_log.sync_end_time = datetime.now(timezone.utc).isoformat()

            await self._session.commit()
            await self._session.refresh(sync_log)
            logger.info(
                "Sync completed for account %s: fetched=%d new=%d duplicate=%d",
                email_account_id,
                fetched,
                new_count,
                duplicate_count,
            )

        except Exception as exc:
            logger.exception("Sync failed for account %s: %s", email_account_id, exc)
            sync_log.status = "failed"
            sync_log.error_message = str(exc)
            sync_log.sync_end_time = datetime.now(timezone.utc).isoformat()
            await self._session.commit()
            await self._session.refresh(sync_log)

        return sync_log

    async def get_emails(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        parsed_only: bool = False,
    ) -> tuple[list[Email], int]:
        """Return a paginated list of emails for a user.

        Args:
            user_id: Owning user's ID.
            page: 1-indexed page number.
            page_size: Number of items per page.
            parsed_only: When ``True``, only return emails where ``parsed=True``.

        Returns:
            A ``(items, total)`` tuple where *items* is the current page of
            :class:`~app.models.email.Email` objects and *total* is the overall
            count matching the filter.
        """
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

        total_result = await self._session.execute(count_stmt)
        total: int = total_result.scalar_one()

        items_result = await self._session.execute(base_stmt)
        items = list(items_result.scalars().all())

        return items, total

    # ------------------------------------------------------------------
    # Sync strategies
    # ------------------------------------------------------------------

    async def _incremental_sync(
        self,
        user_id: str,
        email_account_id: str,
        history_id: str,
        sync_log_id: str,
    ) -> tuple[int, int, int]:
        """Sync only messages added since *history_id*.

        Falls back to a full sync when the Gmail API reports that the
        provided ``historyId`` is no longer valid (HTTP 404).

        Args:
            user_id: Owning user's ID.
            email_account_id: Email account being synced.
            history_id: The ``historyId`` to start from.
            sync_log_id: Primary key of the running sync log.

        Returns:
            ``(fetched, new, duplicate)`` counts.
        """
        try:
            history_response = await self._fetch_history_with_retry(history_id)
        except HttpError as exc:
            if exc.resp.status == 404:
                logger.warning(
                    "historyId %s is stale (404), falling back to full sync", history_id
                )
                return await self._full_sync(
                    user_id=user_id,
                    email_account_id=email_account_id,
                    labels=self.DEFAULT_LABELS,
                    senders=[],
                    sync_log_id=sync_log_id,
                )
            raise

        history_records: list[dict] = history_response.get("history", [])
        message_ids: list[str] = []

        for record in history_records:
            for msg_added in record.get("messagesAdded", []):
                msg_id = msg_added.get("message", {}).get("id")
                if msg_id and msg_id not in message_ids:
                    message_ids.append(msg_id)

        if not message_ids:
            logger.info("Incremental sync: no new message IDs found")
            return 0, 0, 0

        fetched = len(message_ids)
        new_count, duplicate_count = await self._process_messages(
            message_ids=message_ids,
            user_id=user_id,
            email_account_id=email_account_id,
            sync_log_id=sync_log_id,
        )
        return fetched, new_count, duplicate_count

    async def _full_sync(
        self,
        user_id: str,
        email_account_id: str,
        labels: list[str],
        senders: list[str],
        sync_log_id: str,
    ) -> tuple[int, int, int]:
        """Fetch all matching messages via a label/sender search query.

        Paginates through Gmail results up to :attr:`MAX_EMAILS_PER_SYNC`.

        Args:
            user_id: Owning user's ID.
            email_account_id: Email account being synced.
            labels: Gmail labels to filter by.
            senders: Sender addresses to filter by.
            sync_log_id: Primary key of the running sync log.

        Returns:
            ``(fetched, new, duplicate)`` counts.
        """
        query = extract_email_query(labels, senders)
        logger.info("Full sync query: %r", query)

        all_message_ids: list[str] = []
        page_token: str | None = None

        while len(all_message_ids) < self.MAX_EMAILS_PER_SYNC:
            response = await self._list_messages_with_retry(
                query=query,
                max_results=self.DEFAULT_BATCH_SIZE,
                page_token=page_token,
            )
            messages: list[dict] = response.get("messages", [])
            for msg in messages:
                msg_id = msg.get("id")
                if msg_id and msg_id not in all_message_ids:
                    all_message_ids.append(msg_id)

            page_token = response.get("nextPageToken")
            if not page_token or not messages:
                break

        fetched = len(all_message_ids)
        if fetched == 0:
            logger.info("Full sync: no messages found for query %r", query)
            return 0, 0, 0

        new_count, duplicate_count = await self._process_messages(
            message_ids=all_message_ids,
            user_id=user_id,
            email_account_id=email_account_id,
            sync_log_id=sync_log_id,
        )
        return fetched, new_count, duplicate_count

    # ------------------------------------------------------------------
    # Message processing
    # ------------------------------------------------------------------

    async def _process_messages(
        self,
        message_ids: list[str],
        user_id: str,
        email_account_id: str,
        sync_log_id: str,
    ) -> tuple[int, int]:
        """Fetch full message details and persist new emails.

        Args:
            message_ids: Gmail message IDs to process.
            user_id: Owning user's ID.
            email_account_id: Email account being synced.
            sync_log_id: Primary key of the running sync log.

        Returns:
            ``(new, duplicate)`` counts.
        """
        new_count = 0
        duplicate_count = 0

        for message_id in message_ids:
            # Check if we already have this message
            existing_stmt = select(Email).where(
                Email.user_id == user_id,
                Email.gmail_message_id == message_id,
            )
            existing_result = await self._session.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing is not None:
                duplicate_count += 1
                logger.debug("Skipping duplicate message %s", message_id)
                continue

            try:
                full_message = await self._get_message_with_retry(message_id)
            except Exception:
                logger.warning("Could not fetch message %s, skipping", message_id)
                continue

            is_new, _ = await self._save_email(
                message=full_message,
                user_id=user_id,
                email_account_id=email_account_id,
                sync_log_id=sync_log_id,
            )
            if is_new:
                new_count += 1
            else:
                duplicate_count += 1

        return new_count, duplicate_count

    async def _save_email(
        self,
        message: dict,
        user_id: str,
        email_account_id: str,
        sync_log_id: str,
    ) -> tuple[bool, bool]:
        """Persist a Gmail message as an :class:`~app.models.email.Email` row.

        Skips the insert and returns ``(False, True)`` when the message already
        exists (identified by ``(user_id, gmail_message_id)``).

        Args:
            message: Full Gmail message resource dict.
            user_id: Owning user's ID.
            email_account_id: Email account the message belongs to.
            sync_log_id: Primary key of the running sync log.

        Returns:
            ``(is_new, is_duplicate)`` where exactly one value is ``True``.
        """
        gmail_message_id: str = message.get("id", "")
        if not gmail_message_id:
            logger.warning("Message has no 'id' field, skipping")
            return False, False

        # Double-check for race conditions
        check_stmt = select(Email).where(
            Email.user_id == user_id,
            Email.gmail_message_id == gmail_message_id,
        )
        check_result = await self._session.execute(check_stmt)
        if check_result.scalar_one_or_none() is not None:
            return False, True

        payload: dict = message.get("payload", {})
        headers: list[dict] = payload.get("headers", [])

        sender = get_header_value(headers, "From")
        subject = get_header_value(headers, "Subject")
        date_str = get_header_value(headers, "Date")

        received_at: datetime | None = None
        if date_str:
            try:
                received_at = parse_gmail_date(date_str)
            except ValueError:
                logger.warning("Cannot parse date header %r for message %s", date_str, gmail_message_id)

        html_body, text_body = extract_body_from_payload(payload)

        email_record = Email(
            user_id=user_id,
            email_account_id=email_account_id,
            gmail_message_id=gmail_message_id,
            sender=sender,
            subject=subject,
            received_at=received_at,
            raw_html_body=html_body or None,
            raw_text_body=text_body or None,
            parsed=False,
            parse_attempted=False,
            sync_log_id=sync_log_id,
            fingerprint=None,
            is_duplicate=False,
        )
        self._session.add(email_record)
        await self._session.flush()

        logger.debug(
            "Saved new email: gmail_id=%s subject=%r", gmail_message_id, subject
        )
        return True, False

    # ------------------------------------------------------------------
    # History ID management
    # ------------------------------------------------------------------

    async def _update_history_id(self, email_account_id: str, history_id: str) -> None:
        """Persist a new ``historyId`` to the email account record.

        Args:
            email_account_id: Primary key of the :class:`~app.models.email.EmailAccount`.
            history_id: New Gmail ``historyId`` string.
        """
        stmt = select(EmailAccount).where(EmailAccount.id == email_account_id)
        result = await self._session.execute(stmt)
        account = result.scalar_one_or_none()
        if account is not None:
            account.history_id = history_id
            await self._session.flush()
            logger.debug(
                "Updated historyId for account %s -> %s", email_account_id, history_id
            )

    # ------------------------------------------------------------------
    # Retry-wrapped Gmail calls
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _get_message_with_retry(self, message_id: str) -> dict:
        """Fetch a single Gmail message, retrying up to 3 times on failure.

        Args:
            message_id: The Gmail message ID.

        Returns:
            The Gmail message resource dict.
        """
        return await self._gmail.get_message(message_id, format="full")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _list_messages_with_retry(
        self,
        query: str,
        max_results: int,
        page_token: str | None,
    ) -> dict:
        """List Gmail messages matching *query*, retrying up to 3 times on failure.

        Args:
            query: Gmail search query string.
            max_results: Maximum messages per API call.
            page_token: Pagination token from a previous response.

        Returns:
            The Gmail messages.list response dict.
        """
        return await self._gmail.list_messages(
            query=query,
            max_results=max_results,
            page_token=page_token,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _fetch_history_with_retry(self, start_history_id: str) -> dict:
        """Fetch Gmail history records, retrying up to 3 times on failure.

        Args:
            start_history_id: The ``historyId`` to start from.

        Returns:
            The Gmail history.list response dict.
        """
        return await self._gmail.list_history(start_history_id=start_history_id)
