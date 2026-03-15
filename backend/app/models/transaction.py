"""Transaction-related database models."""

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


class TransactionType(str, Enum):
    """Transaction type enumeration."""

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class TransactionStatus(str, Enum):
    """Transaction status enumeration."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    RECONCILED = "reconciled"
    DISPUTED = "disputed"
    ARCHIVED = "archived"


class Account(Base):
    """Bank account model."""

    __tablename__ = "accounts"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    balance: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    institution: Mapped[str | None] = mapped_column(String(255))
    account_number: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )
    categorization_rules: Mapped[list["CategorizationRule"]] = relationship(
        "CategorizationRule", back_populates="account", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_account_user_id", "user_id"),)


class Category(Base):
    """Transaction category model with hierarchical support."""

    __tablename__ = "categories"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(7))
    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType), nullable=False
    )
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="category"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category",
        remote_side=[id],
        backref="parent",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_category_user_id", "user_id"),
        Index("idx_category_parent_id", "parent_id"),
    )


class Transaction(Base):
    """Financial transaction model."""

    __tablename__ = "transactions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"))

    # Core transaction data
    amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType))
    status: Mapped[TransactionStatus] = mapped_column(
        SQLEnum(TransactionStatus), default=TransactionStatus.PENDING
    )

    # Description and metadata
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    merchant: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

    # Dates
    transaction_date: Mapped[str] = mapped_column(String(50))
    booking_date: Mapped[str | None] = mapped_column(String(50))

    # Source information
    source: Mapped[str] = mapped_column(String(100), default="manual")
    source_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    email_id: Mapped[str | None] = mapped_column(String(255))

    # Processing flags
    is_categorized: Mapped[bool] = mapped_column(Boolean, default=False)
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    account: Mapped[Account] = relationship("Account", back_populates="transactions")
    category: Mapped[Category | None] = relationship("Category", back_populates="transactions")

    __table_args__ = (
        Index("idx_transaction_user_id", "user_id"),
        Index("idx_transaction_account_id", "account_id"),
        Index("idx_transaction_category_id", "category_id"),
        Index("idx_transaction_source_id", "source_id"),
        Index("idx_transaction_date", "transaction_date"),
    )


class CategorizationRule(Base):
    """Rule for automatic transaction categorization."""

    __tablename__ = "categorization_rules"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)

    # Rule matching criteria
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Pattern matching
    merchant_pattern: Mapped[str | None] = mapped_column(String(255))
    description_pattern: Mapped[str | None] = mapped_column(String(255))
    min_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2))
    max_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2))
    transaction_type: Mapped[TransactionType | None] = mapped_column(
        SQLEnum(TransactionType)
    )

    # Priority and status
    priority: Mapped[int] = mapped_column(default=0)
    is_regex: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Match statistics
    match_count: Mapped[int] = mapped_column(default=0)
    last_matched_at: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    account: Mapped[Account] = relationship("Account", back_populates="categorization_rules")
    category: Mapped[Category] = relationship("Category")

    __table_args__ = (
        Index("idx_rule_user_id", "user_id"),
        Index("idx_rule_account_id", "account_id"),
    )
