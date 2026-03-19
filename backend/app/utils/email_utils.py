"""Utility functions for parsing and processing Gmail message payloads."""

from __future__ import annotations

import base64
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)


def extract_email_query(labels: list[str], senders: list[str]) -> str:
    """Build a Gmail search query from label and sender filters.

    Combines labels with OR inside parentheses and senders with OR inside
    parentheses, then ANDs the two groups together.

    Args:
        labels: Gmail label names, e.g. ``["Finance/Cake", "Finance/VPBank"]``.
        senders: Sender email addresses, e.g. ``["cake@example.com"]``.

    Returns:
        A Gmail search query string, e.g.
        ``"(label:Finance/Cake OR label:Finance/VPBank) (from:cake@example.com)"``.
        If only labels are provided, only the label group is returned.
        If only senders are provided, only the sender group is returned.
        If neither is provided, an empty string is returned.

    Examples:
        >>> extract_email_query(["Finance/Cake"], [])
        '(label:Finance/Cake)'
        >>> extract_email_query(["Finance/Cake"], ["no-reply@cake.vn"])
        '(label:Finance/Cake) (from:no-reply@cake.vn)'
    """
    parts: list[str] = []

    if labels:
        label_parts = " OR ".join(f"label:{lbl}" for lbl in labels)
        parts.append(f"({label_parts})")

    if senders:
        sender_parts = " OR ".join(f"from:{addr}" for addr in senders)
        parts.append(f"({sender_parts})")

    return " ".join(parts)


def decode_base64url(data: str) -> bytes:
    """Decode a base64url-encoded string to raw bytes.

    Handles the URL-safe variant of base64 (``-`` and ``_`` instead of
    ``+`` and ``/``) and automatically adds the required ``=`` padding.

    Args:
        data: A base64url-encoded string, possibly without padding.

    Returns:
        The decoded bytes.

    Raises:
        Exception: Propagates any decoding error from :func:`base64.urlsafe_b64decode`.
    """
    # Add padding to make the length a multiple of 4
    padding_needed = (4 - len(data) % 4) % 4
    padded = data + "=" * padding_needed
    return base64.urlsafe_b64decode(padded)


def _extract_parts_recursive(payload: dict) -> tuple[str, str]:
    """Recursively walk a MIME payload and collect HTML / plain-text bodies.

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
            try:
                html_body = decode_base64url(data).decode("utf-8", errors="replace")
            except Exception:
                logger.warning("Failed to decode HTML body part")
    elif mime_type == "text/plain":
        data = body.get("data", "")
        if data:
            try:
                text_body = decode_base64url(data).decode("utf-8", errors="replace")
            except Exception:
                logger.warning("Failed to decode text body part")
    else:
        # Recurse into multipart/* or other container types
        for part in parts:
            part_html, part_text = _extract_parts_recursive(part)
            if part_html and not html_body:
                html_body = part_html
            if part_text and not text_body:
                text_body = part_text

    return html_body, text_body


def extract_body_from_payload(payload: dict) -> tuple[str, str]:
    """Extract HTML and plain-text bodies from a Gmail message payload.

    Recursively walks the MIME parts tree decoding base64url-encoded data.

    Args:
        payload: The ``payload`` dict from a Gmail message resource
            (as returned by the ``users.messages.get`` API with
            ``format="full"``).

    Returns:
        A ``(html_body, text_body)`` tuple.  Either value may be an empty
        string when the corresponding MIME part is absent.
    """
    return _extract_parts_recursive(payload)


def get_header_value(headers: list[dict], name: str) -> str | None:
    """Return the value of a named header from a Gmail headers list.

    The lookup is case-insensitive so ``"Date"``, ``"date"``, and ``"DATE"``
    all match the same header.

    Args:
        headers: A list of ``{"name": ..., "value": ...}`` dicts as returned
            by the Gmail API.
        name: The header name to look up.

    Returns:
        The header value string, or ``None`` if the header is not present.
    """
    name_lower = name.lower()
    for header in headers:
        if header.get("name", "").lower() == name_lower:
            return header.get("value")
    return None


def parse_gmail_date(date_str: str) -> datetime:
    """Parse a Gmail ``Date`` header string into a timezone-aware :class:`datetime`.

    Uses :func:`email.utils.parsedate_to_datetime` which correctly handles
    RFC 2822-formatted date strings such as
    ``"Thu, 15 Mar 2026 10:30:00 +0700"``.

    Args:
        date_str: An RFC 2822 date string as found in Gmail message headers.

    Returns:
        A timezone-aware :class:`~datetime.datetime` object.

    Raises:
        ValueError: If *date_str* cannot be parsed.
    """
    try:
        return parsedate_to_datetime(date_str)
    except Exception as exc:
        raise ValueError(f"Cannot parse Gmail date string: {date_str!r}") from exc
