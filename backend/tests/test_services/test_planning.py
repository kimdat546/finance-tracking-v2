"""Tests for WBS-004 planning services: budgets, goals, debts, subscriptions.

Covers:
- BudgetService: create, get_with_spending (no transactions), alerts
- GoalService: create, add_contribution, summary
- DebtService: create (owe type), record_payment
- SubscriptionService: create, summary, upcoming_renewals
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import Budget, Debt, Goal, Subscription
from app.models.transaction import Category, TransactionType
from app.schemas.planning import (
    BudgetCreateRequest,
    DebtCreateRequest,
    GoalCreateRequest,
    SubscriptionCreateRequest,
)
from app.services.budget_service import BudgetService
from app.services.debt_service import DebtService
from app.services.goal_service import GoalService
from app.services.subscription_service import SubscriptionService

# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------

TEST_USER = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


async def _make_user(db: AsyncSession, user_id: str = TEST_USER) -> None:
    """Insert a minimal User row required by FK constraints."""
    from sqlalchemy import select

    from app.models.system import User

    result = await db.execute(select(User).where(User.id == user_id))
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


async def _make_category(
    db: AsyncSession,
    user_id: str = TEST_USER,
    name: str = "Test Category",
    tx_type: TransactionType = TransactionType.EXPENSE,
) -> Category:
    """Create and flush a minimal Category row."""
    category = Category(
        user_id=user_id,
        name=name,
        transaction_type=tx_type,
        is_active=True,
    )
    db.add(category)
    await db.flush()
    return category


# ===========================================================================
# BudgetService tests
# ===========================================================================


@pytest.mark.asyncio
async def test_create_budget(test_db: AsyncSession) -> None:
    """BudgetService.create_budget should persist a new budget row."""
    await _make_user(test_db)
    category = await _make_category(test_db)

    service = BudgetService(test_db)
    data = BudgetCreateRequest(
        category_id=category.id,
        name="Ăn uống tháng 3",
        amount=Decimal("3000000"),
        start_date="2026-03-01",
        end_date="2026-03-31",
    )
    budget = await service.create_budget(TEST_USER, data)

    assert budget.id is not None
    assert budget.user_id == TEST_USER
    assert budget.category_id == category.id
    assert budget.limit_amount == Decimal("3000000")
    assert budget.is_active is True


@pytest.mark.asyncio
async def test_get_budget_with_spending_empty(test_db: AsyncSession) -> None:
    """get_budget_with_spending returns spent_amount=0 when no transactions exist."""
    await _make_user(test_db)
    category = await _make_category(test_db)

    service = BudgetService(test_db)
    data = BudgetCreateRequest(
        category_id=category.id,
        name="Di chuyển",
        amount=Decimal("1000000"),
        start_date="2026-03-01",
    )
    budget = await service.create_budget(TEST_USER, data)
    result = await service.get_budget_with_spending(budget.id, TEST_USER)

    assert result is not None
    assert result["spent_amount"] == Decimal("0")
    assert result["remaining"] == Decimal("1000000")
    assert result["percentage_used"] == 0.0


@pytest.mark.asyncio
async def test_budget_alerts_empty(test_db: AsyncSession) -> None:
    """get_budget_alerts returns empty list when no budgets exceed threshold."""
    await _make_user(test_db)
    category = await _make_category(test_db)

    service = BudgetService(test_db)
    data = BudgetCreateRequest(
        category_id=category.id,
        name="Giải trí",
        amount=Decimal("5000000"),
        start_date="2026-03-01",
    )
    await service.create_budget(TEST_USER, data)

    alerts = await service.get_budget_alerts(TEST_USER)
    # No transactions → spent is 0 → no alerts
    assert alerts == []


# ===========================================================================
# GoalService tests
# ===========================================================================


@pytest.mark.asyncio
async def test_create_goal(test_db: AsyncSession) -> None:
    """GoalService.create_goal should persist a new goal with current_amount=0."""
    await _make_user(test_db)

    service = GoalService(test_db)
    data = GoalCreateRequest(
        name="Mua xe máy",
        target_amount=Decimal("30000000"),
        start_date="2026-01-01",
        target_date="2026-12-31",
    )
    goal = await service.create_goal(TEST_USER, data)

    assert goal.id is not None
    assert goal.name == "Mua xe máy"
    assert goal.current_amount == Decimal("0")
    assert goal.target_amount == Decimal("30000000")


@pytest.mark.asyncio
async def test_goal_add_contribution(test_db: AsyncSession) -> None:
    """add_contribution should increase current_amount by the given amount."""
    await _make_user(test_db)

    service = GoalService(test_db)
    data = GoalCreateRequest(
        name="Du lịch Đà Nẵng",
        target_amount=Decimal("10000000"),
        start_date="2026-01-01",
        target_date="2026-06-30",
    )
    goal = await service.create_goal(TEST_USER, data)

    updated = await service.add_contribution(goal.id, 2_000_000, TEST_USER)

    assert updated is not None
    assert updated.current_amount == Decimal("2000000")


@pytest.mark.asyncio
async def test_goals_summary_structure(test_db: AsyncSession) -> None:
    """get_goals_summary should return a dict with the expected keys."""
    await _make_user(test_db)

    service = GoalService(test_db)
    summary = await service.get_goals_summary(TEST_USER)

    expected_keys = {
        "total_goals",
        "active_goals",
        "completed_goals",
        "total_target",
        "total_saved",
        "completion_percentage",
    }
    assert expected_keys.issubset(summary.keys())


# ===========================================================================
# DebtService tests
# ===========================================================================


@pytest.mark.asyncio
async def test_create_debt_owe_type(test_db: AsyncSession) -> None:
    """DebtService.create_debt should persist a debt with type 'owe'."""
    await _make_user(test_db)

    service = DebtService(test_db)
    data = DebtCreateRequest(
        name="Nợ bạn Minh",
        creditor="Nguyễn Văn Minh",
        amount=Decimal("5000000"),
        start_date="2026-03-01",
        debt_type="owe",
    )
    debt = await service.create_debt(TEST_USER, data)

    assert debt.id is not None
    assert debt.user_id == TEST_USER
    assert debt.original_amount == Decimal("5000000")
    assert debt.remaining_amount == Decimal("5000000")

    # Verify debt_type decoding
    debt_dict = service._build_debt_dict(debt)
    assert debt_dict["debt_type"] == "owe"
    assert debt_dict["paid_amount"] == Decimal("0")


@pytest.mark.asyncio
async def test_debt_record_payment(test_db: AsyncSession) -> None:
    """record_payment should decrease remaining_amount by the payment amount."""
    await _make_user(test_db)

    service = DebtService(test_db)
    data = DebtCreateRequest(
        name="Vay mua laptop",
        creditor="Ngân hàng ABC",
        amount=Decimal("20000000"),
        start_date="2026-01-01",
        debt_type="owe",
    )
    debt = await service.create_debt(TEST_USER, data)

    updated = await service.record_payment(debt.id, 5_000_000, TEST_USER)

    assert updated is not None
    assert updated.remaining_amount == Decimal("15000000")

    debt_dict = service._build_debt_dict(updated)
    assert debt_dict["paid_amount"] == Decimal("5000000")
    assert debt_dict["remaining_amount"] == Decimal("15000000")


# ===========================================================================
# SubscriptionService tests
# ===========================================================================


@pytest.mark.asyncio
async def test_create_subscription(test_db: AsyncSession) -> None:
    """SubscriptionService.create_subscription should persist a new subscription."""
    await _make_user(test_db)

    service = SubscriptionService(test_db)
    data = SubscriptionCreateRequest(
        name="Netflix",
        amount=Decimal("180000"),
        start_date="2026-01-01",
        next_billing_date="2026-04-01",
    )
    sub = await service.create_subscription(TEST_USER, data)

    assert sub.id is not None
    assert sub.name == "Netflix"
    assert sub.amount == Decimal("180000")
    assert sub.is_active is True


@pytest.mark.asyncio
async def test_subscription_summary_structure(test_db: AsyncSession) -> None:
    """get_subscription_summary should return a dict with the expected keys."""
    await _make_user(test_db)

    service = SubscriptionService(test_db)
    summary = await service.get_subscription_summary(TEST_USER)

    expected_keys = {
        "active_count",
        "monthly_cost",
        "yearly_cost",
        "upcoming_renewals_count",
    }
    assert expected_keys.issubset(summary.keys())


@pytest.mark.asyncio
async def test_upcoming_renewals_empty(test_db: AsyncSession) -> None:
    """get_upcoming_renewals returns empty list when no renewals fall in range."""
    await _make_user(test_db)

    service = SubscriptionService(test_db)
    # Subscription renewing far in the future – outside 7-day window
    data = SubscriptionCreateRequest(
        name="Spotify",
        amount=Decimal("59000"),
        start_date="2026-01-01",
        next_billing_date="2027-01-01",  # far future
    )
    await service.create_subscription(TEST_USER, data)

    upcoming = await service.get_upcoming_renewals(TEST_USER, days=7)
    assert upcoming == []
