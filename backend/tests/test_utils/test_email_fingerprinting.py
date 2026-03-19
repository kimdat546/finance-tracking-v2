"""Tests for email fingerprinting and deduplication utilities."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import Email, EmailAccount
from app.utils.email_fingerprinting import (
    EmailDeduplicator,
    generate_email_fingerprint,
    generate_raw_fingerprint,
    is_within_dedup_window,
)
from tests.conftest import create_test_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SENDER = "noreply@cake.vn"
_AMOUNT = 500_000.0
_DATE = datetime(2026, 3, 15, 10, 30, 0)
_MERCHANT = "Nguyen Van A"
_USER_ID = "00000000-0000-0000-0000-000000000001"
_EMAIL_ACCOUNT_ID = "00000000-0000-0000-0000-ee0000000001"

# Maps user_id -> email_account_id for deterministic FK references.
_USER_ACCOUNT_MAP: dict[str, str] = {
    _USER_ID: _EMAIL_ACCOUNT_ID,
}
_account_counter = 0


def _get_account_id(user_id: str) -> str:
    """Return a deterministic email_account_id for a given user_id."""
    global _account_counter
    if user_id not in _USER_ACCOUNT_MAP:
        _account_counter += 1
        _USER_ACCOUNT_MAP[user_id] = f"00000000-0000-0000-0000-ee00000000{_account_counter:02d}"
    return _USER_ACCOUNT_MAP[user_id]


def _make_email(
    user_id: str = _USER_ID,
    fingerprint: str | None = None,
    is_duplicate: bool = False,
    received_at: datetime | None = None,
) -> Email:
    """Build an Email ORM instance without persisting it."""
    return Email(
        id=str(uuid4()),
        user_id=user_id,
        email_account_id=_get_account_id(user_id),
        gmail_message_id=str(uuid4()),
        sender=_SENDER,
        subject="Cake transaction",
        received_at=received_at or _DATE,
        fingerprint=fingerprint,
        is_duplicate=is_duplicate,
    )


async def _ensure_user_and_account(session: AsyncSession, user_id: str) -> None:
    """Create User and EmailAccount rows required by Email FK constraints."""
    await create_test_user(session, user_id=user_id)
    account_id = _get_account_id(user_id)
    account = EmailAccount(
        id=account_id,
        user_id=user_id,
        provider="gmail",
        email_address=f"{user_id}@test.example.com",
    )
    session.add(account)
    await session.flush()


# ---------------------------------------------------------------------------
# Unit tests – pure functions
# ---------------------------------------------------------------------------


class TestGenerateEmailFingerprint:
    """Tests for :func:`generate_email_fingerprint`."""

    def test_fingerprint_is_deterministic(self) -> None:
        """Same inputs must always produce the same hash."""
        fp1 = generate_email_fingerprint(_SENDER, _AMOUNT, _DATE, _MERCHANT, _USER_ID)
        fp2 = generate_email_fingerprint(_SENDER, _AMOUNT, _DATE, _MERCHANT, _USER_ID)
        assert fp1 == fp2

    def test_fingerprint_different_amounts(self) -> None:
        """Different amounts must produce different hashes."""
        fp1 = generate_email_fingerprint(_SENDER, 100.0, _DATE, _MERCHANT, _USER_ID)
        fp2 = generate_email_fingerprint(_SENDER, 200.0, _DATE, _MERCHANT, _USER_ID)
        assert fp1 != fp2

    def test_fingerprint_different_senders(self) -> None:
        """Different senders must produce different hashes."""
        fp1 = generate_email_fingerprint("sender-a@bank.com", _AMOUNT, _DATE, _MERCHANT, _USER_ID)
        fp2 = generate_email_fingerprint("sender-b@bank.com", _AMOUNT, _DATE, _MERCHANT, _USER_ID)
        assert fp1 != fp2

    def test_fingerprint_date_normalization(self) -> None:
        """Two datetimes on the same calendar day must yield the same hash."""
        dt_morning = datetime(2026, 3, 15, 6, 0, 0)
        dt_evening = datetime(2026, 3, 15, 23, 59, 59)
        fp1 = generate_email_fingerprint(_SENDER, _AMOUNT, dt_morning, _MERCHANT, _USER_ID)
        fp2 = generate_email_fingerprint(_SENDER, _AMOUNT, dt_evening, _MERCHANT, _USER_ID)
        assert fp1 == fp2

    def test_fingerprint_different_days(self) -> None:
        """Two datetimes on different calendar days must yield different hashes."""
        dt_day1 = datetime(2026, 3, 15, 10, 0, 0)
        dt_day2 = datetime(2026, 3, 16, 10, 0, 0)
        fp1 = generate_email_fingerprint(_SENDER, _AMOUNT, dt_day1, _MERCHANT, _USER_ID)
        fp2 = generate_email_fingerprint(_SENDER, _AMOUNT, dt_day2, _MERCHANT, _USER_ID)
        assert fp1 != fp2

    def test_fingerprint_merchant_normalization(self) -> None:
        """Merchant comparison is case-insensitive after normalisation."""
        fp_lower = generate_email_fingerprint(
            _SENDER, _AMOUNT, _DATE, "nguyen van a", _USER_ID
        )
        fp_upper = generate_email_fingerprint(
            _SENDER, _AMOUNT, _DATE, "NGUYEN VAN A", _USER_ID
        )
        assert fp_lower == fp_upper

    def test_fingerprint_merchant_whitespace_normalization(self) -> None:
        """Extra whitespace in merchant name is collapsed before hashing."""
        fp1 = generate_email_fingerprint(_SENDER, _AMOUNT, _DATE, "Nguyen  Van A", _USER_ID)
        fp2 = generate_email_fingerprint(_SENDER, _AMOUNT, _DATE, "Nguyen Van A", _USER_ID)
        assert fp1 == fp2

    def test_fingerprint_hex_length(self) -> None:
        """SHA-256 digest must be exactly 64 hexadecimal characters."""
        fp = generate_email_fingerprint(_SENDER, _AMOUNT, _DATE, _MERCHANT, _USER_ID)
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_none_merchant(self) -> None:
        """None merchant is treated as empty string and hashed consistently."""
        fp1 = generate_email_fingerprint(_SENDER, _AMOUNT, _DATE, None, _USER_ID)
        fp2 = generate_email_fingerprint(_SENDER, _AMOUNT, _DATE, None, _USER_ID)
        assert fp1 == fp2

    def test_fingerprint_accepts_iso_date_string(self) -> None:
        """ISO-format date string normalises to date-only, matching datetime input."""
        fp_dt = generate_email_fingerprint(_SENDER, _AMOUNT, _DATE, _MERCHANT, _USER_ID)
        fp_str = generate_email_fingerprint(
            _SENDER, _AMOUNT, "2026-03-15T10:30:00", _MERCHANT, _USER_ID
        )
        assert fp_dt == fp_str


class TestGenerateRawFingerprint:
    """Tests for :func:`generate_raw_fingerprint`."""

    def test_raw_fingerprint_generation(self) -> None:
        """Raw fingerprint must be a valid 64-char hex digest."""
        fp = generate_raw_fingerprint("Hello raw content", _SENDER, _USER_ID)
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)

    def test_raw_fingerprint_is_deterministic(self) -> None:
        """Same raw content must always produce the same hash."""
        content = "Raw email body text 12345"
        fp1 = generate_raw_fingerprint(content, _SENDER, _USER_ID)
        fp2 = generate_raw_fingerprint(content, _SENDER, _USER_ID)
        assert fp1 == fp2

    def test_raw_fingerprint_truncates_at_500_chars(self) -> None:
        """Content beyond 500 characters is ignored in the hash."""
        short = "A" * 500
        long_with_same_prefix = "A" * 500 + "EXTRA"
        fp_short = generate_raw_fingerprint(short, _SENDER, _USER_ID)
        fp_long = generate_raw_fingerprint(long_with_same_prefix, _SENDER, _USER_ID)
        assert fp_short == fp_long

    def test_raw_fingerprint_differs_by_sender(self) -> None:
        """Different senders must yield different raw fingerprints."""
        content = "Same content"
        fp1 = generate_raw_fingerprint(content, "sender-a@x.com", _USER_ID)
        fp2 = generate_raw_fingerprint(content, "sender-b@x.com", _USER_ID)
        assert fp1 != fp2


class TestIsWithinDedupWindow:
    """Tests for :func:`is_within_dedup_window`."""

    def test_within_window_true(self) -> None:
        """1 hour apart is within the 24-hour window."""
        t1 = datetime(2026, 3, 15, 10, 0, 0)
        t2 = t1 + timedelta(hours=1)
        assert is_within_dedup_window(t1, t2) is True

    def test_outside_window_false(self) -> None:
        """25 hours apart is outside the 24-hour window."""
        t1 = datetime(2026, 3, 15, 10, 0, 0)
        t2 = t1 + timedelta(hours=25)
        assert is_within_dedup_window(t1, t2) is False

    def test_exactly_on_boundary_false(self) -> None:
        """Exactly at 24 hours is NOT within the window (strict less-than)."""
        t1 = datetime(2026, 3, 15, 10, 0, 0)
        t2 = t1 + timedelta(hours=24)
        assert is_within_dedup_window(t1, t2) is False

    def test_custom_window(self) -> None:
        """Custom window_hours parameter is respected."""
        t1 = datetime(2026, 3, 15, 10, 0, 0)
        t2 = t1 + timedelta(hours=3)
        assert is_within_dedup_window(t1, t2, window_hours=6) is True
        assert is_within_dedup_window(t1, t2, window_hours=2) is False

    def test_reversed_order_is_symmetric(self) -> None:
        """Order of arguments does not matter (absolute difference)."""
        t1 = datetime(2026, 3, 15, 10, 0, 0)
        t2 = t1 + timedelta(hours=5)
        assert is_within_dedup_window(t1, t2) == is_within_dedup_window(t2, t1)


# ---------------------------------------------------------------------------
# Integration tests – EmailDeduplicator (require test_db fixture)
# ---------------------------------------------------------------------------


class TestEmailDeduplicator:
    """Integration tests for :class:`EmailDeduplicator`."""

    @pytest.mark.asyncio
    async def test_check_duplicate_no_existing(self, test_db: AsyncSession) -> None:
        """check_duplicate returns False when no matching email exists."""
        deduplicator = EmailDeduplicator(test_db)
        result = await deduplicator.check_duplicate(
            fingerprint="abc123fingerprint",
            user_id=_USER_ID,
            received_at=_DATE,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_check_duplicate_found_within_window(self, test_db: AsyncSession) -> None:
        """check_duplicate returns True when a matching email is within 24 hours."""
        await _ensure_user_and_account(test_db, _USER_ID)
        fp = generate_email_fingerprint(_SENDER, _AMOUNT, _DATE, _MERCHANT, _USER_ID)

        email = _make_email(user_id=_USER_ID, fingerprint=fp, received_at=_DATE)
        test_db.add(email)
        await test_db.commit()

        deduplicator = EmailDeduplicator(test_db)
        # Candidate arrives 2 hours later — within window
        candidate_time = _DATE + timedelta(hours=2)
        result = await deduplicator.check_duplicate(
            fingerprint=fp,
            user_id=_USER_ID,
            received_at=candidate_time,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_check_duplicate_outside_window(self, test_db: AsyncSession) -> None:
        """check_duplicate returns False when the existing email is outside the window."""
        await _ensure_user_and_account(test_db, _USER_ID)
        fp = generate_email_fingerprint(_SENDER, _AMOUNT, _DATE, _MERCHANT, _USER_ID)

        email = _make_email(user_id=_USER_ID, fingerprint=fp, received_at=_DATE)
        test_db.add(email)
        await test_db.commit()

        deduplicator = EmailDeduplicator(test_db)
        # Candidate arrives 30 hours later — outside 24-hour window
        candidate_time = _DATE + timedelta(hours=30)
        result = await deduplicator.check_duplicate(
            fingerprint=fp,
            user_id=_USER_ID,
            received_at=candidate_time,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_deduplicator_mark_as_duplicate(self, test_db: AsyncSession) -> None:
        """mark_as_duplicate sets is_duplicate=True on the target email."""
        await _ensure_user_and_account(test_db, _USER_ID)
        email = _make_email(user_id=_USER_ID, is_duplicate=False)
        test_db.add(email)
        await test_db.commit()
        await test_db.refresh(email)

        deduplicator = EmailDeduplicator(test_db)
        await deduplicator.mark_as_duplicate(email.id)

        # Re-fetch and assert
        await test_db.refresh(email)
        assert email.is_duplicate is True

    @pytest.mark.asyncio
    async def test_get_duplicate_count(self, test_db: AsyncSession) -> None:
        """get_duplicate_count returns the correct count of duplicate emails."""
        uid = "00000000-0000-0000-0000-000000000010"
        await _ensure_user_and_account(test_db, uid)
        for i in range(3):
            test_db.add(_make_email(user_id=uid, is_duplicate=True))
        # One non-duplicate — should not be counted
        test_db.add(_make_email(user_id=uid, is_duplicate=False))
        await test_db.commit()

        deduplicator = EmailDeduplicator(test_db)
        count = await deduplicator.get_duplicate_count(uid)
        assert count == 3

    @pytest.mark.asyncio
    async def test_cleanup_old_duplicates(self, test_db: AsyncSession) -> None:
        """cleanup_old_duplicates deletes duplicates older than the cutoff and returns count."""
        uid = "00000000-0000-0000-0000-000000000011"
        await _ensure_user_and_account(test_db, uid)
        old_time = datetime.now(timezone.utc) - timedelta(days=40)

        # Two old duplicates — should be deleted
        for _ in range(2):
            e = _make_email(user_id=uid, is_duplicate=True, received_at=old_time)
            # Override created_at to simulate old records
            e.created_at = old_time  # type: ignore[assignment]
            test_db.add(e)

        # One recent duplicate — should NOT be deleted
        recent = _make_email(user_id=uid, is_duplicate=True)
        test_db.add(recent)

        await test_db.commit()

        deduplicator = EmailDeduplicator(test_db)
        deleted = await deduplicator.cleanup_old_duplicates(uid, older_than_days=30)

        assert deleted == 2

        # Verify the recent one is still there
        remaining_count = await deduplicator.get_duplicate_count(uid)
        assert remaining_count == 1

    @pytest.mark.asyncio
    async def test_mark_as_duplicate_nonexistent_email(self, test_db: AsyncSession) -> None:
        """mark_as_duplicate handles a non-existent email ID gracefully (no error)."""
        deduplicator = EmailDeduplicator(test_db)
        # Should not raise
        await deduplicator.mark_as_duplicate("00000000-0000-0000-0000-ffffffffffff")
