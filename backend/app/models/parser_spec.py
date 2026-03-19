"""SQLAlchemy model for storing JSON-based dynamic parser specs."""

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DynamicParserSpec(Base):
    """Model for storing user-defined or system JSON parser specifications."""

    __tablename__ = "dynamic_parser_specs"

    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )  # None = system/global spec
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    spec_json: Mapped[str] = mapped_column(Text, nullable=False)  # Full JSON spec
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # True for system-provided specs
    is_public: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # True if shared across users

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_dynamic_parser_spec_user_name"),
        Index("idx_dynamic_parser_spec_enabled_priority", "enabled", "priority"),
        Index("idx_dynamic_parser_spec_user_id", "user_id"),
    )
