"""FastAPI endpoints for parser health monitoring."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.health import (
    AlertListResponse,
    ErrorBreakdownResponse,
    HealthDashboardResponse,
    MetricsTimeSeriesResponse,
    ParserHealthAlertSchema,
    ParserHealthMetricSchema,
    ParserHealthSummarySchema,
)
from app.services.health_monitor import HealthMonitorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parser-health", tags=["parser-health"])


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_model=HealthDashboardResponse)
async def get_dashboard(
    user_id: str | None = Query(None, description="Scope results to a specific user"),
    db: AsyncSession = Depends(get_db),
) -> HealthDashboardResponse:
    """Return an overall health dashboard across all parsers.

    Aggregates 24-hour metrics for every parser that has recorded activity and
    returns counts broken down by health status.

    Args:
        user_id: Optional user to scope the metrics.
        db: Database session.

    Returns:
        ``HealthDashboardResponse`` with per-parser summaries and status counts.
    """
    monitor = HealthMonitorService(db)
    summaries_raw = await monitor.get_all_parser_health(user_id=user_id)

    summaries = [ParserHealthSummarySchema(**s) for s in summaries_raw]
    healthy = sum(1 for s in summaries if s.status == "healthy")
    degraded = sum(1 for s in summaries if s.status == "degraded")
    failed = sum(1 for s in summaries if s.status in ("failed", "disabled"))

    return HealthDashboardResponse(
        parsers=summaries,
        total_parsers=len(summaries),
        healthy_count=healthy,
        degraded_count=degraded,
        failed_count=failed,
    )


# ---------------------------------------------------------------------------
# Per-parser endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/parsers/{name}/metrics",
    response_model=MetricsTimeSeriesResponse,
)
async def get_parser_metrics(
    name: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    user_id: str | None = Query(None, description="Scope to a specific user"),
    db: AsyncSession = Depends(get_db),
) -> MetricsTimeSeriesResponse:
    """Return time-series daily metrics for a specific parser.

    Args:
        name: Parser name.
        days: Number of calendar days to include (default 30, max 365).
        user_id: Optional user scope.
        db: Database session.

    Returns:
        ``MetricsTimeSeriesResponse`` with daily metric rows.
    """
    monitor = HealthMonitorService(db)
    metrics = await monitor.get_metrics(
        parser_name=name, user_id=user_id, days=days
    )
    metric_schemas = [ParserHealthMetricSchema.model_validate(m) for m in metrics]
    return MetricsTimeSeriesResponse(parser_name=name, metrics=metric_schemas)


@router.get(
    "/parsers/{name}/summary",
    response_model=ParserHealthSummarySchema,
)
async def get_parser_summary(
    name: str,
    user_id: str | None = Query(None, description="Scope to a specific user"),
    db: AsyncSession = Depends(get_db),
) -> ParserHealthSummarySchema:
    """Return a 24-hour health summary for a specific parser.

    Args:
        name: Parser name.
        user_id: Optional user scope.
        db: Database session.

    Returns:
        ``ParserHealthSummarySchema`` for the requested parser.

    Raises:
        HTTPException 404: If no metrics are found for the given parser name.
    """
    monitor = HealthMonitorService(db)
    all_summaries = await monitor.get_all_parser_health(user_id=user_id)
    for summary in all_summaries:
        if summary["parser_name"] == name:
            return ParserHealthSummarySchema(**summary)

    raise HTTPException(
        status_code=404, detail=f"No health metrics found for parser '{name}'"
    )


@router.get(
    "/parsers/{name}/errors",
    response_model=ErrorBreakdownResponse,
)
async def get_parser_errors(
    name: str,
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    user_id: str | None = Query(None, description="Scope to a specific user"),
    db: AsyncSession = Depends(get_db),
) -> ErrorBreakdownResponse:
    """Return the aggregated error-type breakdown for a specific parser.

    Args:
        name: Parser name.
        days: Number of calendar days to include (default 7, max 90).
        user_id: Optional user scope.
        db: Database session.

    Returns:
        ``ErrorBreakdownResponse`` mapping error types to cumulative counts.
    """
    monitor = HealthMonitorService(db)
    breakdown = await monitor.get_error_breakdown(
        parser_name=name, user_id=user_id, days=days
    )
    return ErrorBreakdownResponse(
        parser_name=name, errors=breakdown, period_days=days
    )


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    user_id: str | None = Query(None, description="Scope to a specific user"),
    acknowledged: bool = Query(False, description="Return acknowledged alerts"),
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    """Return a paginated list of parser health alerts.

    Args:
        user_id: Optional user scope.
        acknowledged: If ``False`` (default) return open alerts; ``True`` for
            already-acknowledged ones.
        page: 1-based page number.
        page_size: Number of items per page (max 100).
        db: Database session.

    Returns:
        ``AlertListResponse`` with items, total, page and page_size.
    """
    monitor = HealthMonitorService(db)
    alerts, total = await monitor.get_alerts(
        user_id=user_id,
        acknowledged=acknowledged,
        page=page,
        page_size=page_size,
    )
    items = [ParserHealthAlertSchema.from_alert(a) for a in alerts]
    return AlertListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=ParserHealthAlertSchema,
)
async def acknowledge_alert(
    alert_id: str,
    user_id: str | None = Query(None, description="Scope to a specific user"),
    db: AsyncSession = Depends(get_db),
) -> ParserHealthAlertSchema:
    """Mark a health alert as acknowledged.

    Args:
        alert_id: UUID of the alert to acknowledge.
        user_id: Optional user scope.
        db: Database session.

    Returns:
        Updated ``ParserHealthAlertSchema``.

    Raises:
        HTTPException 404: If the alert is not found.
    """
    monitor = HealthMonitorService(db)
    alert = await monitor.acknowledge_alert(alert_id=alert_id, user_id=user_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    return ParserHealthAlertSchema.from_alert(alert)


# ---------------------------------------------------------------------------
# Disabled parsers
# ---------------------------------------------------------------------------


@router.get("/disabled", response_model=list[dict])
async def list_disabled_parsers(
    user_id: str | None = Query(None, description="Scope to a specific user"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return the list of currently auto-disabled parsers.

    Args:
        user_id: Optional user scope.
        db: Database session.

    Returns:
        List of dicts with parser_name, reason, success_rate, disabled_at.
    """
    monitor = HealthMonitorService(db)
    logs = await monitor.get_disabled_parsers(user_id=user_id)
    return [
        {
            "id": log.id,
            "parser_name": log.parser_name,
            "user_id": log.user_id,
            "reason": log.reason,
            "success_rate": log.success_rate,
            "disabled_at": log.disabled_at,
            "re_enabled_at": log.re_enabled_at,
            "is_active": log.is_active,
        }
        for log in logs
    ]
