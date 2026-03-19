"""Health monitoring database models for parser metrics and disabled logs."""

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ParserHealthMetric(Base):
    """Time-series health metrics per parser per day.

    Stores aggregated daily metrics for each parser, optionally scoped to a
    specific user and/or transaction type.  The combination of
    (parser_name, metric_date, user_id, transaction_type) is unique so that
    repeated calls on the same day update the existing row (upsert pattern).
    """

    __tablename__ = "parser_health_metrics"

    # Identity
    parser_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    # "YYYY-MM-DD" stored as String for SQLite compatibility
    metric_date: Mapped[str] = mapped_column(String(10), nullable=False)
    # "income" | "expense" | "transfer" | None (all types)
    transaction_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Counters
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Cumulative milliseconds for average-time calculation
    total_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # JSON-encoded breakdown of failure types, e.g. {"parsing_error": 3}
    error_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # Nullable-safe unique constraint: use a composite approach where NULLs
        # are treated as distinct by SQLite/PostgreSQL (ISO SQL behaviour).
        # The application layer enforces the logical uniqueness via upsert logic.
        UniqueConstraint(
            "parser_name",
            "metric_date",
            "user_id",
            "transaction_type",
            name="uq_parser_health_metric",
        ),
        Index("idx_phm_parser_date", "parser_name", "metric_date"),
        Index("idx_phm_user_date", "user_id", "metric_date"),
    )

    @property
    def success_rate(self) -> float:
        """Fraction of successful attempts; 0.0 if no attempts recorded."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    @property
    def avg_parse_time_ms(self) -> float:
        """Average parse time in milliseconds; 0.0 if no attempts recorded."""
        total = self.success_count + self.failure_count
        return self.total_time_ms / total if total > 0 else 0.0


class ParserDisabledLog(Base):
    """Log of automatic parser disabling events.

    Records when a parser was automatically disabled due to falling below the
    failure-rate threshold, and optionally when it was re-enabled.
    """

    __tablename__ = "parser_disabled_logs"

    parser_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # Success rate at the moment the parser was disabled
    success_rate: Mapped[float] = mapped_column(Float, nullable=False)
    # ISO-8601 datetime strings for SQLite compatibility
    disabled_at: Mapped[str] = mapped_column(String(50), nullable=False)
    re_enabled_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # True while the parser remains disabled
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("idx_pdl_parser_name", "parser_name"),
        Index("idx_pdl_user_id", "user_id"),
    )
