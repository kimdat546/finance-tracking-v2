"""Planning API endpoints: budgets, goals, debts, subscriptions."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.planning import Subscription
from app.schemas.planning import (
    BudgetCreateRequest,
    BudgetListResponse,
    BudgetSchema,
    BudgetUpdateRequest,
    DebtCreateRequest,
    DebtListResponse,
    DebtPaymentRequest,
    DebtSchema,
    DebtUpdateRequest,
    GoalCreateRequest,
    GoalListResponse,
    GoalSchema,
    GoalUpdateRequest,
    SubscriptionCreateRequest,
    SubscriptionDetectionResult,
    SubscriptionListResponse,
    SubscriptionSchema,
    SubscriptionUpdateRequest,
)
from app.services.budget_service import BudgetService
from app.services.debt_service import DebtService
from app.services.goal_service import GoalService
from app.services.subscription_service import SubscriptionService, _compute_annual_cost

# Hard-coded user ID per project conventions
_USER_ID = "00000000-0000-0000-0000-000000000001"

router = APIRouter(prefix="/planning", tags=["planning"])


# ===========================================================================
# Budget endpoints
# ===========================================================================


@router.get("/budgets/alerts", response_model=list[dict])
async def get_budget_alerts(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return budgets where spending has exceeded the alert threshold.

    Returns a list of alert messages for budgets where spending >= alert_threshold%.
    """
    service = BudgetService(db)
    return await service.get_budget_alerts(_USER_ID)


