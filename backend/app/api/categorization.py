"""Categorization API – rules, review queue, suggestions, learning and analytics."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.transaction import CategorizationRule, Transaction
from app.schemas.categorization import (
    ApproveRequest,
    BulkApproveRequest,
    CategorizationRuleCreateRequest,
    CategorizationRuleSchema,
    CategorizationRuleUpdateRequest,
    CategorizationStatsSchema,
    CategorySuggestRequest,
    CategorySuggestResponse,
    CategoryTrendSchema,
    LearnCorrectionRequest,
    ReviewQueueItemSchema,
    ReviewQueueStatsSchema,
    RuleTestRequest,
    RuleTestResponse,
    SpendingByCategorySchema,
)
from app.services.categorizer import RuleEngine
from app.services.category_analytics import CategoryAnalyticsService
from app.services.category_seeder import CategorySeeder
from app.services.pattern_learner import PatternLearner
from app.services.review_queue import ReviewQueueService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categorization", tags=["categorization"])

# ---------------------------------------------------------------------------
# Hard-coded user ID – auth will be wired in WBS-007
# ---------------------------------------------------------------------------
CURRENT_USER_ID = "00000000-0000-0000-0000-000000000001"


# ===========================================================================
# Categorization Rules
# ===========================================================================


@router.get("/rules", response_model=list[CategorizationRuleSchema])
async def list_rules(
    is_active: bool | None = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
) -> list[CategorizationRuleSchema]:
    """List all categorization rules for the current user."""
    stmt = select(CategorizationRule).where(
        CategorizationRule.user_id == CURRENT_USER_ID
    )
    if is_active is not None:
        stmt = stmt.where(CategorizationRule.is_active == is_active)
    stmt = stmt.order_by(CategorizationRule.priority.desc())
    result = await db.execute(stmt)
    rules = result.scalars().all()
    return [CategorizationRuleSchema.model_validate(r) for r in rules]


@router.post("/rules", response_model=CategorizationRuleSchema, status_code=201)
async def create_rule(
    body: CategorizationRuleCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> CategorizationRuleSchema:
    """Create a new categorization rule."""
    engine = RuleEngine(db)
    rule = await engine.create_rule(
        user_id=CURRENT_USER_ID,
        name=body.name,
        pattern=body.pattern,
        category_id=body.category_id,
        priority=body.priority,
        match_type=body.match_type,
        match_field=body.match_field,
    )
    await db.commit()
    await db.refresh(rule)
    return CategorizationRuleSchema.model_validate(rule)


@router.get("/rules/{rule_id}", response_model=CategorizationRuleSchema)
async def get_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
) -> CategorizationRuleSchema:
    """Get a specific categorization rule by ID."""
    result = await db.execute(
        select(CategorizationRule).where(
            CategorizationRule.id == rule_id,
            CategorizationRule.user_id == CURRENT_USER_ID,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return CategorizationRuleSchema.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=CategorizationRuleSchema)
async def update_rule(
    rule_id: str,
    body: CategorizationRuleUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> CategorizationRuleSchema:
    """Update an existing categorization rule."""
    result = await db.execute(
        select(CategorizationRule).where(
            CategorizationRule.id == rule_id,
            CategorizationRule.user_id == CURRENT_USER_ID,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return CategorizationRuleSchema.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete (soft-disable) a categorization rule."""
    result = await db.execute(
        select(CategorizationRule).where(
            CategorizationRule.id == rule_id,
            CategorizationRule.user_id == CURRENT_USER_ID,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.is_active = False
    db.add(rule)
    await db.commit()


@router.post("/rules/test", response_model=RuleTestResponse)
async def test_rule(
    body: RuleTestRequest,
    db: AsyncSession = Depends(get_db),
) -> RuleTestResponse:
    """Test a rule pattern against sample transaction data."""
    engine = RuleEngine(db)
    matched = await engine.test_rule(
        pattern=body.pattern,
        match_type=body.match_type,
        match_field=body.match_field,
        description=body.description,
        merchant=body.merchant,
    )
    # Also surface existing rules that match the same sample
    matching_rules = await engine.get_matching_rules(
        user_id=CURRENT_USER_ID,
        description=body.description,
        merchant=body.merchant,
    )
    return RuleTestResponse(
        matched=matched,
        matching_rules=[
            {"rule_id": r.id, "rule_name": r.name, "confidence": conf}
            for r, conf in matching_rules
        ],
    )


# ===========================================================================
# Review Queue
# ===========================================================================


@router.get("/review", response_model=dict)
async def get_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a paginated list of transactions awaiting review."""
    svc = ReviewQueueService(db)
    items, total = await svc.get_review_queue(
        user_id=CURRENT_USER_ID,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [ReviewQueueItemSchema.model_validate(t) for t in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


@router.get("/review/stats", response_model=ReviewQueueStatsSchema)
async def get_review_stats(
    db: AsyncSession = Depends(get_db),
) -> ReviewQueueStatsSchema:
    """Return review queue statistics."""
    svc = ReviewQueueService(db)
    stats = await svc.get_queue_stats(user_id=CURRENT_USER_ID)
    return ReviewQueueStatsSchema(**stats)


@router.post("/review/{transaction_id}/approve", response_model=ReviewQueueItemSchema)
async def approve_category(
    transaction_id: str,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> ReviewQueueItemSchema:
    """Approve a category for a transaction in the review queue."""
    svc = ReviewQueueService(db)
    txn = await svc.approve_category(
        transaction_id=transaction_id,
        user_id=CURRENT_USER_ID,
        category_id=body.category_id,
        learn=body.learn,
    )
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.commit()
    await db.refresh(txn)
    return ReviewQueueItemSchema.model_validate(txn)


@router.post("/review/bulk-approve", response_model=dict)
async def bulk_approve(
    body: BulkApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bulk approve categories for multiple transactions."""
    svc = ReviewQueueService(db)
    count = await svc.bulk_approve(
        user_id=CURRENT_USER_ID,
        approvals=body.approvals,
    )
    await db.commit()
    return {"approved": count}


@router.post("/review/{transaction_id}/dismiss", response_model=dict)
async def dismiss_from_review(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Dismiss a transaction from the review queue without categorizing."""
    svc = ReviewQueueService(db)
    ok = await svc.dismiss_from_review(
        transaction_id=transaction_id,
        user_id=CURRENT_USER_ID,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.commit()
    return {"dismissed": True}


# ===========================================================================
# Suggestions & Learning
# ===========================================================================


@router.post("/suggest", response_model=CategorySuggestResponse)
async def suggest_category(
    body: CategorySuggestRequest,
    db: AsyncSession = Depends(get_db),
) -> CategorySuggestResponse:
    """Suggest a category for the given description and merchant."""
    # First try the rule engine for a deterministic match
    engine = RuleEngine(db)
    cat_id, confidence = await engine.apply_rules(
        user_id=CURRENT_USER_ID,
        description=body.description,
        merchant=body.merchant,
        amount=body.amount or 0.0,
    )
    if cat_id:
        await db.commit()
        return CategorySuggestResponse(
            category_id=cat_id, confidence=confidence, source="rule"
        )

    # Fall back to pattern learner
    learner = PatternLearner(db)
    cat_id, confidence = await learner.get_category_suggestion(
        user_id=CURRENT_USER_ID,
        description=body.description,
        merchant=body.merchant,
        amount=body.amount,
    )
    if cat_id:
        return CategorySuggestResponse(
            category_id=cat_id, confidence=confidence, source="pattern"
        )

    return CategorySuggestResponse(category_id=None, confidence=0.0, source="none")


@router.post("/learn", response_model=dict)
async def learn_correction(
    body: LearnCorrectionRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Record a manual category correction for pattern learning."""
    learner = PatternLearner(db)
    rule = await learner.learn_from_correction(
        user_id=CURRENT_USER_ID,
        transaction_id=body.transaction_id,
        old_category_id=body.old_category_id,
        new_category_id=body.new_category_id,
        description=body.description,
        merchant=body.merchant,
    )
    await db.commit()
    return {
        "learned": True,
        "rule_created": rule is not None,
        "rule_id": rule.id if rule else None,
    }


# ===========================================================================
# Overall Stats
# ===========================================================================


@router.get("/stats", response_model=CategorizationStatsSchema)
async def get_categorization_stats(
    db: AsyncSession = Depends(get_db),
) -> CategorizationStatsSchema:
    """Return overall categorization statistics for the current user."""
    user_id = CURRENT_USER_ID

    total_result = await db.execute(
        select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)
    )
    total: int = total_result.scalar_one()

    auto_result = await db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.categorization_source == "rule",
            Transaction.is_categorized == True,  # noqa: E712
        )
    )
    auto: int = auto_result.scalar_one()

    manual_result = await db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.categorization_source == "manual",
            Transaction.is_categorized == True,  # noqa: E712
        )
    )
    manual: int = manual_result.scalar_one()

    pending_result = await db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.needs_review == True,  # noqa: E712
        )
    )
    pending: int = pending_result.scalar_one()

    total_cat = auto + manual
    accuracy_rate = round(total_cat / total, 3) if total else 0.0
    auto_rate = round(auto / total_cat, 3) if total_cat else 0.0

    return CategorizationStatsSchema(
        auto_categorized=auto,
        manual=manual,
        pending_review=pending,
        total_categorized=total_cat,
        total_transactions=total,
        accuracy_rate=accuracy_rate,
        auto_rate=auto_rate,
    )


