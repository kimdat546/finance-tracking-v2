"""Monthly report service - detailed per-month financial analytics."""

import calendar
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.planning import Budget
from app.models.transaction import Category, Transaction, TransactionType


class MonthlyReportService:
    """Generates detailed monthly financial reports."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the service with a database session.

        Args:
            session: The async SQLAlchemy session to use for all queries.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _month_range(self, year: int, month: int) -> tuple[str, str]:
        """Return (start_date, end_date) strings for a given year/month.

        Args:
            year: Four-digit year.
            month: Month number (1-12).

        Returns:
            Tuple of ISO date strings (start, end).
        """
        _, last_day = calendar.monthrange(year, month)
        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-{last_day:02d}"
        return start, end

    def _prev_month(self, year: int, month: int) -> tuple[int, int]:
        """Return (year, month) for the month before the given one.

        Args:
            year: Four-digit year.
            month: Month number (1-12).

        Returns:
            Tuple of (year, month) for the previous month.
        """
        if month == 1:
            return year - 1, 12
        return year, month - 1

    async def _sum_by_type(
        self, user_id: str, tx_type: TransactionType, start: str, end: str
    ) -> Decimal:
        """Sum transaction amounts for a specific type and date range.

        Args:
            user_id: The user's ID.
            tx_type: The transaction type to filter.
            start: Start date string.
            end: End date string.

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
        val = result.scalar_one_or_none()
        return Decimal(str(val)) if val is not None else Decimal("0")

    async def _category_breakdown(
        self, user_id: str, tx_type: TransactionType, start: str, end: str
    ) -> list[dict]:
        """Get spending breakdown by category.

        Args:
            user_id: The user's ID.
            tx_type: The transaction type to aggregate.
            start: Start date string.
            end: End date string.

        Returns:
            List of dicts with category_id, name, amount, count.
        """
        result = await self.session.execute(
            select(
                Category.id,
                Category.name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("cnt"),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == tx_type,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
                Transaction.category_id.isnot(None),
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        )
        rows = result.all()
        return [
            {
                "category_id": row.id,
                "name": row.name,
                "amount": float(row.total),
                "count": row.cnt,
            }
            for row in rows
        ]

    async def _spending_by_day(self, user_id: str, start: str, end: str) -> list[dict]:
        """Get daily expense totals.

        Args:
            user_id: The user's ID.
            start: Start date string.
            end: End date string.

        Returns:
            List of dicts with date and amount.
        """
        result = await self.session.execute(
            select(
                Transaction.transaction_date.label("day"),
                func.sum(Transaction.amount).label("total"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
            )
            .group_by(Transaction.transaction_date)
            .order_by(Transaction.transaction_date)
        )
        rows = result.all()
        return [{"date": row.day, "amount": float(row.total)} for row in rows]

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_monthly_report(self, user_id: str, year: int, month: int) -> dict:
        """Full monthly financial report.

        Args:
            user_id: The authenticated user's ID.
            year: Report year.
            month: Report month (1-12).

        Returns:
            Dict with period, income, expenses, net, savings_rate,
            vs_previous_month, top_merchants, budget_performance,
            transaction_count.
        """
        start, end = self._month_range(year, month)
        p_year, p_month = self._prev_month(year, month)
        p_start, p_end = self._month_range(p_year, p_month)

        income_total = await self._sum_by_type(user_id, TransactionType.INCOME, start, end)
        expense_total = await self._sum_by_type(user_id, TransactionType.EXPENSE, start, end)
        net = income_total - expense_total
        savings_rate = float(net / income_total * 100) if income_total > 0 else 0.0

        income_by_cat = await self._category_breakdown(
            user_id, TransactionType.INCOME, start, end
        )
        expense_by_cat = await self._category_breakdown(
            user_id, TransactionType.EXPENSE, start, end
        )
        expense_by_day = await self._spending_by_day(user_id, start, end)

        # Previous month totals for comparison
        prev_income = await self._sum_by_type(user_id, TransactionType.INCOME, p_start, p_end)
        prev_expense = await self._sum_by_type(user_id, TransactionType.EXPENSE, p_start, p_end)

        def pct_change(current: Decimal, previous: Decimal) -> float:
            if previous == 0:
                return 0.0
            return float((current - previous) / previous * 100)

        # Top merchants
        merchants_result = await self.session.execute(
            select(
                Transaction.merchant,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("cnt"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
                Transaction.merchant.isnot(None),
            )
            .group_by(Transaction.merchant)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(10)
        )
        top_merchants = [
            {"name": r.merchant, "amount": float(r.total), "count": r.cnt}
            for r in merchants_result.all()
        ]

        # Budget performance
        budget_performance = await self._budget_performance(user_id, start, end)

        # Transaction count
        count_result = await self.session.execute(
            select(func.count(Transaction.id)).where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
            )
        )
        transaction_count = count_result.scalar_one() or 0

        return {
            "period": f"{year}-{month:02d}",
            "income": {
                "total": float(income_total),
                "by_category": income_by_cat,
            },
            "expenses": {
                "total": float(expense_total),
                "by_category": expense_by_cat,
                "by_day": expense_by_day,
            },
            "net": float(net),
            "savings_rate": round(savings_rate, 2),
            "vs_previous_month": {
                "income_change": round(pct_change(income_total, prev_income), 2),
                "expense_change": round(pct_change(expense_total, prev_expense), 2),
            },
            "top_merchants": top_merchants,
            "budget_performance": budget_performance,
            "transaction_count": transaction_count,
        }

    async def _budget_performance(
        self, user_id: str, start: str, end: str
    ) -> list[dict]:
        """Compare budget limits to actual spending for the period.

        Args:
            user_id: The user's ID.
            start: Period start date.
            end: Period end date.

        Returns:
            List of dicts with category, budgeted, actual, variance.
        """
        budgets_result = await self.session.execute(
            select(Budget)
            .where(Budget.user_id == user_id, Budget.is_active.is_(True))
            .options(selectinload(Budget.category))
        )
        budgets = budgets_result.scalars().all()
        performance: list[dict] = []
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
            actual = float(Decimal(str(spent_val)) if spent_val is not None else Decimal("0"))
            budgeted = float(budget.limit_amount)
            performance.append(
                {
                    "category": budget.category.name if budget.category else budget.name,
                    "budgeted": budgeted,
                    "actual": actual,
                    "variance": round(budgeted - actual, 2),
                }
            )
        return performance

    async def get_monthly_comparison(self, user_id: str, months: int = 6) -> list[dict]:
        """Compare the last N months: income, expense, and net per month.

        Args:
            user_id: The authenticated user's ID.
            months: Number of months to include.

        Returns:
            List of dicts with month, income, expense, net (ordered oldest first).
        """
        now = datetime.now(timezone.utc)
        results: list[dict] = []
        year = now.year
        month = now.month

        for _ in range(months):
            start, end = self._month_range(year, month)
            income = await self._sum_by_type(user_id, TransactionType.INCOME, start, end)
            expense = await self._sum_by_type(user_id, TransactionType.EXPENSE, start, end)
            net = income - expense
            results.append(
                {
                    "month": f"{year}-{month:02d}",
                    "income": float(income),
                    "expense": float(expense),
                    "net": float(net),
                }
            )
            year, month = self._prev_month(year, month)

        results.reverse()
        return results

    async def get_day_of_week_pattern(self, user_id: str, months: int = 3) -> dict:
        """Spending by day of week (Mon=0 to Sun=6) over the last N months.

        Args:
            user_id: The authenticated user's ID.
            months: Number of months to look back.

        Returns:
            Dict with labels (day names) and amounts per day of week.
        """
        now = datetime.now(timezone.utc)
        if now.month > months:
            start_month = now.month - months
            start_year = now.year
        else:
            start_month = now.month - months + 12
            start_year = now.year - 1
        start = f"{start_year}-{start_month:02d}-01"
        end = now.strftime("%Y-%m-%d")

        result = await self.session.execute(
            select(
                Transaction.transaction_date,
                func.sum(Transaction.amount).label("total"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
            )
            .group_by(Transaction.transaction_date)
        )
        rows = result.all()

        day_totals: dict[int, float] = {i: 0.0 for i in range(7)}
        day_counts: dict[int, int] = {i: 0 for i in range(7)}
        for row in rows:
            try:
                date_obj = datetime.strptime(row.transaction_date[:10], "%Y-%m-%d")
                dow = date_obj.weekday()  # 0=Monday
                day_totals[dow] += float(row.total)
                day_counts[dow] += 1
            except (ValueError, TypeError):
                continue

        labels = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        return {
            "labels": labels,
            "amounts": [round(day_totals[i], 2) for i in range(7)],
            "averages": [
                round(day_totals[i] / day_counts[i], 2) if day_counts[i] > 0 else 0.0
                for i in range(7)
            ],
        }

    async def get_time_of_day_pattern(self, user_id: str, months: int = 3) -> dict:
        """Spending aggregated by hour of day over the last N months.

        Since transaction_date is stored as a date string without time,
        this method groups by booking_date or falls back to even distribution.

        Args:
            user_id: The authenticated user's ID.
            months: Number of months to look back.

        Returns:
            Dict with hours (0-23) and amounts arrays.
        """
        now = datetime.now(timezone.utc)
        if now.month > months:
            start_month = now.month - months
            start_year = now.year
        else:
            start_month = now.month - months + 12
            start_year = now.year - 1
        start = f"{start_year}-{start_month:02d}-01"
        end = now.strftime("%Y-%m-%d")

        result = await self.session.execute(
            select(Transaction.created_at, Transaction.amount)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
            )
        )
        rows = result.all()

        hour_totals: dict[int, float] = {h: 0.0 for h in range(24)}
        for row in rows:
            if row.created_at:
                hour = row.created_at.hour
                hour_totals[hour] += float(row.amount)

        return {
            "hours": list(range(24)),
            "amounts": [round(hour_totals[h], 2) for h in range(24)],
        }
