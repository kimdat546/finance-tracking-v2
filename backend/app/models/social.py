"""Social finance features database models."""

from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Contact(Base):
    """Contact model for split bills and shared expenses."""

    __tablename__ = "contacts"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    split_participants: Mapped[list["SplitParticipant"]] = relationship(
        "SplitParticipant", back_populates="contact", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_contact_user_id", "user_id"),)


class SplitGroup(Base):
    """Group for managing shared expenses."""

    __tablename__ = "split_groups"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3), default="VND")

    # Relationships
    split_bills: Mapped[list["SplitBill"]] = relationship(
        "SplitBill", back_populates="split_group", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_split_group_user_id", "user_id"),)


class SplitBill(Base):
    """Shared expense/bill that needs to be split."""

    __tablename__ = "split_bills"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    split_group_id: Mapped[str] = mapped_column(ForeignKey("split_groups.id"), nullable=False)

    # Bill details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND")

    # Who paid
    payer_contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id"), nullable=False)

    # Status
    is_settled: Mapped[bool] = mapped_column(default=False)
    settled_date: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    split_group: Mapped[SplitGroup] = relationship("SplitGroup", back_populates="split_bills")
    payer_contact: Mapped[Contact] = relationship("Contact")
    participants: Mapped[list["SplitParticipant"]] = relationship(
        "SplitParticipant", back_populates="split_bill", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_split_bill_user_id", "user_id"),
        Index("idx_split_bill_group_id", "split_group_id"),
    )


class SplitParticipant(Base):
    """Participant in a split bill."""

    __tablename__ = "split_participants"

    split_bill_id: Mapped[str] = mapped_column(ForeignKey("split_bills.id"), nullable=False)
    contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id"), nullable=False)

    # Amount owed
    share_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)

    # Payment status
    is_paid: Mapped[bool] = mapped_column(default=False)
    paid_date: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    split_bill: Mapped[SplitBill] = relationship(
        "SplitBill", back_populates="participants"
    )
    contact: Mapped[Contact] = relationship("Contact", back_populates="split_participants")

    __table_args__ = (Index("idx_split_participant_bill_id", "split_bill_id"),)
