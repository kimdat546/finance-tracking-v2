"""Pydantic v2 schemas for merchant matching, alias management, and transaction groups."""

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Alias schemas
# ---------------------------------------------------------------------------


class AliasCreateRequest(BaseModel):
    """Request body for creating a single merchant alias."""

    original_name: str = Field(description="Raw merchant name from email or transaction")
    canonical_name: str = Field(description="Normalized canonical form to map to")


class AliasSchema(BaseModel):
    """Response representation of a merchant alias."""

    id: str = Field(description="Alias ID")
    original_name: str = Field(description="Raw merchant name")
    canonical_name: str = Field(description="Canonical merchant name")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    source: str = Field(description="Source of alias: 'manual' or 'auto'")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = {"from_attributes": True}


class AliasListResponse(BaseModel):
    """Paginated list of merchant aliases."""

    items: list[AliasSchema] = Field(description="Alias records")
    total: int = Field(description="Total number of aliases")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")


# ---------------------------------------------------------------------------
# Transaction group schemas
# ---------------------------------------------------------------------------


class TransactionGroupSchema(BaseModel):
    """Response representation of a transaction group."""

    id: str = Field(description="Group ID")
    name: str = Field(description="Group display name")
    canonical_merchant: str | None = Field(
        default=None, description="Normalized merchant name for this group"
    )
    category_hint: str | None = Field(
        default=None, description="Suggested category for the group"
    )
    transaction_count: int = Field(description="Cached count of transactions in this group")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = {"from_attributes": True}


class TransactionGroupListResponse(BaseModel):
    """Paginated list of transaction groups."""

    items: list[TransactionGroupSchema] = Field(description="Group records")
    total: int = Field(description="Total number of groups")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")


# ---------------------------------------------------------------------------
# Similarity report schema
# ---------------------------------------------------------------------------


class SimilarityReportResponse(BaseModel):
    """Response for a merchant similarity report."""

    input: str = Field(description="Original input merchant name")
    normalized: str = Field(description="Normalized form of the input name")
    alias: str | None = Field(
        default=None, description="Canonical name from alias table if found"
    )
    similar_merchants: list[dict] = Field(
        description="List of similar merchants with their similarity scores"
    )


# ---------------------------------------------------------------------------
# Bulk alias schema
# ---------------------------------------------------------------------------


class BulkAliasRequest(BaseModel):
    """Request body for bulk alias creation."""

    mappings: list[AliasCreateRequest] = Field(
        description="List of original->canonical alias mappings"
    )


# ---------------------------------------------------------------------------
# Auto-group schema
# ---------------------------------------------------------------------------


class AutoGroupRequest(BaseModel):
    """Request body for auto-grouping transactions by merchant."""

    merchant_name: str = Field(description="Merchant name to group transactions by")
    threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for including a transaction in the group",
    )


# ---------------------------------------------------------------------------
# Group creation schema
# ---------------------------------------------------------------------------


class TransactionGroupCreateRequest(BaseModel):
    """Request body for creating a transaction group."""

    name: str = Field(description="Group display name")
    merchant_name: str | None = Field(
        default=None, description="Optional canonical merchant name for the group"
    )