# ===========================================================================
# Category Seeding
# ===========================================================================


@router.post("/seed", response_model=dict, status_code=201)
async def seed_categories(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Seed default categories and rules for the current user."""
    seeder = CategorySeeder(db)
    result = await seeder.seed_all(user_id=CURRENT_USER_ID)
    await db.commit()
    return {**result, "already_seeded": False}


# ===========================================================================
# Category Analytics
# ===========================================================================


@router.get("/analytics/spending", response_model=list[SpendingByCategorySchema])
async def spending_by_category(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    transaction_type: str = Query("expense", description="income | expense | transfer"),
    db: AsyncSession = Depends(get_db),
) -> list[SpendingByCategorySchema]:
    """Get spending totals grouped by category."""
    analytics = CategoryAnalyticsService(db)
    rows = await analytics.get_spending_by_category(
        user_id=CURRENT_USER_ID,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
    )
    return [SpendingByCategorySchema(**row) for row in rows]


@router.get(
    "/analytics/trend/{category_id}", response_model=list[CategoryTrendSchema]
)
async def category_trend(
    category_id: str,
    months: int = Query(6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
) -> list[CategoryTrendSchema]:
    """Return monthly spending trend for a specific category."""
    analytics = CategoryAnalyticsService(db)
    rows = await analytics.get_category_trend(
        user_id=CURRENT_USER_ID,
        category_id=category_id,
        months=months,
    )
    return [CategoryTrendSchema(**row) for row in rows]


@router.get("/analytics/uncategorized", response_model=dict)
async def uncategorized_stats(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return stats about uncategorized transactions."""
    analytics = CategoryAnalyticsService(db)
    return await analytics.get_uncategorized_stats(user_id=CURRENT_USER_ID)


@router.get("/analytics/top-merchants", response_model=list[dict])
async def top_merchants(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return top merchants by spend in the last N days."""
    analytics = CategoryAnalyticsService(db)
    return await analytics.get_top_merchants(
        user_id=CURRENT_USER_ID, limit=limit, days=days
    )
