"""Tests for WBS-002 categorization services.

Covers:
- RuleEngine (rule matching, priority ordering, test_rule helper)
- PatternLearner (history-based suggestions, learn_from_correction)
- ReviewQueueService (add, get, approve, bulk_approve)
- CategorySeeder (seed categories, idempotency)
- CategoryAnalyticsService (empty state)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import (
    Account,
    Category,
    CategorizationRule,
    Transaction,
    TransactionType,
)
from app.services.categorizer import RuleEngine
from app.services.category_analytics import CategoryAnalyticsService
from app.services.category_seeder import CategorySeeder
from app.services.pattern_learner import PatternLearner
from app.services.review_queue import ReviewQueueService

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

TEST_USER = "00000000-0000-0000-0000-000000000001"


async def _make_user(db: AsyncSession, user_id: str = TEST_USER) -> None:
    """Insert a minimal User row required by FK constraints."""
    from sqlalchemy import select as sa_select

    from app.models.system import User

    result = await db.execute(sa_select(User).where(User.id == user_id))
    if result.scalar_one_or_none() is None:
        user = User(
            id=user_id,
            email=f"{user_id}@example.com",
            username=user_id,
            hashed_password="test-hash",
            schema_name=f"schema_{user_id}",
            is_active=True,
        )
        db.add(user)
        await db.flush()


async def _make_account(db: AsyncSession, user_id: str = TEST_USER) -> Account:
    account = Account(
        user_id=user_id,
        name="Test Account",
        account_type="checking",
        currency="VND",
    )
    db.add(account)
    await db.flush()
    return account


async def _make_category(
    db: AsyncSession,
    user_id: str = TEST_USER,
    name: str = "Food",
    tx_type: TransactionType = TransactionType.EXPENSE,
) -> Category:
    category = Category(
        user_id=user_id,
        name=name,
        transaction_type=tx_type,
        is_active=True,
    )
    db.add(category)
    await db.flush()
    return category


async def _make_rule(
    db: AsyncSession,
    user_id: str,
    category_id: str,
    pattern: str = "coffee",
    match_type: str = "contains",
    match_field: str = "description",
    priority: int = 50,
    name: str = "Test Rule",
) -> CategorizationRule:
    engine = RuleEngine(db)
    return await engine.create_rule(
        user_id=user_id,
        name=name,
        pattern=pattern,
        category_id=category_id,
        priority=priority,
        match_type=match_type,
        match_field=match_field,
    )


async def _make_transaction(
    db: AsyncSession,
    user_id: str,
    account_id: str,
    category_id: str | None = None,
    description: str = "Test transaction",
    merchant: str | None = None,
    amount: float = 100_000.0,
    is_categorized: bool = False,
    categorization_source: str | None = None,
) -> Transaction:
    from decimal import Decimal

    txn = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        description=description,
        merchant=merchant,
        amount=Decimal(str(amount)),
        currency="VND",
        type=TransactionType.EXPENSE,
        transaction_date="2026-03-01",
        source="manual",
        is_categorized=is_categorized,
        categorization_source=categorization_source,
    )
    db.add(txn)
    await db.flush()
    return txn


# ===========================================================================
# RuleEngine tests
# ===========================================================================


@pytest.mark.asyncio
async def test_rule_engine_apply_regex_rule(test_db: AsyncSession) -> None:
    """A regex rule should match the correct transaction description."""
    await _make_user(test_db)
    category = await _make_category(test_db)
    await _make_rule(
        test_db,
        user_id=TEST_USER,
        category_id=category.id,
        pattern=r"grab|gojek",
        match_type="regex",
        match_field="description",
        priority=60,
        name="Ride Hailing",
    )
    await test_db.flush()

    engine = RuleEngine(test_db)
    cat_id, confidence = await engine.apply_rules(
        user_id=TEST_USER,
        description="Payment to Grab",
        merchant=None,
        amount=50_000.0,
    )
    assert cat_id == category.id
    assert confidence > 0.0


@pytest.mark.asyncio
async def test_rule_engine_apply_contains_rule(test_db: AsyncSession) -> None:
    """A 'contains' rule should match when the pattern appears in the description."""
    await _make_user(test_db)
    category = await _make_category(test_db, name="Coffee")
    await _make_rule(
        test_db,
        user_id=TEST_USER,
        category_id=category.id,
        pattern="starbucks",
        match_type="contains",
        match_field="description",
        priority=50,
    )
    await test_db.flush()

    engine = RuleEngine(test_db)
    cat_id, confidence = await engine.apply_rules(
        user_id=TEST_USER,
        description="Starbucks Hanoi branch",
        merchant=None,
        amount=75_000.0,
    )
    assert cat_id == category.id
    assert confidence > 0.0


@pytest.mark.asyncio
async def test_rule_engine_priority_ordering(test_db: AsyncSession) -> None:
    """The rule with higher priority should win when multiple rules match."""
    await _make_user(test_db)
    low_cat = await _make_category(test_db, name="Low Priority")
    high_cat = await _make_category(test_db, name="High Priority")

    # Both rules match description "coffee"
    await _make_rule(
        test_db,
        user_id=TEST_USER,
        category_id=low_cat.id,
        pattern="coffee",
        match_type="contains",
        match_field="description",
        priority=10,
        name="Low Rule",
    )
    await _make_rule(
        test_db,
        user_id=TEST_USER,
        category_id=high_cat.id,
        pattern="coffee",
        match_type="contains",
        match_field="description",
        priority=90,
        name="High Rule",
    )
    await test_db.flush()

    engine = RuleEngine(test_db)
    cat_id, _ = await engine.apply_rules(
        user_id=TEST_USER,
        description="coffee shop",
        merchant=None,
        amount=30_000.0,
    )
    assert cat_id == high_cat.id, "Higher priority rule should win"


@pytest.mark.asyncio
async def test_rule_engine_no_match_returns_none(test_db: AsyncSession) -> None:
    """No matching rule should return (None, 0.0)."""
    await _make_user(test_db)
    category = await _make_category(test_db, name="Shopping")
    await _make_rule(
        test_db,
        user_id=TEST_USER,
        category_id=category.id,
        pattern="shopee",
        match_type="contains",
        match_field="description",
        priority=50,
    )
    await test_db.flush()

    engine = RuleEngine(test_db)
    cat_id, confidence = await engine.apply_rules(
        user_id=TEST_USER,
        description="random ATM withdrawal",
        merchant=None,
        amount=200_000.0,
    )
    assert cat_id is None
    assert confidence == 0.0


@pytest.mark.asyncio
async def test_rule_engine_test_rule(test_db: AsyncSession) -> None:
    """RuleEngine.test_rule should work independently of persisted rules."""
    engine = RuleEngine(test_db)

    # Regex match
    assert await engine.test_rule(
        pattern=r"grab|gojek",
        match_type="regex",
        match_field="description",
        description="Grab payment",
    )
    # Contains match – case-insensitive
    assert await engine.test_rule(
        pattern="STARBUCKS",
        match_type="contains",
        match_field="description",
        description="starbucks latte",
    )
    # startswith
    assert await engine.test_rule(
        pattern="netflix",
        match_type="startswith",
        match_field="description",
        description="Netflix subscription",
    )
    # exact
    assert await engine.test_rule(
        pattern="grab",
        match_type="exact",
        match_field="merchant",
        description="irrelevant",
        merchant="grab",
    )
    # No match
    assert not await engine.test_rule(
        pattern="shopee",
        match_type="contains",
        match_field="description",
        description="ATM withdrawal",
    )


# ===========================================================================
# PatternLearner tests
# ===========================================================================


@pytest.mark.asyncio
async def test_pattern_learner_no_history_returns_none(test_db: AsyncSession) -> None:
    """With no transaction history, suggestion should return (None, 0.0)."""
    await _make_user(test_db)
    learner = PatternLearner(test_db)
    cat_id, confidence = await learner.get_category_suggestion(
        user_id=TEST_USER,
        description="unknown merchant",
        merchant="XYZ Corp",
    )
    assert cat_id is None
    assert confidence == 0.0


@pytest.mark.asyncio
async def test_pattern_learner_learn_from_correction(test_db: AsyncSession) -> None:
    """learn_from_correction should auto-create a rule after >= 3 corrections."""
    await _make_user(test_db)
    account = await _make_account(test_db)
    category = await _make_category(test_db, name="Coffee")

    # Create 3 categorized transactions for the same merchant
    for _ in range(3):
        txn = await _make_transaction(
            test_db,
            user_id=TEST_USER,
            account_id=account.id,
            category_id=category.id,
            description="Morning coffee",
            merchant="Highlands Coffee",
            is_categorized=True,
        )
    await test_db.flush()

    learner = PatternLearner(test_db)
    rule = await learner.learn_from_correction(
        user_id=TEST_USER,
        transaction_id=txn.id,
        old_category_id=None,
        new_category_id=category.id,
        description="Morning coffee",
        merchant="Highlands Coffee",
    )
    assert rule is not None, "A rule should have been auto-created"
    assert rule.pattern == "Highlands Coffee"
    assert rule.category_id == category.id
    assert rule.auto_created is True


# ===========================================================================
# ReviewQueueService tests
# ===========================================================================


@pytest.mark.asyncio
async def test_review_queue_add_and_get(test_db: AsyncSession) -> None:
    """add_to_review should mark a transaction and get_review_queue should return it."""
    await _make_user(test_db)
    account = await _make_account(test_db)
    txn = await _make_transaction(
        test_db,
        user_id=TEST_USER,
        account_id=account.id,
        description="Unclear charge",
    )
    await test_db.flush()

    svc = ReviewQueueService(test_db)
    await svc.add_to_review(
        transaction_id=txn.id,
        user_id=TEST_USER,
        reason="Low confidence",
        confidence=0.3,
    )
    await test_db.flush()

    items, total = await svc.get_review_queue(user_id=TEST_USER)
    assert total == 1
    assert len(items) == 1
    assert items[0].id == txn.id
    assert items[0].needs_review is True
    assert items[0].review_reason == "Low confidence"


@pytest.mark.asyncio
async def test_review_queue_approve(test_db: AsyncSession) -> None:
    """approve_category should assign the category and clear the review flag."""
    await _make_user(test_db)
    account = await _make_account(test_db)
    category = await _make_category(test_db, name="Food")
    txn = await _make_transaction(
        test_db,
        user_id=TEST_USER,
        account_id=account.id,
        description="Lunch",
    )
    svc = ReviewQueueService(test_db)
    await svc.add_to_review(
        transaction_id=txn.id,
        user_id=TEST_USER,
        reason="Needs review",
    )
    await test_db.flush()

    approved = await svc.approve_category(
        transaction_id=txn.id,
        user_id=TEST_USER,
        category_id=category.id,
        learn=False,
    )
    assert approved is not None
    assert approved.category_id == category.id
    assert approved.is_categorized is True
    assert approved.needs_review is False


@pytest.mark.asyncio
async def test_review_queue_bulk_approve(test_db: AsyncSession) -> None:
    """bulk_approve should approve multiple transactions at once."""
    await _make_user(test_db)
    account = await _make_account(test_db)
    category = await _make_category(test_db, name="Transport")

    txns = []
    for i in range(3):
        t = await _make_transaction(
            test_db,
            user_id=TEST_USER,
            account_id=account.id,
            description=f"Charge {i}",
        )
        txns.append(t)
    await test_db.flush()

    svc = ReviewQueueService(test_db)
    for t in txns:
        await svc.add_to_review(
            transaction_id=t.id,
            user_id=TEST_USER,
            reason="Batch review",
        )
    await test_db.flush()

    count = await svc.bulk_approve(
        user_id=TEST_USER,
        approvals=[
            {"transaction_id": t.id, "category_id": category.id, "learn": False}
            for t in txns
        ],
    )
    assert count == 3

    _, total = await svc.get_review_queue(user_id=TEST_USER)
    assert total == 0


# ===========================================================================
# CategorySeeder tests
# ===========================================================================


@pytest.mark.asyncio
async def test_category_seeder_seeds_categories(test_db: AsyncSession) -> None:
    """seed_all should create more than 10 categories for a fresh user."""
    await _make_user(test_db)
    seeder = CategorySeeder(test_db)
    result = await seeder.seed_all(user_id=TEST_USER)
    assert result["categories_created"] > 10


@pytest.mark.asyncio
async def test_category_seeder_idempotent(test_db: AsyncSession) -> None:
    """Running seed_all twice should not create duplicate categories."""
    await _make_user(test_db)
    seeder = CategorySeeder(test_db)
    first = await seeder.seed_all(user_id=TEST_USER)
    await test_db.flush()
    second = await seeder.seed_all(user_id=TEST_USER)
    # Second run should create 0 new categories
    assert second["categories_created"] == 0


# ===========================================================================
# CategoryAnalyticsService tests
# ===========================================================================


@pytest.mark.asyncio
async def test_category_analytics_empty(test_db: AsyncSession) -> None:
    """get_spending_by_category should return an empty list when there is no data."""
    await _make_user(test_db)
    analytics = CategoryAnalyticsService(test_db)
    result = await analytics.get_spending_by_category(user_id=TEST_USER)
    assert result == []
