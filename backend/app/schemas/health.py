"""Pydantic v2 schemas for parser health monitoring endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field


class ParserHealthMetricSchema(BaseModel):
    """Daily metric snapshot for a single parser.

    Attributes:
        parser_name: Name of the parser.
        metric_date: Date of the metric in 'YYYY-MM-DD' format.
        success_count: Number of successful parses on this day.
        failure_count: Number of failed parses on this day.
        total_time_ms: Cumulative parse time in milliseconds.
        transaction_type: Optional scoped transaction type.
    """

    model_config = ConfigDict(from_attributes=True)

    parser_name: str
    metric_date: str
    success_count: int
    failure_count: int
    total_time_ms: int
    transaction_type: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_attempts(self) -> int:
        """Total number of parse attempts (successes + failures)."""
        return self.success_count + self.failure_count

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success_rate(self) -> float:
        """Fraction of successful parse attempts; 0.0 if no attempts."""
        total = self.total_attempts
        return self.success_count / total if total > 0 else 0.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def avg_parse_time_ms(self) -> float:
        """Average parse time in milliseconds; 0.0 if no attempts."""
        total = self.total_attempts
        return self.total_time_ms / total if total > 0 else 0.0


class ParserHealthSummarySchema(BaseModel):
    """Aggregated 24-hour health summary for a single parser.

    Attributes:
        parser_name: Name of the parser.
        success_rate_24h: Rolling success rate over the last 24 hours.
        total_attempts_24h: Total parse attempts in the last 24 hours.
        avg_time_ms: Average parse time in milliseconds.
        status: Qualitative health status.
        last_attempt_at: ISO date of the most recent recorded attempt.
    """

    model_config = ConfigDict(from_attributes=True)

    parser_name: str
    success_rate_24h: float
    total_attempts_24h: int
    avg_time_ms: float
    status: Literal["healthy", "degraded", "failed", "disabled"]
    last_attempt_at: str | None = None


class ParserHealthAlertSchema(BaseModel):
    """Schema for a single parser health alert.

    Attributes:
        id: UUID of the alert.
        parser_name: Derived from the alert ``message`` field.
        status: Alert severity status.
        message: Human-readable alert message.
        error_count_24h: Number of errors in the last 24 hours.
        success_count_24h: Number of successes in the last 24 hours.
        avg_parse_time_ms: Average parse time at the time of the alert.
        is_acknowledged: Whether the alert has been acknowledged.
        acknowledged_at: ISO datetime when the alert was acknowledged.
        created_at: ISO datetime when the alert was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    parser_name: str
    status: str
    message: str
    error_count_24h: int
    success_count_24h: int
    avg_parse_time_ms: float
    is_acknowledged: bool
    acknowledged_at: str | None = None
    created_at: str

    @classmethod
    def from_alert(cls, alert: object) -> "ParserHealthAlertSchema":
        """Build schema from a ``ParserHealthAlert`` ORM instance.

        Extracts ``parser_name`` from the ``message`` field using a best-
        effort parse so that we don't require a live DB join.

        Args:
            alert: ``ParserHealthAlert`` ORM model instance.

        Returns:
            Populated ``ParserHealthAlertSchema``.
        """
        # Extract parser name from the message pattern:
        # "Parser 'NAME' success rate ..."
        import re

        message: str = getattr(alert, "message", "")
        match = re.search(r"Parser '([^']+)'", message)
        parser_name = match.group(1) if match else "unknown"

        created_at_raw = getattr(alert, "created_at", None)
        created_at_str = (
            created_at_raw.isoformat()
            if hasattr(created_at_raw, "isoformat")
            else str(created_at_raw)
        )

        status_raw = getattr(alert, "status", None)
        status_str = status_raw.value if hasattr(status_raw, "value") else str(status_raw)

        return cls(
            id=str(getattr(alert, "id", "")),
            parser_name=parser_name,
            status=status_str,
            message=message,
            error_count_24h=getattr(alert, "error_count_24h", 0),
            success_count_24h=getattr(alert, "success_count_24h", 0),
            avg_parse_time_ms=getattr(alert, "avg_parse_time_ms", 0.0),
            is_acknowledged=getattr(alert, "is_acknowledged", False),
            acknowledged_at=getattr(alert, "acknowledged_at", None),
            created_at=created_at_str,
        )


class AlertListResponse(BaseModel):
    """Paginated list of parser health alerts.

    Attributes:
        items: Page of alert schemas.
        total: Total number of matching alerts.
        page: Current 1-based page number.
        page_size: Number of items per page.
    """

    items: list[ParserHealthAlertSchema]
    total: int
    page: int
    page_size: int


class HealthDashboardResponse(BaseModel):
    """Aggregated dashboard view across all parsers.

    Attributes:
        parsers: Per-parser summaries.
        total_parsers: Total number of parsers with recent activity.
        healthy_count: Number of parsers in 'healthy' status.
        degraded_count: Number of parsers in 'degraded' status.
        failed_count: Number of parsers in 'failed' or 'disabled' status.
    """

    parsers: list[ParserHealthSummarySchema]
    total_parsers: int
    healthy_count: int
    degraded_count: int
    failed_count: int


class MetricsTimeSeriesResponse(BaseModel):
    """Time-series metric history for a single parser.

    Attributes:
        parser_name: Name of the parser.
        metrics: Daily metric snapshots ordered by date ascending.
    """

    parser_name: str
    metrics: list[ParserHealthMetricSchema]


class ErrorBreakdownResponse(BaseModel):
    """Aggregated error type breakdown for a parser over a period.

    Attributes:
        parser_name: Name of the parser.
        errors: Mapping of error type to cumulative count.
        period_days: Number of days the breakdown covers.
    """

    parser_name: str
    errors: dict[str, int]
    period_days: int
