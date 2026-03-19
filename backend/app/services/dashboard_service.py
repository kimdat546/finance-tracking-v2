"""Dashboard service - aggregated summary data for the main dashboard."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.planning import Budget, Debt, Subscription
from app.models.social import SplitBill
from app.models.transaction import Account, Category, Transaction, TransactionType


class DashboardService:
    """Aggregated data for the main dashboard."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the service with a database session.

        Args:
            session: The async SQLAlchemy session to use for all queries.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _current_month_range(self) -> tuple[str, str]:
        """Return (start_date, end_date) strings for the current month."""
        now = datetime.now(timezone.utc)
        start = now.replace(day=1).strftime("%Y-%m-%d")
        # Last day of month: go to next month day 1 then subtract one day
        if now.month == 12:
            end = now.replace(year=now.year + 1, month=1, day=1)
        else:
            end = now.replace(month=now.month + 1, day=1)
        end_str = (end.replace(day=1) if end.day != 1 else end).strftime("%Y-%m-%d")
        # Simply use the month's last possible date via string comparison
        end_str = f"{now.year}-{now.month:02d}-31"
        return start, end_str

    def _previous_month_range(self) -> tuple[str, str]:
        """Return (start_date, end_date) strings for the previous month."""
        now = datetime.now(timezone.utc)
        if now.month == 1:
            prev_year = now.year - 1
            prev_month = 12
        else:
            prev_year = now.year
            prev_month = now.month - 1
        start = f"{prev_year}-{prev_month:02d}-01"
        end = f"{prev_year}-{prev_month:02d}-31"
        return start, end

    async def _sum_transactions(
        self, user_id: str, tx_type: TransactionType, start: str, end: str
    ) -> Decimal:
        """Sum transaction amounts for a user, type and date range.

        Args:
            user_id: The user's ID.
            tx_type: TransactionType.INCOME or TransactionType.EXPENSE.
            start: Start date string (YYYY-MM-DD).
            end: End date string (YYYY-MM-DD).

        Returns:
            Total as Decimal.
        """
        result = await self.session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user_id,
                Transaction.type == tx_type,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
            )
        )
        value = result.scalar_one_or_none()
        return Decimal(str(value)) if value is not None else Decimal("0")

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_summary(self, user_id: str) -> dict:
        """Dashboard summary for current month.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            Dict containing total_income, total_expense, net_cashflow,
            transaction_count, top_categories, recent_transactions,
            budget_alerts, and savings_rate.
        """
        start, end = self._current_month_range()

        # Income and expense totals
        total_income = await self._sum_transactions(user_id, TransactionType.INCOME, start, end)
        total_expense = await self._sum_transactions(user_id, TransactionType.EXPENSE, start, end)
        net_cashflow = total_income - total_expense
        savings_rate = float(net_cashflow / total_income * 100) if total_income > 0 else 0.0

        # Transaction count
        count_result = await self.session.execute(
            select(func.count(Transaction.id)).where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
            )
        )
        transaction_count = count_result.scalar_one() or 0

        # Top categories by expense
        top_categories = await self._get_top_categories(user_id, start, end)

        # Recent 5 transactions
        recent_result = await self.session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .options(selectinload(Transaction.category))
            .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .limit(5)
        )
        recent_txns = recent_result.scalars().all()
        recent_transactions = [
            {
                "id": t.id,
                "description": t.description,
                "amount": float(t.amount),
                "type": t.type.value,
                "transaction_date": t.transaction_date,
                "merchant": t.merchant,
                "category": t.category.name if t.category else None,
            }
            for t in recent_txns
        ]

        # Budget alerts (budgets > 80% used)
        budget_alerts = await self._get_budget_alerts(user_id, start, end)

        return {
            "total_income": float(total_income),
            "total_expense": float(total_expense),
            "net_cashflow": float(net_cashflow),
            "transaction_count": transaction_count,
            "top_categories": top_categories,
            "recent_transactions": recent_transactions,
            "budget_alerts": budget_alerts,
            "savings_rate": round(savings_rate, 2),
        }

    async def _get_top_categories(
        self, user_id: str, start: str, end: str, limit: int = 5
    ) -> list[dict]:
        """Get top spending categories for the given period.

        Args:
            user_id: The user's ID.
            start: Start date string.
            end: End date string.
            limit: Number of top categories to return.

        Returns:
            List of dicts with name, amount, count.
        """
        result = await self.session.execute(
            select(
                Category.name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("cnt"),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
                Transaction.category_id.isnot(None),
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            {"name": row.name, "amount": float(row.total), "count": row.cnt} for row in rows
        ]

    async def _get_budget_alerts(self, user_id: str, start: str, end: str) -> list[dict]:
        """Get budget alerts for budgets exceeding 80% usage.

        Args:
            user_id: The user's ID.
            start: Period start date string.
            end: Period end date string.

        Returns:
            List of alert dicts for over-threshold budgets.
        """
        budgets_result = await self.session.execute(
            select(Budget)
            .where(Budget.user_id == user_id, Budget.is_active.is_(True))
            .options(selectinload(Budget.category))
        )
        budgets = budgets_result.scalars().all()
        alerts: list[dict] = []
        for budget in budgets:
            spent_result = await self.session.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == user_id,
                    Transaction.category_id == budget.category_id,
                    Transaction.type == TransactionType.EXPENSE,
                    Transaction.transaction_date >= start,
                    Transaction.transaction_date <= end,
                )
            )
            spent_val = spent_result.scalar_one_or_none()
            spent = Decimal(str(spent_val)) if spent_val is not None else Decimal("0")
            limit = Decimal(str(budget.limit_amount))
            pct = float(spent / limit * 100) if limit > 0 else 0.0
            if pct >= 80:
                alerts.append(
                    {
                        "budget_id": budget.id,
                        "name": budget.name,
                        "category": budget.category.name if budget.category else None,
                        "limit_amount": float(limit),
                        "spent_amount": float(spent),
                        "percentage_used": round(pct, 2),
                    }
                )
        return alerts

    async def get_account_balances(self, user_id: str) -> list[dict]:
        """Return all accounts with current balance.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            List of dicts with id, name, account_type, balance, currency.
        """
        result = await self.session.execute(
            select(Account).where(Account.user_id == user_id, Account.is_active.is_(True))
        )
        accounts = result.scalars().all()
        return [
            {
                "id": a.id,
                "name": a.name,
                "account_type": a.account_type,
                "balance": float(a.balance),
                "currency": a.currency,
                "institution": a.institution,
            }
            for a in accounts
        ]

    async def get_net_worth(self, user_id: str) -> dict:
        """Net worth: sum of all account balances minus outstanding debts.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            Dict with assets, liabilities, net_worth.
        """
        # Assets: sum of all active account balances
        assets_result = await self.session.execute(
            select(func.coalesce(func.sum(Account.balance), 0)).where(
                Account.user_id == user_id, Account.is_active.is_(True)
            )
        )
        assets_val = assets_result.scalar_one_or_none()
        assets = Decimal(str(assets_val)) if assets_val is not None else Decimal("0")

        # Liabilities: sum of remaining debt amounts
        liabilities_result = await self.session.execute(
            select(func.coalesce(func.sum(Debt.remaining_amount), 0)).where(
                Debt.user_id == user_id
            )
        )
        liabilities_val = liabilities_result.scalar_one_or_none()
        liabilities = (
            Decimal(str(liabilities_val)) if liabilities_val is not None else Decimal("0")
        )

        net_worth = assets - liabilities
        return {
            "assets": float(assets),
            "liabilities": float(liabilities),
            "net_worth": float(net_worth),
        }

    async def get_quick_stats(self, user_id: str) -> dict:
        """Quick stats for header cards.

        Returns this month's spend vs last month (% change), savings goal progress,
        upcoming subscription renewals count, and unresolved split bills count.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            Dict with this_month_spend, last_month_spend, spend_change_pct,
            savings_current, savings_target, savings_progress_pct,
            upcoming_renewals_count, unresolved_split_bills_count.
        """
        curr_start, curr_end = self._current_month_range()
        prev_start, prev_end = self._previous_month_range()

        this_month_spend = await self._sum_transactions(
            user_id, TransactionType.EXPENSE, curr_start, curr_end
        )
        last_month_spend = await self._sum_transactions(
            user_id, TransactionType.EXPENSE, prev_start, prev_end
        )

        if last_month_spend > 0:
            spend_change_pct = float(
                (this_month_spend - last_month_spend) / last_month_spend * 100
            )
        else:
            spend_change_pct = 0.0

        # Savings goal progress (sum of active goals)
        goals_result = await self.session.execute(
            select(
                func.coalesce(func.sum(
                    # SQLAlchemy workaround: import Goal inline
                    __import__("app.models.planning", fromlist=["Goal"]).Goal.current_amount
                ), 0).label("current"),
                func.coalesce(func.sum(
                    __import__("app.models.planning", fromlist=["Goal"]).Goal.target_amount
                ), 0).label("target"),
            ).where(
                __import__("app.models.planning", fromlist=["Goal"]).Goal.user_id == user_id,
                __import__("app.models.planning", fromlist=["Goal"]).Goal.status == "active",
            )
        )
        goals_row = goals_result.one_or_none()
        savings_current = float(goals_row.current) if goals_row else 0.0
        savings_target = float(goals_row.target) if goals_row else 0.0
        savings_progress_pct = (
            savings_current / savings_target * 100 if savings_target > 0 else 0.0
        )

        # Upcoming subscription renewals in the next 30 days
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        future_str = now.replace(day=min(now.day + 30, 28)).strftime("%Y-%m-%d")
        renewals_result = await self.session.execute(
            select(func.count(Subscription.id)).where(
                Subscription.user_id == user_id,
                Subscription.is_active.is_(True),
                Subscription.next_billing_date >= today_str,
                Subscription.next_billing_date <= future_str,
            )
        )
        upcoming_renewals_count = renewals_result.scalar_one() or 0

        # Unresolved split bills
        splits_result = await self.session.execute(
            select(func.count(SplitBill.id)).where(
                SplitBill.user_id == user_id,
                SplitBill.is_settled.is_(False),
            )
        )
        unresolved_split_bills_count = splits_result.scalar_one() or 0

        return {
            "this_month_spend": float(this_month_spend),
            "last_month_spend": float(last_month_spend),
            "spend_change_pct": round(spend_change_pct, 2),
            "savings_current": savings_current,
            "savings_target": savings_target,
            "savings_progress_pct": round(savings_progress_pct, 2),
            "upcoming_renewals_count": upcoming_renewals_count,
            "unresolved_split_bills_count": unresolved_split_bills_count,
        }
