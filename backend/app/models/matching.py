"""Matching-related database models for merchant alias resolution and transaction grouping."""

from sqlalchemy import Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Alias(Base):
    """Merchant name aliases for normalization.

    Maps raw merchant names from emails to canonical (normalized) forms,
    enabling consistent grouping and reporting across varied name formats.
    """

    __tablename__ = "aliases"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    original_name: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Raw merchant name from email or transaction"
    )
    canonical_name: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Normalized canonical form of the merchant name"
    )
    confidence: Mapped[float] = mapped_column(
        Float, default=1.0, doc="Confidence score between 0.0 and 1.0"
    )
    source: Mapped[str] = mapped_column(
        String(50), default="manual", doc="Source of alias: 'manual' or 'auto'"
    )

    __table_args__ = (
        Index("idx_alias_user_canonical", "user_id", "canonical_name"),
        Index("idx_alias_user_original", "user_id", "original_name"),
    )


class TransactionGroup(Base):
    """Groups of similar transactions sharing the same merchant or pattern.

    Used to cluster related transactions (e.g., all Grab rides) for aggregated
    analysis and bulk categorization.
    """

    __tablename__ = "transaction_groups"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Group display name (e.g., 'Grab rides')"
    )
    canonical_merchant: Mapped[str | None] = mapped_column(
        String(255), doc="Normalized merchant name for this group"
    )
    category_hint: Mapped[str | None] = mapped_column(
        String(100), doc="Suggested category for the group"
    )
    transaction_count: Mapped[int] = mapped_column(
        default=0, doc="Cached count of transactions in this group"
    )

    # Relationships
    members: Mapped[list["TransactionGroupMember"]] = relationship(
        "TransactionGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("idx_txgroup_user_merchant", "user_id", "canonical_merchant"),)


class TransactionGroupMember(Base):
    """Membership record linking a transaction to a group.

    Tracks which transactions belong to a given group along with the similarity
    score that caused the assignment.
    """

    __tablename__ = "transaction_group_members"

    group_id: Mapped[str] = mapped_column(
        ForeignKey("transaction_groups.id"), nullable=False
    )
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.id"), nullable=False
    )
    similarity_score: Mapped[float] = mapped_column(
        Float, default=1.0, doc="Similarity score (0.0-1.0) used for assignment"
    )

    # Relationships
    group: Mapped["TransactionGroup"] = relationship(
        "TransactionGroup", back_populates="members"
    )

    __table_args__ = (
        UniqueConstraint("group_id", "transaction_id", name="uq_group_transaction"),
        Index("idx_txgroupmember_group", "group_id"),
        Index("idx_txgroupmember_transaction", "transaction_id"),
    )
