"""Transaction schema definitions."""

from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.transaction import TransactionType, TransactionStatus


class CategoryBase(BaseModel):
    """Base category schema."""

    name: str = Field(description="Category name")
    description: str | None = Field(default=None, description="Category description")
    icon: str | None = Field(default=None, description="Category icon")
    color: str | None = Field(default=None, description="Category color hex code")
    transaction_type: TransactionType = Field(description="Transaction type")


class CategoryCreate(CategoryBase):
    """Create category schema."""

    parent_id: str | None = Field(default=None, description="Parent category ID")


class CategoryUpdate(BaseModel):
    """Update category schema."""

    name: str | None = Field(default=None, description="Category name")
    description: str | None = Field(default=None, description="Category description")
    icon: str | None = Field(default=None, description="Category icon")
    color: str | None = Field(default=None, description="Category color")
    parent_id: str | None = Field(default=None, description="Parent category ID")
    is_active: bool | None = Field(default=None, description="Is category active")


class CategoryResponse(CategoryBase):
    """Category response schema."""

    id: str = Field(description="Category ID")
    parent_id: str | None = Field(description="Parent category ID")
    is_system: bool = Field(description="Is system category")
    is_active: bool = Field(description="Is active")
    created_at: datetime = Field(description="Created at")
    updated_at: datetime = Field(description="Updated at")

    class Config:
        """Pydantic config."""

        from_attributes = True


class TransactionBase(BaseModel):
    """Base transaction schema."""

    amount: Decimal = Field(decimal_places=2, description="Transaction amount")
    currency: str = Field(default="VND", description="Transaction currency")
    type: TransactionType = Field(description="Transaction type")
    description: str = Field(description="Transaction description")
    merchant: str | None = Field(default=None, description="Merchant name")
    notes: str | None = Field(default=None, description="Additional notes")


class TransactionCreate(TransactionBase):
    """Create transaction schema."""

    account_id: str = Field(description="Account ID")
    category_id: str | None = Field(default=None, description="Category ID")
    transaction_date: str = Field(description="Transaction date")
    booking_date: str | None = Field(default=None, description="Booking date")


class TransactionUpdate(BaseModel):
    """Update transaction schema."""

    category_id: str | None = Field(default=None, description="Category ID")
    description: str | None = Field(default=None, description="Transaction description")
    merchant: str | None = Field(default=None, description="Merchant name")
    notes: str | None = Field(default=None, description="Additional notes")
    status: TransactionStatus | None = Field(default=None, description="Transaction status")
    is_reconciled: bool | None = Field(default=None, description="Is reconciled")


class TransactionIngest(BaseModel):
    """Transaction ingest schema for client-side processing."""

    account_id: str = Field(description="Account ID")
    transactions: list[TransactionCreate] = Field(description="Transactions to ingest")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Batch size")


class TransactionResponse(TransactionBase):
    """Transaction response schema."""

    id: str = Field(description="Transaction ID")
    account_id: str = Field(description="Account ID")
    category_id: str | None = Field(description="Category ID")
    status: TransactionStatus = Field(description="Transaction status")
    source: str = Field(description="Transaction source")
    source_id: str | None = Field(description="Source ID")
    is_categorized: bool = Field(description="Is categorized")
    is_reconciled: bool = Field(description="Is reconciled")
    is_duplicate: bool = Field(description="Is duplicate")
    created_at: datetime = Field(description="Created at")
    updated_at: datetime = Field(description="Updated at")

    class Config:
        """Pydantic config."""

        from_attributes = True


class TransactionListResponse(BaseModel):
    """Transaction list response schema."""

    items: list[TransactionResponse] = Field(description="Transactions")
    total: int = Field(description="Total count")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")
    total_pages: int = Field(description="Total pages")