@router.get("/budgets/summary", response_model=dict)
async def get_budget_summary(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return aggregate budget summary for the current user."""
    service = BudgetService(db)
    return await service.get_budget_summary(_USER_ID)


@router.get("/budgets", response_model=BudgetListResponse)
async def list_budgets(
    active_only: bool = Query(True, description="Only return active budgets"),
    db: AsyncSession = Depends(get_db),
) -> BudgetListResponse:
    """List all budgets with spending data for the current user."""
    service = BudgetService(db)
    budgets = await service.get_budgets(_USER_ID, active_only=active_only)

    items: list[BudgetSchema] = []
    for budget in budgets:
        data = await service.get_budget_with_spending(budget.id, _USER_ID)
        if data:
            items.append(BudgetSchema(**data))

    return BudgetListResponse(items=items, total=len(items))


@router.post("/budgets", response_model=BudgetSchema, status_code=201)
async def create_budget(
    body: BudgetCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> BudgetSchema:
    """Create a new budget for the current user."""
    service = BudgetService(db)
    budget = await service.create_budget(_USER_ID, body)
    data = await service.get_budget_with_spending(budget.id, _USER_ID)
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve created budget")
    return BudgetSchema(**data)


@router.get("/budgets/{budget_id}", response_model=BudgetSchema)
async def get_budget(
    budget_id: str,
    db: AsyncSession = Depends(get_db),
) -> BudgetSchema:
    """Get a single budget with spending data."""
    service = BudgetService(db)
    data = await service.get_budget_with_spending(budget_id, _USER_ID)
    if data is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    return BudgetSchema(**data)


@router.put("/budgets/{budget_id}", response_model=BudgetSchema)
async def update_budget(
    budget_id: str,
    body: BudgetUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> BudgetSchema:
    """Update an existing budget."""
    service = BudgetService(db)
    budget = await service.update_budget(budget_id, _USER_ID, body)
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found")
    data = await service.get_budget_with_spending(budget.id, _USER_ID)
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve updated budget")
    return BudgetSchema(**data)


@router.delete("/budgets/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a budget."""
    service = BudgetService(db)
    deleted = await service.delete_budget(budget_id, _USER_ID)
    if not deleted:
        raise HTTPException(status_code=404, detail="Budget not found")


# ===========================================================================
# Goal endpoints
# ===========================================================================


@router.get("/goals/summary", response_model=dict)
async def get_goals_summary(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return aggregate statistics for all goals."""
    service = GoalService(db)
    return await service.get_goals_summary(_USER_ID)


@router.get("/goals", response_model=GoalListResponse)
async def list_goals(
    active_only: bool = Query(True, description="Only return active goals"),
    db: AsyncSession = Depends(get_db),
) -> GoalListResponse:
    """List all goals for the current user."""
    service = GoalService(db)
    goals = await service.get_goals(_USER_ID, active_only=active_only)

    items: list[GoalSchema] = []
    for goal in goals:
        goal_dict = service._to_schema_dict(goal)
        items.append(GoalSchema(**goal_dict))

    return GoalListResponse(items=items, total=len(items))


@router.post("/goals", response_model=GoalSchema, status_code=201)
async def create_goal(
    body: GoalCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> GoalSchema:
    """Create a new financial goal."""
    service = GoalService(db)
    goal = await service.create_goal(_USER_ID, body)
    return GoalSchema(**service._to_schema_dict(goal))


@router.get("/goals/{goal_id}", response_model=GoalSchema)
async def get_goal(
    goal_id: str,
    db: AsyncSession = Depends(get_db),
) -> GoalSchema:
    """Get a single goal by ID."""
    service = GoalService(db)
    goal = await service.get_goal(goal_id, _USER_ID)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return GoalSchema(**service._to_schema_dict(goal))


@router.put("/goals/{goal_id}", response_model=GoalSchema)
async def update_goal(
    goal_id: str,
    body: GoalUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> GoalSchema:
    """Update an existing goal."""
    service = GoalService(db)
    goal = await service.update_goal(goal_id, _USER_ID, body)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return GoalSchema(**service._to_schema_dict(goal))


@router.delete("/goals/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a goal."""
    service = GoalService(db)
    deleted = await service.delete_goal(goal_id, _USER_ID)
    if not deleted:
        raise HTTPException(status_code=404, detail="Goal not found")


@router.post("/goals/{goal_id}/contribute", response_model=GoalSchema)
async def add_goal_contribution(
    goal_id: str,
    amount: float = Query(..., gt=0, description="Contribution amount"),
    db: AsyncSession = Depends(get_db),
) -> GoalSchema:
    """Add a monetary contribution to a goal's current amount."""
    service = GoalService(db)
    try:
        goal = await service.add_contribution(goal_id, amount, _USER_ID)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return GoalSchema(**service._to_schema_dict(goal))


# ===========================================================================
# Debt endpoints
# ===========================================================================


@router.get("/debts/summary", response_model=dict)
async def get_debt_summary(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return aggregate debt summary (total owe, total owed, net position)."""
    service = DebtService(db)
    return await service.get_debt_summary(_USER_ID)


@router.get("/debts", response_model=DebtListResponse)
async def list_debts(
    debt_type: str | None = Query(None, description="Filter by type: 'owe' or 'owed'"),
    db: AsyncSession = Depends(get_db),
) -> DebtListResponse:
    """List all debts, optionally filtered by type."""
    service = DebtService(db)
    debts = await service.get_debts(_USER_ID, debt_type=debt_type)

    items: list[DebtSchema] = []
    for debt in debts:
        items.append(DebtSchema(**service._build_debt_dict(debt)))

    return DebtListResponse(items=items, total=len(items))


@router.post("/debts", response_model=DebtSchema, status_code=201)
async def create_debt(
    body: DebtCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> DebtSchema:
    """Create a new debt record."""
    service = DebtService(db)
    debt = await service.create_debt(_USER_ID, body)
    return DebtSchema(**service._build_debt_dict(debt))


@router.put("/debts/{debt_id}", response_model=DebtSchema)
async def update_debt(
    debt_id: str,
    body: DebtUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> DebtSchema:
    """Update an existing debt record."""
    service = DebtService(db)
    debt = await service.update_debt(debt_id, _USER_ID, body)
    if debt is None:
        raise HTTPException(status_code=404, detail="Debt not found")
    return DebtSchema(**service._build_debt_dict(debt))


@router.delete("/debts/{debt_id}", status_code=204)
async def delete_debt(
    debt_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a debt record."""
    service = DebtService(db)
    deleted = await service.delete_debt(debt_id, _USER_ID)
    if not deleted:
        raise HTTPException(status_code=404, detail="Debt not found")


@router.post("/debts/{debt_id}/payment", response_model=DebtSchema)
async def record_debt_payment(
    debt_id: str,
    body: DebtPaymentRequest,
    db: AsyncSession = Depends(get_db),
) -> DebtSchema:
    """Record a payment against a debt, reducing the remaining balance."""
    service = DebtService(db)
    try:
        debt = await service.record_payment(debt_id, float(body.amount), _USER_ID)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if debt is None:
        raise HTTPException(status_code=404, detail="Debt not found")
    return DebtSchema(**service._build_debt_dict(debt))


# ===========================================================================
# Subscription endpoints
# ===========================================================================


@router.get("/subscriptions/detect", response_model=list[SubscriptionDetectionResult])
async def detect_subscriptions(
    db: AsyncSession = Depends(get_db),
) -> list[SubscriptionDetectionResult]:
    """Detect recurring charges from transaction history."""
    service = SubscriptionService(db)
    return await service.detect_subscriptions(_USER_ID)


@router.get("/subscriptions/upcoming", response_model=SubscriptionListResponse)
async def get_upcoming_renewals(
    days: int = Query(7, ge=1, le=90, description="Days ahead to look for renewals"),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionListResponse:
    """List subscriptions renewing within the next N days."""
    service = SubscriptionService(db)
    subs = await service.get_upcoming_renewals(_USER_ID, days=days)
    items = [_sub_to_schema(sub) for sub in subs]
    return SubscriptionListResponse(items=items, total=len(items))


@router.get("/subscriptions/summary", response_model=dict)
async def get_subscription_summary(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return aggregate subscription cost statistics."""
    service = SubscriptionService(db)
    return await service.get_subscription_summary(_USER_ID)


@router.get("/subscriptions", response_model=SubscriptionListResponse)
async def list_subscriptions(
    active_only: bool = Query(True, description="Only return active subscriptions"),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionListResponse:
    """List all subscriptions for the current user."""
    service = SubscriptionService(db)
    subs = await service.get_subscriptions(_USER_ID, active_only=active_only)
    items = [_sub_to_schema(sub) for sub in subs]
    return SubscriptionListResponse(items=items, total=len(items))


@router.post("/subscriptions", response_model=SubscriptionSchema, status_code=201)
async def create_subscription(
    body: SubscriptionCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionSchema:
    """Create a new subscription."""
    service = SubscriptionService(db)
    sub = await service.create_subscription(_USER_ID, body)
    return _sub_to_schema(sub)


@router.put("/subscriptions/{sub_id}", response_model=SubscriptionSchema)
async def update_subscription(
    sub_id: str,
    body: SubscriptionUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionSchema:
    """Update an existing subscription."""
    service = SubscriptionService(db)
    sub = await service.update_subscription(sub_id, _USER_ID, body)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return _sub_to_schema(sub)


@router.delete("/subscriptions/{sub_id}", status_code=204)
async def cancel_subscription(
    sub_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Cancel (deactivate) a subscription."""
    service = SubscriptionService(db)
    cancelled = await service.cancel_subscription(sub_id, _USER_ID)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Subscription not found")


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _sub_to_schema(sub: Subscription) -> SubscriptionSchema:
    """Convert a Subscription ORM instance to SubscriptionSchema.

    Args:
        sub: The Subscription model instance.

    Returns:
        A fully populated SubscriptionSchema.
    """
    annual = _compute_annual_cost(Decimal(str(sub.amount)), sub.billing_period)
    return SubscriptionSchema(
        id=sub.id,
        name=sub.name,
        description=sub.description,
        amount=sub.amount,
        currency=sub.currency,
        billing_cycle=sub.billing_period,
        start_date=sub.start_date,
        next_billing_date=sub.next_billing_date,
        end_date=sub.end_date,
        annual_cost=annual,
        is_active=sub.is_active,
        is_auto_renew=sub.is_auto_renew,
        category_id=sub.category_id,
    )
