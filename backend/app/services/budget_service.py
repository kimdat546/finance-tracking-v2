"""Budget service - business logic for budget management and spending tracking."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.planning import Budget, BudgetPeriod
from app.models.transaction import Category, Transaction, TransactionType
from app.schemas.planning import BudgetCreateRequest, BudgetUpdateRequest


class BudgetService:
    """Service for managing budgets and calculating spending."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the service with a database session.

        Args:
            session: The async SQLAlchemy session to use for all queries.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_spending_fields(self, budget: Budget, spent: Decimal) -> dict:
        """Compute spending-related fields for a budget.

        Args:
            budget: The budget model instance.
            spent: The actual amount spent in the current period.

        Returns:
            Dict with spent_amount, remaining, percentage_used keys.
        """
        limit = Decimal(str(budget.limit_amount))
        remaining = max(limit - spent, Decimal("0"))
        percentage_used = float(spent / limit * 100) if limit > 0 else 0.0
        return {
            "spent_amount": spent,
            "remaining": remaining,
            "percentage_used": round(percentage_used, 2),
        }

    async def _get_spending_for_budget(self, budget: Budget) -> Decimal:
        """Sum expense transactions for a budget's category in its date range.

        Args:
            budget: The budget to calculate spending for.

        Returns:
            Total amount spent as Decimal.
        """
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == budget.user_id,
            Transaction.category_id == budget.category_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.transaction_date >= budget.start_date,
        )
        if budget.end_date:
            query = query.where(Transaction.transaction_date <= budget.end_date)

        result = await self.session.execute(query)
        value = result.scalar_one_or_none()
        return Decimal(str(value)) if value is not None else Decimal("0")

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def create_budget(self, user_id: str, data: BudgetCreateRequest) -> Budget:
        """Create a new budget for the given user.

        Args:
            user_id: The authenticated user's ID.
            data: Validated budget creation data.

        Returns:
            The newly created Budget instance.
        """
        budget = Budget(
            user_id=user_id,
            category_id=data.category_id,
            name=data.name,
            limit_amount=data.amount,
            period=data.period,
            start_date=data.start_date,
            end_date=data.end_date,
            currency=data.currency,
            alert_threshold=data.alert_threshold,
        )
        self.session.add(budget)
        await self.session.commit()
        await self.session.refresh(budget)
        return budget

    async def get_budgets(self, user_id: str, active_only: bool = True) -> list[Budget]:
        """Retrieve all budgets for a user, optionally filtering inactive ones.

        Args:
            user_id: The authenticated user's ID.
            active_only: When True, only return active budgets.

        Returns:
            List of Budget instances.
        """
        query = (
            select(Budget)
            .where(Budget.user_id == user_id)
            .options(selectinload(Budget.category))
        )
        if active_only:
            query = query.where(Budget.is_active.is_(True))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_budget_with_spending(
        self, budget_id: str, user_id: str
    ) -> dict | None:
        """Fetch a budget enriched with actual spending data for the current period.

        Args:
            budget_id: The budget's UUID.
            user_id: The authenticated user's ID.

        Returns:
            Dict combining budget attributes with spent_amount, remaining, and
            percentage_used, or None if the budget is not found.
        """
        result = await self.session.execute(
            select(Budget)
            .where(Budget.id == budget_id, Budget.user_id == user_id)
            .options(selectinload(Budget.category))
        )
        budget = result.scalar_one_or_none()
        if budget is None:
            return None

        spent = await self._get_spending_for_budget(budget)
        spending = self._compute_spending_fields(budget, spent)

        return {
            "id": budget.id,
            "category_id": budget.category_id,
            "category_name": budget.category.name if budget.category else None,
            "name": budget.name,
            "amount": budget.limit_amount,
            "period": budget.period,
            "currency": budget.currency,
            "start_date": budget.start_date,
            "end_date": budget.end_date,
            "is_active": budget.is_active,
            "alert_threshold": budget.alert_threshold,
            **spending,
        }

    async def update_budget(
        self, budget_id: str, user_id: str, data: BudgetUpdateRequest
    ) -> Budget | None:
        """Update an existing budget.

        Args:
            budget_id: The budget's UUID.
            user_id: The authenticated user's ID.
            data: Fields to update (only non-None values are applied).

        Returns:
            Updated Budget instance, or None if not found.
        """
        result = await self.session.execute(
            select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
        )
        budget = result.scalar_one_or_none()
        if budget is None:
            return None

        if data.category_id is not None:
            budget.category_id = data.category_id
        if data.name is not None:
            budget.name = data.name
        if data.amount is not None:
            budget.limit_amount = data.amount
        if data.period is not None:
            budget.period = data.period
        if data.start_date is not None:
            budget.start_date = data.start_date
        if data.end_date is not None:
            budget.end_date = data.end_date
        if data.currency is not None:
            budget.currency = data.currency
        if data.alert_threshold is not None:
            budget.alert_threshold = data.alert_threshold
        if data.is_active is not None:
            budget.is_active = data.is_active

        await self.session.commit()
        await self.session.refresh(budget)
        return budget

    async def delete_budget(self, budget_id: str, user_id: str) -> bool:
        """Soft-delete (deactivate) a budget.

        Args:
            budget_id: The budget's UUID.
            user_id: The authenticated user's ID.

        Returns:
            True if the budget was found and deactivated, False otherwise.
        """
        result = await self.session.execute(
            select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
        )
        budget = result.scalar_one_or_none()
        if budget is None:
            return False
        await self.session.delete(budget)
        await self.session.commit()
        return True

    async def get_budget_alerts(self, user_id: str) -> list[dict]:
        """Return alert messages for budgets where spending exceeds the alert threshold.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            List of dicts with budget_id, name, percentage_used, and message.
        """
        budgets = await self.get_budgets(user_id, active_only=True)
        alerts: list[dict] = []
        for budget in budgets:
            spent = await self._get_spending_for_budget(budget)
            spending = self._compute_spending_fields(budget, spent)
            if spending["percentage_used"] >= budget.alert_threshold:
                msg = (
                    f"Ngân sách '{budget.name}' đã dùng "
                    f"{spending['percentage_used']:.1f}% "
                    f"(hạn mức: {budget.alert_threshold}%)"
                )
                alerts.append(
                    {
                        "budget_id": budget.id,
                        "name": budget.name,
                        "percentage_used": spending["percentage_used"],
                        "spent_amount": float(spending["spent_amount"]),
                        "limit_amount": float(budget.limit_amount),
                        "alert_threshold": budget.alert_threshold,
                        "message": msg,
                    }
                )
        return alerts

    async def get_budget_summary(self, user_id: str) -> dict:
        """Return an aggregate summary of budgets and spending for a user.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            Dict with total_budgeted, total_spent, on_track_count, over_limit_count.
        """
        budgets = await self.get_budgets(user_id, active_only=True)
        total_budgeted = Decimal("0")
        total_spent = Decimal("0")
        on_track = 0
        over_limit = 0
        warning = 0

        for budget in budgets:
            spent = await self._get_spending_for_budget(budget)
            limit = Decimal(str(budget.limit_amount))
            total_budgeted += limit
            total_spent += spent
            pct = float(spent / limit * 100) if limit > 0 else 0.0
            if pct > 100:
                over_limit += 1
            elif pct >= 80:
                warning += 1
            else:
                on_track += 1

        return {
            "total_budgeted": float(total_budgeted),
            "total_spent": float(total_spent),
            "total_remaining": float(max(total_budgeted - total_spent, Decimal("0"))),
            "budget_count": len(budgets),
            "on_track_count": on_track,
            "warning_count": warning,
            "over_limit_count": over_limit,
        }
