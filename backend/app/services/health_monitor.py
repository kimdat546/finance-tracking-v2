"""Parser health monitoring service.

Tracks per-parser success/failure metrics and issues alerts when parsers
degrade below configurable thresholds.
"""

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health import ParserDisabledLog, ParserHealthMetric
from app.models.system import ParserHealthAlert, ParserHealthStatus

logger = logging.getLogger(__name__)


class HealthMonitorService:
    """Monitors parser health metrics and triggers alerts.

    Responsibilities:
    - Record individual parse attempts as aggregated daily metrics.
    - Compute rolling success rates.
    - Create ``ParserHealthAlert`` rows when parsers fall below thresholds.
    - Log auto-disable events and update the in-memory ``ParserRegistry``.
    """

    LOW_SUCCESS_RATE_THRESHOLD: float = 0.90  # Alert if below this
    AUTO_DISABLE_THRESHOLD: float = 0.50  # Auto-disable if below this
    ALERT_WINDOW_HOURS: int = 24

    # Placeholder UUID used for parser_id on ParserHealthAlert rows when
    # the parser is not present in the parser_registry table.
    _PLACEHOLDER_PARSER_ID: str = "00000000-0000-0000-0000-000000000000"

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the service with a database session.

        Args:
            session: Async SQLAlchemy session.
        """
        self._session = session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _today(self) -> str:
        """Return today's date as a 'YYYY-MM-DD' string (UTC)."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _now_iso(self) -> str:
        """Return current UTC datetime as an ISO-8601 string."""
        return datetime.now(timezone.utc).isoformat()

    def _date_n_days_ago(self, days: int) -> str:
        """Return the date N days ago as a 'YYYY-MM-DD' string."""
        return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    async def _get_or_create_metric(
        self,
        parser_name: str,
        metric_date: str,
        user_id: str | None,
        transaction_type: str | None,
    ) -> ParserHealthMetric:
        """Fetch or create the daily metric row for the given key.

        Args:
            parser_name: Name of the parser.
            metric_date: Date string in 'YYYY-MM-DD' format.
            user_id: Optional user scope.
            transaction_type: Optional transaction type scope.

        Returns:
            The existing or newly created ``ParserHealthMetric`` row.
        """
        # Build filter conditions handling NULL comparisons
        conditions = [
            ParserHealthMetric.parser_name == parser_name,
            ParserHealthMetric.metric_date == metric_date,
        ]
        if user_id is None:
            conditions.append(ParserHealthMetric.user_id.is_(None))
        else:
            conditions.append(ParserHealthMetric.user_id == user_id)

        if transaction_type is None:
            conditions.append(ParserHealthMetric.transaction_type.is_(None))
        else:
            conditions.append(ParserHealthMetric.transaction_type == transaction_type)

        stmt = select(ParserHealthMetric).where(and_(*conditions))
        result = await self._session.execute(stmt)
        metric = result.scalar_one_or_none()

        if metric is None:
            metric = ParserHealthMetric(
                parser_name=parser_name,
                user_id=user_id,
                metric_date=metric_date,
                transaction_type=transaction_type,
                success_count=0,
                failure_count=0,
                total_time_ms=0,
                error_breakdown=None,
            )
            self._session.add(metric)
            await self._session.flush()

        return metric

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def record_parse_attempt(
        self,
        parser_name: str,
        success: bool,
        parse_time_ms: float,
        transaction_type: str | None = None,
        error_type: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Record a single parse attempt in the daily metric row.

        Upserts into ``ParserHealthMetric`` for today.  After updating the
        counts, checks whether the new success rate crosses any threshold and
        creates an alert or disables the parser if needed.

        Args:
            parser_name: Identifier of the parser that ran.
            success: Whether the parse was successful.
            parse_time_ms: Elapsed time in milliseconds.
            transaction_type: Optional transaction type hint.
            error_type: Category of the error if ``success`` is False.
            user_id: Optional user scope.
        """
        today = self._today()
        metric = await self._get_or_create_metric(
            parser_name=parser_name,
            metric_date=today,
            user_id=user_id,
            transaction_type=transaction_type,
        )

        # Update counters
        if success:
            metric.success_count += 1
        else:
            metric.failure_count += 1

        metric.total_time_ms += int(parse_time_ms)

        # Update error breakdown JSON
        if not success and error_type:
            breakdown: dict[str, int] = {}
            if metric.error_breakdown:
                try:
                    breakdown = json.loads(metric.error_breakdown)
                except (json.JSONDecodeError, ValueError):
                    breakdown = {}
            breakdown[error_type] = breakdown.get(error_type, 0) + 1
            metric.error_breakdown = json.dumps(breakdown)

        await self._session.flush()

        # Check thresholds and alert
        try:
            await self.check_and_alert(parser_name=parser_name, user_id=user_id)
        except Exception:
            logger.exception(
                "Failed to check/alert for parser %s after recording attempt",
                parser_name,
            )

    async def get_metrics(
        self,
        parser_name: str,
        user_id: str | None = None,
        days: int = 30,
    ) -> list[ParserHealthMetric]:
        """Return daily metrics for a parser over the last N days.

        Args:
            parser_name: Parser to query.
            user_id: Optional user scope.
            days: Number of calendar days to look back.

        Returns:
            List of ``ParserHealthMetric`` rows ordered by date ascending.
        """
        cutoff = self._date_n_days_ago(days)
        conditions = [
            ParserHealthMetric.parser_name == parser_name,
            ParserHealthMetric.metric_date >= cutoff,
        ]
        if user_id is None:
            conditions.append(ParserHealthMetric.user_id.is_(None))
        else:
            conditions.append(ParserHealthMetric.user_id == user_id)

        stmt = (
            select(ParserHealthMetric)
            .where(and_(*conditions))
            .order_by(ParserHealthMetric.metric_date.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_success_rate(
        self,
        parser_name: str,
        user_id: str | None = None,
        hours: int = 24,
    ) -> float:
        """Calculate the rolling success rate for a parser over N hours.

        Because metrics are stored at day granularity we approximate by
        summing the metric rows that fall within the hour window.

        Args:
            parser_name: Parser to query.
            user_id: Optional user scope.
            hours: Rolling window in hours.

        Returns:
            Success rate in ``[0.0, 1.0]``; ``0.0`` if no data.
        """
        days = max(1, (hours + 23) // 24)  # ceil division
        metrics = await self.get_metrics(
            parser_name=parser_name, user_id=user_id, days=days
        )
        total_success = sum(m.success_count for m in metrics)
        total_failure = sum(m.failure_count for m in metrics)
        total = total_success + total_failure
        return total_success / total if total > 0 else 0.0

    async def get_all_parser_health(
        self,
        user_id: str | None = None,
    ) -> list[dict]:
        """Return a health summary for every parser that has recorded metrics.

        Args:
            user_id: Optional user scope.

        Returns:
            List of dicts with keys: parser_name, success_rate_24h,
            total_attempts_24h, avg_time_ms, status, last_attempt_at.
        """
        cutoff = self._date_n_days_ago(1)
        conditions = [ParserHealthMetric.metric_date >= cutoff]
        if user_id is None:
            conditions.append(ParserHealthMetric.user_id.is_(None))
        else:
            conditions.append(ParserHealthMetric.user_id == user_id)

        stmt = select(ParserHealthMetric).where(and_(*conditions))
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        # Aggregate by parser_name
        aggregated: dict[str, dict] = {}
        for row in rows:
            name = row.parser_name
            if name not in aggregated:
                aggregated[name] = {
                    "success": 0,
                    "failure": 0,
                    "total_time_ms": 0,
                    "last_date": None,
                }
            agg = aggregated[name]
            agg["success"] += row.success_count
            agg["failure"] += row.failure_count
            agg["total_time_ms"] += row.total_time_ms
            if agg["last_date"] is None or row.metric_date > agg["last_date"]:
                agg["last_date"] = row.metric_date

        # Check disabled parsers
        disabled_names: set[str] = set()
        disabled_logs = await self.get_disabled_parsers(user_id=user_id)
        for log in disabled_logs:
            disabled_names.add(log.parser_name)

        summaries: list[dict] = []
        for name, agg in aggregated.items():
            total = agg["success"] + agg["failure"]
            rate = agg["success"] / total if total > 0 else 0.0
            avg_time = agg["total_time_ms"] / total if total > 0 else 0.0

            if name in disabled_names:
                status = "disabled"
            elif rate >= self.LOW_SUCCESS_RATE_THRESHOLD:
                status = "healthy"
            elif rate >= self.AUTO_DISABLE_THRESHOLD:
                status = "degraded"
            else:
                status = "failed"

            summaries.append(
                {
                    "parser_name": name,
                    "success_rate_24h": rate,
                    "total_attempts_24h": total,
                    "avg_time_ms": avg_time,
                    "status": status,
                    "last_attempt_at": agg["last_date"],
                }
            )

        return summaries

    async def check_and_alert(
        self,
        parser_name: str,
        user_id: str | None = None,
    ) -> ParserHealthAlert | None:
        """Check parser health and create an alert if thresholds are crossed.

        - If success_rate < 0.90: creates a ``degraded`` alert.
        - If success_rate < 0.50: creates a ``failed`` alert and auto-disables.

        Args:
            parser_name: Parser to check.
            user_id: Optional user scope.

        Returns:
            The created ``ParserHealthAlert`` row, or ``None`` if healthy.
        """
        rate = await self.get_success_rate(
            parser_name=parser_name,
            user_id=user_id,
            hours=self.ALERT_WINDOW_HOURS,
        )

        if rate >= self.LOW_SUCCESS_RATE_THRESHOLD:
            return None

        # Determine alert status
        if rate < self.AUTO_DISABLE_THRESHOLD:
            alert_status = ParserHealthStatus.FAILED
        else:
            alert_status = ParserHealthStatus.DEGRADED

        # Gather 24h counts for the alert
        metrics = await self.get_metrics(
            parser_name=parser_name, user_id=user_id, days=1
        )
        success_24h = sum(m.success_count for m in metrics)
        failure_24h = sum(m.failure_count for m in metrics)
        total_time = sum(m.total_time_ms for m in metrics)
        total_24h = success_24h + failure_24h
        avg_time = total_time / total_24h if total_24h > 0 else 0.0

        # Build message — embed parser_name because parser_id is a FK we may
        # not have a real value for in tests / when the parser isn't in the DB.
        message = (
            f"Parser '{parser_name}' success rate dropped to "
            f"{rate:.1%} over the last {self.ALERT_WINDOW_HOURS}h "
            f"(threshold: {self.LOW_SUCCESS_RATE_THRESHOLD:.0%})"
        )

        # Resolve user_id; ParserHealthAlert.user_id is non-nullable.
        # Use a placeholder when monitoring globally.
        resolved_user_id = user_id or self._PLACEHOLDER_PARSER_ID

        alert = ParserHealthAlert(
            user_id=resolved_user_id,
            parser_id=self._PLACEHOLDER_PARSER_ID,
            status=alert_status,
            message=message,
            error_count_24h=failure_24h,
            success_count_24h=success_24h,
            avg_parse_time_ms=avg_time,
            is_acknowledged=False,
        )
        self._session.add(alert)
        await self._session.flush()

        if rate < self.AUTO_DISABLE_THRESHOLD:
            await self.auto_disable_parser(
                parser_name=parser_name,
                user_id=user_id,
                success_rate=rate,
            )

        return alert

    async def auto_disable_parser(
        self,
        parser_name: str,
        user_id: str | None,
        success_rate: float,
    ) -> None:
        """Log the auto-disabling event and mark the in-memory parser disabled.

        Args:
            parser_name: Parser to disable.
            user_id: Optional user scope.
            success_rate: The rate that triggered the disabling.
        """
        reason = (
            f"Auto-disabled: success rate {success_rate:.1%} fell below "
            f"the {self.AUTO_DISABLE_THRESHOLD:.0%} threshold."
        )
        log = ParserDisabledLog(
            parser_name=parser_name,
            user_id=user_id,
            reason=reason,
            success_rate=success_rate,
            disabled_at=self._now_iso(),
            re_enabled_at=None,
            is_active=True,
        )
        self._session.add(log)
        await self._session.flush()

        logger.warning(
            "Auto-disabled parser '%s' (user=%s, success_rate=%.2f)",
            parser_name,
            user_id,
            success_rate,
        )

        # Best-effort: disable in the in-memory registry if available
        try:
            from app.parsers.registry import registry

            parser_instance = registry.get_parser(parser_name)
            if parser_instance is not None:
                # The in-memory parser classes don't have an `is_active` flag,
                # but we can remove the instance so it won't be matched.
                registry._parser_instances.pop(parser_name, None)
                registry._parsers.pop(parser_name, None)
                logger.info(
                    "Removed parser '%s' from in-memory registry", parser_name
                )
        except Exception:
            logger.exception(
                "Could not update in-memory registry for parser '%s'", parser_name
            )

    async def get_alerts(
        self,
        user_id: str | None = None,
        acknowledged: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ParserHealthAlert], int]:
        """Return paginated health alerts.

        Args:
            user_id: Optional user scope.  ``None`` returns all alerts.
            acknowledged: If ``False`` (default) return only unacknowledged;
                if ``True`` return only acknowledged alerts.
            page: 1-based page number.
            page_size: Number of items per page.

        Returns:
            Tuple of (page of alerts, total count).
        """
        conditions = [ParserHealthAlert.is_acknowledged == acknowledged]
        if user_id is not None:
            conditions.append(ParserHealthAlert.user_id == user_id)

        # Count query
        count_stmt = select(ParserHealthAlert).where(and_(*conditions))
        count_result = await self._session.execute(count_stmt)
        all_rows = list(count_result.scalars().all())
        total = len(all_rows)

        # Paginated query
        offset = (page - 1) * page_size
        stmt = (
            select(ParserHealthAlert)
            .where(and_(*conditions))
            .order_by(ParserHealthAlert.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        alerts = list(result.scalars().all())

        return alerts, total

    async def acknowledge_alert(
        self,
        alert_id: str,
        user_id: str | None = None,
    ) -> ParserHealthAlert | None:
        """Mark a health alert as acknowledged.

        Args:
            alert_id: UUID of the alert to acknowledge.
            user_id: Optional user scope used to scope the lookup.

        Returns:
            Updated alert row, or ``None`` if not found.
        """
        conditions = [ParserHealthAlert.id == alert_id]
        if user_id is not None:
            conditions.append(ParserHealthAlert.user_id == user_id)

        stmt = select(ParserHealthAlert).where(and_(*conditions))
        result = await self._session.execute(stmt)
        alert = result.scalar_one_or_none()

        if alert is None:
            return None

        alert.is_acknowledged = True
        alert.acknowledged_at = self._now_iso()
        await self._session.flush()
        return alert

    async def get_error_breakdown(
        self,
        parser_name: str,
        user_id: str | None = None,
        days: int = 7,
    ) -> dict[str, int]:
        """Aggregate error breakdown JSON across the requested number of days.

        Args:
            parser_name: Parser to query.
            user_id: Optional user scope.
            days: Number of days to look back.

        Returns:
            Dict mapping error type to cumulative count.
        """
        metrics = await self.get_metrics(
            parser_name=parser_name, user_id=user_id, days=days
        )
        combined: dict[str, int] = {}
        for metric in metrics:
            if not metric.error_breakdown:
                continue
            try:
                breakdown: dict[str, int] = json.loads(metric.error_breakdown)
            except (json.JSONDecodeError, ValueError):
                continue
            for error_type, count in breakdown.items():
                combined[error_type] = combined.get(error_type, 0) + count
        return combined

    async def get_disabled_parsers(
        self, user_id: str | None = None
    ) -> list[ParserDisabledLog]:
        """Return the list of currently auto-disabled parsers.

        Args:
            user_id: Optional user scope.

        Returns:
            List of active ``ParserDisabledLog`` rows.
        """
        conditions = [ParserDisabledLog.is_active.is_(True)]
        if user_id is None:
            conditions.append(ParserDisabledLog.user_id.is_(None))
        else:
            conditions.append(
                or_(
                    ParserDisabledLog.user_id == user_id,
                    ParserDisabledLog.user_id.is_(None),
                )
            )

        stmt = (
            select(ParserDisabledLog)
            .where(and_(*conditions))
            .order_by(ParserDisabledLog.disabled_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Context manager helper
# ---------------------------------------------------------------------------


@asynccontextmanager
async def track_parse_time(
    monitor: HealthMonitorService,
    parser_name: str,
    transaction_type: str | None = None,
    user_id: str | None = None,
) -> AsyncGenerator[None, None]:
    """Context manager that records parse time and outcome as health metrics.

    Records a successful attempt on normal exit and a failed attempt
    (``error_type="parsing_error"``) on exception.  Monitoring errors are
    silently swallowed so they never interrupt the main parsing flow.

    Usage::

        async with track_parse_time(monitor, "cake_vpbank"):
            result = await parser.parse(email_body)

    Args:
        monitor: ``HealthMonitorService`` instance to record into.
        parser_name: Name of the parser being timed.
        transaction_type: Optional transaction type hint.
        user_id: Optional user scope.
    """
    start = time.time()
    success = True
    error_type: str | None = None
    try:
        yield
    except Exception:
        success = False
        error_type = "parsing_error"
        raise
    finally:
        elapsed_ms = (time.time() - start) * 1000
        try:
            await monitor.record_parse_attempt(
                parser_name=parser_name,
                success=success,
                parse_time_ms=elapsed_ms,
                transaction_type=transaction_type,
                error_type=error_type,
                user_id=user_id,
            )
        except Exception:
            logger.exception(
                "Failed to record parse attempt for parser '%s'; "
                "monitoring error suppressed.",
                parser_name,
            )
