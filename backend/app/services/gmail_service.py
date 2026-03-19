"""Gmail API client wrapper providing async access to Gmail resources."""

import asyncio
import base64
import logging
from collections.abc import Callable
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

logger = logging.getLogger(__name__)

_GMAIL_API_SERVICE = "gmail"
_GMAIL_API_VERSION = "v1"
_GMAIL_USER_ID = "me"


class GmailService:
    """Async wrapper around the Google Gmail API client.

    All Google API calls are synchronous; they are dispatched to a thread-pool
    executor so that the event loop is never blocked.

    Attributes:
        _credentials: Google OAuth2 credentials used to authenticate API calls.
    """

    def __init__(self, credentials: Credentials) -> None:
        """Initialize the GmailService.

        Args:
            credentials: A valid :class:`~google.oauth2.credentials.Credentials` object.
        """
        self._credentials = credentials

    # ------------------------------------------------------------------
    # Client construction
    # ------------------------------------------------------------------

    def build_client(self) -> Resource:
        """Build and return a synchronous Gmail API Resource.

        Returns:
            A :class:`~googleapiclient.discovery.Resource` bound to the Gmail API v1.
        """
        return build(
            _GMAIL_API_SERVICE,
            _GMAIL_API_VERSION,
            credentials=self._credentials,
            cache_discovery=False,
        )

    # ------------------------------------------------------------------
    # Async execution helper
    # ------------------------------------------------------------------

    async def _run_sync(self, func: Callable[[], Any]) -> Any:
        """Run a synchronous callable in the default executor.

        Args:
            func: A zero-argument callable that performs a synchronous operation.

        Returns:
            The return value of *func*.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)

    # ------------------------------------------------------------------
    # Gmail API methods
    # ------------------------------------------------------------------

    async def get_profile(self) -> dict:
        """Retrieve the authenticated user's Gmail profile.

        Returns:
            A dict with keys such as ``emailAddress``, ``messagesTotal``,
            ``threadsTotal``, and ``historyId``.
        """
        client = self.build_client()

        def _call() -> dict:
            return client.users().getProfile(userId=_GMAIL_USER_ID).execute()

        result: dict = await self._run_sync(_call)
        logger.debug("Gmail profile fetched: %s", result.get("emailAddress"))
        return result

    async def list_messages(
        self,
        query: str = "",
        max_results: int = 100,
        page_token: str | None = None,
    ) -> dict:
        """List Gmail messages matching *query*.

        Args:
            query: A Gmail search query string (e.g. ``"from:bank@example.com"``).
            max_results: Maximum number of messages to return (1–500).
            page_token: Token for fetching the next page of results.

        Returns:
            A dict with keys ``messages`` (list of ``{id, threadId}`` dicts),
            ``nextPageToken`` (optional), and ``resultSizeEstimate``.
        """
        client = self.build_client()

        def _call() -> dict:
            kwargs: dict[str, Any] = {
                "userId": _GMAIL_USER_ID,
                "maxResults": max_results,
                "q": query,
            }
            if page_token:
                kwargs["pageToken"] = page_token
            return client.users().messages().list(**kwargs).execute()

        result: dict = await self._run_sync(_call)
        logger.debug(
            "list_messages returned %d messages",
            len(result.get("messages", [])),
        )
        return result

    async def get_message(self, message_id: str, format: str = "full") -> dict:
        """Fetch a single Gmail message by ID.

        Args:
            message_id: The Gmail message ID.
            format: The message format; one of ``"full"``, ``"metadata"``,
                ``"minimal"``, or ``"raw"``.

        Returns:
            The Gmail message resource as a dict.
        """
        client = self.build_client()

        def _call() -> dict:
            return (
                client.users()
                .messages()
                .get(userId=_GMAIL_USER_ID, id=message_id, format=format)
                .execute()
            )

        result: dict = await self._run_sync(_call)
        logger.debug("Fetched message %s (format=%s)", message_id, format)
        return result

    async def list_history(
        self,
        start_history_id: str,
        max_results: int = 500,
    ) -> dict:
        """List Gmail history records starting from *start_history_id*.

        Args:
            start_history_id: The Gmail ``historyId`` to start listing from.
            max_results: Maximum number of history records to return.

        Returns:
            A dict with keys ``history`` (list of history records),
            ``nextPageToken`` (optional), and ``historyId``.
        """
        client = self.build_client()

        def _call() -> dict:
            return (
                client.users()
                .history()
                .list(
                    userId=_GMAIL_USER_ID,
                    startHistoryId=start_history_id,
                    maxResults=max_results,
                )
                .execute()
            )

        result: dict = await self._run_sync(_call)
        logger.debug(
            "list_history from %s returned %d records",
            start_history_id,
            len(result.get("history", [])),
        )
        return result

    # ------------------------------------------------------------------
    # Message body extraction
    # ------------------------------------------------------------------

    async def get_message_body(self, message: dict) -> tuple[str, str]:
        """Extract HTML and plain-text bodies from a Gmail message resource.

        Recursively searches through MIME parts for ``text/html`` and
        ``text/plain`` content, decoding base64url-encoded data.

        Args:
            message: A Gmail message dict as returned by :meth:`get_message`
                with ``format="full"``.

        Returns:
            A ``(html_body, text_body)`` tuple.  Either value may be an empty
            string if the corresponding MIME part is absent.
        """
        payload: dict = message.get("payload", {})
        html_body, text_body = self._extract_parts(payload)
        return html_body, text_body

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _decode_base64url(self, data: str) -> str:
        """Decode a base64url-encoded string to a UTF-8 string.

        Args:
            data: A base64url-encoded byte string (may omit padding).

        Returns:
            The decoded UTF-8 string, or an empty string on failure.
        """
        try:
            # Add padding if necessary
            padded = data + "=" * (4 - len(data) % 4)
            decoded_bytes = base64.urlsafe_b64decode(padded)
            return decoded_bytes.decode("utf-8", errors="replace")
        except Exception:
            logger.warning("Failed to decode base64url data")
            return ""

    def _extract_parts(self, payload: dict) -> tuple[str, str]:
        """Recursively extract HTML and text bodies from a MIME payload.

        Args:
            payload: A Gmail message payload dict that may contain ``parts``.

        Returns:
            A ``(html_body, text_body)`` tuple.
        """
        mime_type: str = payload.get("mimeType", "")
        body: dict = payload.get("body", {})
        parts: list[dict] = payload.get("parts", [])

        html_body = ""
        text_body = ""

        if mime_type == "text/html":
            data = body.get("data", "")
            if data:
                html_body = self._decode_base64url(data)
        elif mime_type == "text/plain":
            data = body.get("data", "")
            if data:
                text_body = self._decode_base64url(data)
        else:
            # Recurse into multipart/* or other containers
            for part in parts:
                part_html, part_text = self._extract_parts(part)
                if part_html and not html_body:
                    html_body = part_html
                if part_text and not text_body:
                    text_body = part_text

        return html_body, text_body
