"""Pydantic schemas for the categorization feature (WBS-002)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.transaction import TransactionResponse


# ---------------------------------------------------------------------------
# Categorization Rules
# ---------------------------------------------------------------------------


class CategorizationRuleSchema(BaseModel):
    """Full representation of a categorization rule."""

    id: str = Field(description="Rule ID")
    user_id: str = Field(description="Owner user ID")
    name: str = Field(description="Human-readable rule name")
    pattern: str = Field(description="Matching pattern")
    match_type: str = Field(
        description="Matching strategy: contains | regex | startswith | exact"
    )
    match_field: str = Field(description="Field to match: description | merchant | any")
    category_id: str = Field(description="Category assigned when rule matches")
    priority: int = Field(description="Priority (higher = evaluated first)")
    is_active: bool = Field(description="Whether the rule is active")
    auto_created: bool = Field(description="Whether created automatically by learner")
    match_count: int = Field(description="Number of times this rule has matched")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True


class CategorizationRuleCreateRequest(BaseModel):
    """Request body for creating a new categorization rule."""

    name: str = Field(description="Human-readable rule name")
    pattern: str = Field(description="Matching pattern")
    match_type: str = Field(
        default="contains",
        description="Matching strategy: contains | regex | startswith | exact",
    )
    match_field: str = Field(
        default="description",
        description="Field to match: description | merchant | any",
    )
    category_id: str = Field(description="Category to assign when rule matches")
    priority: int = Field(default=50, ge=0, le=100, description="Rule priority (0–100)")


class CategorizationRuleUpdateRequest(BaseModel):
    """Request body for updating an existing categorization rule."""

    name: str | None = Field(default=None, description="New rule name")
    pattern: str | None = Field(default=None, description="New pattern")
    match_type: str | None = Field(default=None, description="New match type")
    match_field: str | None = Field(default=None, description="New match field")
    category_id: str | None = Field(default=None, description="New category ID")
    priority: int | None = Field(default=None, ge=0, le=100, description="New priority")
    is_active: bool | None = Field(default=None, description="Enable or disable rule")


class RuleTestRequest(BaseModel):
    """Request body for testing a rule pattern against sample data."""

    pattern: str = Field(description="Pattern to test")
    match_type: str = Field(default="contains", description="Match strategy")
    match_field: str = Field(default="description", description="Field to test against")
    description: str = Field(description="Sample transaction description")
    merchant: str | None = Field(default=None, description="Sample merchant name")


class RuleTestResponse(BaseModel):
    """Response body for a rule test."""

    matched: bool = Field(description="Whether the pattern matched")
    matching_rules: list[dict] = Field(
        default_factory=list,
        description="Existing rules that match the same sample data",
    )


# ---------------------------------------------------------------------------
# Category Suggestion
# ---------------------------------------------------------------------------


class CategorySuggestRequest(BaseModel):
    """Request body for getting a category suggestion."""

    description: str = Field(description="Transaction description")
    merchant: str | None = Field(default=None, description="Merchant name")
    amount: float | None = Field(default=None, description="Transaction amount")


class CategorySuggestResponse(BaseModel):
    """Response body for a category suggestion."""

    category_id: str | None = Field(description="Suggested category ID (None if no suggestion)")
    confidence: float = Field(description="Confidence score 0.0–1.0")
    source: str = Field(description="Suggestion source: rule | pattern | none")


# ---------------------------------------------------------------------------
# Review Queue
# ---------------------------------------------------------------------------


class ReviewQueueItemSchema(BaseModel):
    """A transaction in the review queue with additional review metadata."""

    id: str = Field(description="Transaction ID")
    user_id: str = Field(description="Owner user ID")
    account_id: str = Field(description="Account ID")
    category_id: str | None = Field(description="Current category ID")
    amount: Decimal = Field(description="Transaction amount")
    currency: str = Field(description="Currency code")
    description: str = Field(description="Transaction description")
    merchant: str | None = Field(description="Merchant name")
    transaction_date: str = Field(description="Transaction date")
    needs_review: bool = Field(description="Whether review is needed")
    review_reason: str | None = Field(description="Reason for review")
    suggested_category_id: str | None = Field(description="Auto-suggested category ID")
    categorization_confidence: float = Field(description="Confidence of suggestion")
    categorization_source: str | None = Field(description="Source of categorization")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True


class ReviewQueueStatsSchema(BaseModel):
    """Statistics about the review queue."""

    total: int = Field(description="Total items in queue")
    by_confidence: dict = Field(description="Items grouped by confidence bucket")
    oldest_date: str | None = Field(description="ISO timestamp of oldest queued item")


class ApproveRequest(BaseModel):
    """Request body for approving a single transaction category."""

    category_id: str = Field(description="Category to assign")
    learn: bool = Field(default=True, description="Whether to record for learning")


class BulkApproveRequest(BaseModel):
    """Request body for bulk-approving transaction categories."""

    approvals: list[dict] = Field(
        description="List of {transaction_id, category_id, learn?} dicts"
    )


# ---------------------------------------------------------------------------
# Learning
# ---------------------------------------------------------------------------


class LearnCorrectionRequest(BaseModel):
    """Request body for recording a manual correction for learning."""

    transaction_id: str = Field(description="Transaction that was corrected")
    old_category_id: str | None = Field(default=None, description="Previous category")
    new_category_id: str = Field(description="New (correct) category")
    description: str = Field(description="Transaction description")
    merchant: str | None = Field(default=None, description="Merchant name")


# ---------------------------------------------------------------------------
# Categorization Stats
# ---------------------------------------------------------------------------


class CategorizationStatsSchema(BaseModel):
    """Overall categorization statistics for a user."""

    auto_categorized: int = Field(description="Transactions categorized by rules")
    manual: int = Field(description="Manually categorized transactions")
    pending_review: int = Field(description="Transactions awaiting review")
    total_categorized: int = Field(description="Total categorized transactions")
    total_transactions: int = Field(description="All transactions")
    accuracy_rate: float = Field(description="Estimated accuracy (0.0–1.0)")
    auto_rate: float = Field(description="Fraction auto-categorized (0.0–1.0)")


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class SpendingByCategorySchema(BaseModel):
    """Spending total for one category."""

    category_id: str = Field(description="Category ID")
    category_name: str = Field(description="Category name")
    total: float = Field(description="Total amount spent")
    count: int = Field(description="Number of transactions")
    percentage: float = Field(description="Share of total spending (%)")


class CategoryTrendSchema(BaseModel):
    """Monthly spending trend entry."""

    month: str = Field(description="Month in YYYY-MM format")
    total: float = Field(description="Total amount for this month")
    count: int = Field(description="Number of transactions")
