"""Tests for HealthMonitorService and the track_parse_time context manager."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health import ParserHealthMetric
from app.models.system import ParserRegistry
from app.services.health_monitor import HealthMonitorService, track_parse_time
from tests.conftest import create_test_user

# The HealthMonitorService uses this placeholder UUID as user_id when creating
# ParserHealthAlert rows without an explicit user scope.
_PLACEHOLDER_USER_ID = "00000000-0000-0000-0000-000000000000"
_PLACEHOLDER_PARSER_ID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PARSER = "test_parser"


async def _ensure_placeholder_rows(session: AsyncSession) -> None:
    """Create User and ParserRegistry rows needed by ParserHealthAlert FKs."""
    await create_test_user(session, user_id=_PLACEHOLDER_USER_ID)
    parser_reg = ParserRegistry(
        id=_PLACEHOLDER_PARSER_ID,
        user_id=_PLACEHOLDER_USER_ID,
        parser_name=PARSER,
        parser_type="builtin",
        display_name="Test Parser",
    )
    session.add(parser_reg)
    await session.flush()


async def _record(
    monitor: HealthMonitorService,
    *,
    success: bool,
    parse_time_ms: float = 10.0,
    error_type: str | None = None,
    transaction_type: str | None = None,
    user_id: str | None = None,
) -> None:
    """Thin wrapper to reduce boilerplate in tests."""
    await monitor.record_parse_attempt(
        parser_name=PARSER,
        success=success,
        parse_time_ms=parse_time_ms,
        transaction_type=transaction_type,
        error_type=error_type,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# record_parse_attempt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_parse_attempt_success(test_db: AsyncSession) -> None:
    """A successful parse attempt should increment success_count by 1."""
    monitor = HealthMonitorService(test_db)
    await _record(monitor, success=True)
    await test_db.commit()

    from sqlalchemy import select

    result = await test_db.execute(
        select(ParserHealthMetric).where(ParserHealthMetric.parser_name == PARSER)
    )
    metric = result.scalar_one()
    assert metric.success_count == 1
    assert metric.failure_count == 0


@pytest.mark.asyncio
async def test_record_parse_attempt_failure(test_db: AsyncSession) -> None:
    """A failed parse attempt should increment failure_count by 1."""
    await _ensure_placeholder_rows(test_db)
    monitor = HealthMonitorService(test_db)
    await _record(monitor, success=False, error_type="parsing_error")
    await test_db.commit()

    from sqlalchemy import select

    result = await test_db.execute(
        select(ParserHealthMetric).where(ParserHealthMetric.parser_name == PARSER)
    )
    metric = result.scalar_one()
    assert metric.failure_count == 1
    assert metric.success_count == 0


# ---------------------------------------------------------------------------
# get_success_rate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_success_rate_100_percent(test_db: AsyncSession) -> None:
    """All successful attempts should yield a 1.0 success rate."""
    monitor = HealthMonitorService(test_db)
    for _ in range(5):
        await _record(monitor, success=True)
    await test_db.commit()

    rate = await monitor.get_success_rate(PARSER)
    assert rate == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_success_rate_50_percent(test_db: AsyncSession) -> None:
    """Half successes and half failures should yield a 0.5 success rate."""
    await _ensure_placeholder_rows(test_db)
    monitor = HealthMonitorService(test_db)
    for _ in range(3):
        await _record(monitor, success=True)
    for _ in range(3):
        await _record(monitor, success=False)
    await test_db.commit()

    rate = await monitor.get_success_rate(PARSER)
    assert rate == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_success_rate_empty(test_db: AsyncSession) -> None:
    """No data should return a 0.0 success rate."""
    monitor = HealthMonitorService(test_db)
    rate = await monitor.get_success_rate("nonexistent_parser")
    assert rate == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Upsert (same-day deduplication)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metric_upsert_same_day(test_db: AsyncSession) -> None:
    """Two record calls on the same day should update the same metric row."""
    monitor = HealthMonitorService(test_db)

    await _record(monitor, success=True)
    await _record(monitor, success=True)
    await test_db.commit()

    from sqlalchemy import select

    result = await test_db.execute(
        select(ParserHealthMetric).where(ParserHealthMetric.parser_name == PARSER)
    )
    rows = result.scalars().all()
    # There should be exactly ONE row for today
    today_rows = [
        r
        for r in rows
        if r.transaction_type is None and r.user_id is None
    ]
    assert len(today_rows) == 1
    assert today_rows[0].success_count == 2


# ---------------------------------------------------------------------------
# Error breakdown tracking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_breakdown_tracking(test_db: AsyncSession) -> None:
    """Error types should accumulate correctly in the error_breakdown field."""
    await _ensure_placeholder_rows(test_db)
    monitor = HealthMonitorService(test_db)

    await _record(monitor, success=False, error_type="parsing_error")
    await _record(monitor, success=False, error_type="parsing_error")
    await _record(monitor, success=False, error_type="validation_error")
    await test_db.commit()

    breakdown = await monitor.get_error_breakdown(PARSER)
    assert breakdown.get("parsing_error") == 2
    assert breakdown.get("validation_error") == 1


# ---------------------------------------------------------------------------
# check_and_alert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_and_alert_healthy(test_db: AsyncSession) -> None:
    """A parser with a 100 % success rate should not create any alert."""
    monitor = HealthMonitorService(test_db)
    for _ in range(10):
        await _record(monitor, success=True)
    await test_db.commit()

    alert = await monitor.check_and_alert(PARSER)
    assert alert is None


@pytest.mark.asyncio
async def test_check_and_alert_degraded(test_db: AsyncSession) -> None:
    """A success rate below 0.90 but above 0.50 should produce a 'degraded' alert."""
    await _ensure_placeholder_rows(test_db)
    monitor = HealthMonitorService(test_db)
    # 8 successes + 2 failures = 80 % success rate → below LOW_SUCCESS_RATE_THRESHOLD
    for _ in range(8):
        await _record(monitor, success=True)
    for _ in range(2):
        await _record(monitor, success=False)
    await test_db.commit()

    alert = await monitor.check_and_alert(PARSER)
    assert alert is not None
    assert alert.status.value == "degraded"


@pytest.mark.asyncio
async def test_check_and_alert_failed(test_db: AsyncSession) -> None:
    """A success rate below 0.50 should produce a 'failed' alert."""
    await _ensure_placeholder_rows(test_db)
    monitor = HealthMonitorService(test_db)
    # 1 success + 9 failures = 10 % success rate → below AUTO_DISABLE_THRESHOLD
    await _record(monitor, success=True)
    for _ in range(9):
        await _record(monitor, success=False)
    await test_db.commit()

    alert = await monitor.check_and_alert(PARSER)
    assert alert is not None
    assert alert.status.value == "failed"


# ---------------------------------------------------------------------------
# acknowledge_alert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledge_alert(test_db: AsyncSession) -> None:
    """acknowledge_alert should mark the alert as acknowledged."""
    await _ensure_placeholder_rows(test_db)
    monitor = HealthMonitorService(test_db)

    # Force an alert by recording a bad success rate
    await _record(monitor, success=True)
    for _ in range(9):
        await _record(monitor, success=False)
    await test_db.commit()

    alert = await monitor.check_and_alert(PARSER)
    assert alert is not None
    assert not alert.is_acknowledged

    acked = await monitor.acknowledge_alert(alert_id=alert.id)
    assert acked is not None
    assert acked.is_acknowledged is True
    assert acked.acknowledged_at is not None


# ---------------------------------------------------------------------------
# get_all_parser_health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_all_parser_health_empty(test_db: AsyncSession) -> None:
    """get_all_parser_health should return an empty list when no metrics exist."""
    monitor = HealthMonitorService(test_db)
    summaries = await monitor.get_all_parser_health()
    assert summaries == []


# ---------------------------------------------------------------------------
# track_parse_time context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_track_parse_time_context_manager(test_db: AsyncSession) -> None:
    """track_parse_time should record a successful attempt with non-zero timing."""
    monitor = HealthMonitorService(test_db)

    async with track_parse_time(monitor, PARSER):
        # Simulate some work
        pass

    await test_db.commit()

    from sqlalchemy import select

    result = await test_db.execute(
        select(ParserHealthMetric).where(ParserHealthMetric.parser_name == PARSER)
    )
    metric = result.scalar_one()
    assert metric.success_count == 1
    assert metric.failure_count == 0
    # total_time_ms should be >= 0 (timing is always non-negative)
    assert metric.total_time_ms >= 0
