"""Financial planning database models."""

from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    DECIMAL,
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BudgetPeriod(str, Enum):
    """Budget period enumeration."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class GoalStatus(str, Enum):
    """Goal status enumeration."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class DebtStatus(str, Enum):
    """Debt status enumeration."""

    ACTIVE = "active"
    PAUSED = "paused"
    PAID_OFF = "paid_off"


class Budget(Base):
    """Budget model for expense tracking."""

    __tablename__ = "budgets"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)

    # Budget details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    limit_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND")

    # Period
    period: Mapped[BudgetPeriod] = mapped_column(
        SQLEnum(BudgetPeriod), default=BudgetPeriod.MONTHLY
    )
    start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    end_date: Mapped[str | None] = mapped_column(String(50))

    # Tracking
    current_spent: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), default=Decimal("0"))
    alert_threshold: Mapped[int] = mapped_column(default=80)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    category: Mapped["Category"] = relationship("Category")

    __table_args__ = (
        Index("idx_budget_user_id", "user_id"),
        Index("idx_budget_category_id", "category_id"),
    )


class Goal(Base):
    """Financial goal model."""

    __tablename__ = "goals"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Goal details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="VND")

    # Timeline
    start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    target_date: Mapped[str] = mapped_column(String(50), nullable=False)

    # Status and priority
    status: Mapped[GoalStatus] = mapped_column(
        SQLEnum(GoalStatus), default=GoalStatus.ACTIVE
    )
    priority: Mapped[int] = mapped_column(default=0)
    icon: Mapped[str | None] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(7))

    __table_args__ = (Index("idx_goal_user_id", "user_id"),)


class Debt(Base):
    """Debt tracking model."""

    __tablename__ = "debts"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Debt details
    creditor: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    original_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND")

    # Interest and terms
    interest_rate: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 2))
    monthly_payment: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2))

    # Dates
    start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    due_date: Mapped[str | None] = mapped_column(String(50))
    paid_off_date: Mapped[str | None] = mapped_column(String(50))

    # Status
    status: Mapped[DebtStatus] = mapped_column(
        SQLEnum(DebtStatus), default=DebtStatus.ACTIVE
    )

    __table_args__ = (Index("idx_debt_user_id", "user_id"),)


class Subscription(Base):
    """Recurring subscription/payment model."""

    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"))

    # Subscription details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND")

    # Billing cycle
    billing_period: Mapped[BudgetPeriod] = mapped_column(
        SQLEnum(BudgetPeriod), default=BudgetPeriod.MONTHLY
    )

    # Dates
    start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    next_billing_date: Mapped[str] = mapped_column(String(50), nullable=False)
    end_date: Mapped[str | None] = mapped_column(String(50))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    category: Mapped["Category | None"] = relationship("Category")

    __table_args__ = (
        Index("idx_subscription_user_id", "user_id"),
        Index("idx_subscription_category_id", "category_id"),
    )
