"""Category analytics service – spending breakdowns and trends by category."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Category, Transaction, TransactionType

logger = logging.getLogger(__name__)


class CategoryAnalyticsService:
    """Analytics service for spending by category."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise CategoryAnalyticsService.

        Args:
            session: Async SQLAlchemy database session.
        """
        self.session = session

    async def get_spending_by_category(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        transaction_type: str = "expense",
    ) -> list[dict]:
        """Get spending totals grouped by category.

        Args:
            user_id: The user's ID.
            start_date: Optional inclusive lower bound (UTC).
            end_date: Optional inclusive upper bound (UTC).
            transaction_type: One of "income", "expense", "transfer".

        Returns:
            List of dicts with keys:
            category_id, category_name, total, count, percentage.
            Sorted by total descending.
        """
        tx_type = TransactionType(transaction_type)

        conditions = [
            Transaction.user_id == user_id,
            Transaction.type == tx_type,
            Transaction.category_id.isnot(None),
        ]
        if start_date:
            conditions.append(Transaction.transaction_date >= start_date.date().isoformat())
        if end_date:
            conditions.append(Transaction.transaction_date <= end_date.date().isoformat())

        stmt = (
            select(
                Transaction.category_id,
                Category.name.label("category_name"),
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .where(and_(*conditions))
            .group_by(Transaction.category_id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        grand_total = sum(float(row.total) for row in rows)

        output: list[dict] = []
        for row in rows:
            total_val = float(row.total)
            percentage = (total_val / grand_total * 100) if grand_total else 0.0
            output.append(
                {
                    "category_id": row.category_id,
                    "category_name": row.category_name,
                    "total": total_val,
                    "count": row.count,
                    "percentage": round(percentage, 2),
                }
            )
        return output

    async def get_category_trend(
        self,
        user_id: str,
        category_id: str,
        months: int = 6,
    ) -> list[dict]:
        """Return monthly spending trend for a specific category.

        Args:
            user_id: The user's ID.
            category_id: Target category ID.
            months: How many months of history to include.

        Returns:
            List of dicts with keys: month (YYYY-MM), total, count.
            Ordered chronologically.
        """
        # Compute earliest date boundary (first day of the month N months ago)
        now = datetime.now(timezone.utc)
        start_month = (now.replace(day=1) - timedelta(days=months * 31)).replace(day=1)
        start_str = start_month.date().isoformat()

        stmt = (
            select(
                func.substr(Transaction.transaction_date, 1, 7).label("month"),
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.category_id == category_id,
                Transaction.transaction_date >= start_str,
            )
            .group_by(func.substr(Transaction.transaction_date, 1, 7))
            .order_by(func.substr(Transaction.transaction_date, 1, 7).asc())
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "month": row.month,
                "total": float(row.total),
                "count": row.count,
            }
            for row in rows
        ]

    async def get_uncategorized_stats(self, user_id: str) -> dict:
        """Return stats about uncategorized transactions.

        Args:
            user_id: The user's ID.

        Returns:
            Dictionary with keys: count, total_amount, percentage.
        """
        total_count_result = await self.session.execute(
            select(func.count()).select_from(Transaction).where(
                Transaction.user_id == user_id,
            )
        )
        total_count: int = total_count_result.scalar_one()

        uncategorized_result = await self.session.execute(
            select(
                func.count(Transaction.id).label("count"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            ).where(
                Transaction.user_id == user_id,
                Transaction.category_id.is_(None),
            )
        )
        row = uncategorized_result.one()
        count: int = row.count
        total_amount: float = float(row.total)
        percentage = (count / total_count * 100) if total_count else 0.0

        return {
            "count": count,
            "total_amount": total_amount,
            "percentage": round(percentage, 2),
        }

    async def get_top_merchants(
        self,
        user_id: str,
        limit: int = 10,
        days: int = 30,
    ) -> list[dict]:
        """Return top merchants by spend in the last N days.

        Args:
            user_id: The user's ID.
            limit: Maximum number of merchants to return.
            days: Look-back window in days.

        Returns:
            List of dicts with keys: merchant, total, count. Sorted by total desc.
        """
        since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

        stmt = (
            select(
                Transaction.merchant,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.merchant.isnot(None),
                Transaction.transaction_date >= since,
            )
            .group_by(Transaction.merchant)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "merchant": row.merchant,
                "total": float(row.total),
                "count": row.count,
            }
            for row in rows
        ]
