"""Trends service - spending trend analysis and anomaly detection."""

import calendar
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Category, Transaction, TransactionType


class TrendsService:
    """Spending trend analysis, anomaly detection, and recurring transaction detection."""

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
        """Return ISO date strings for the start and end of a month.

        Args:
            year: Four-digit year.
            month: Month number 1-12.

        Returns:
            Tuple (start_str, end_str).
        """
        _, last_day = calendar.monthrange(year, month)
        return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day:02d}"

    def _prev_month(self, year: int, month: int) -> tuple[int, int]:
        """Return (year, month) for the month preceding the given one.

        Args:
            year: Four-digit year.
            month: Month number 1-12.

        Returns:
            (year, month) of the previous month.
        """
        if month == 1:
            return year - 1, 12
        return year, month - 1

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_category_trends(
        self,
        user_id: str,
        months: int = 6,
        category_ids: list[str] | None = None,
    ) -> list[dict]:
        """Monthly spending per category for the last N months.

        Args:
            user_id: The authenticated user's ID.
            months: Number of past months to include.
            category_ids: Optional filter to specific category IDs.

        Returns:
            List of dicts: {"month": "YYYY-MM", "categories": {"Cat": amount}}.
        """
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
        results: list[dict] = []

        for _ in range(months):
            start, end = self._month_range(year, month)

            query = (
                select(
                    Category.name,
                    func.sum(Transaction.amount).label("total"),
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
            )
            if category_ids:
                query = query.where(Category.id.in_(category_ids))

            rows = (await self.session.execute(query)).all()
            categories = {row.name: float(row.total) for row in rows}

            results.append({"month": f"{year}-{month:02d}", "categories": categories})
            year, month = self._prev_month(year, month)

        results.reverse()
        return results

    async def get_merchant_trends(
        self, user_id: str, merchant_name: str, months: int = 12
    ) -> list[dict]:
        """Monthly spending at a specific merchant over the last N months.

        Args:
            user_id: The authenticated user's ID.
            merchant_name: The merchant name to search for (case-insensitive contains).
            months: Number of past months to include.

        Returns:
            List of dicts: {"month": "YYYY-MM", "amount": float, "count": int}.
        """
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
        results: list[dict] = []

        for _ in range(months):
            start, end = self._month_range(year, month)

            result = await self.session.execute(
                select(
                    func.coalesce(func.sum(Transaction.amount), 0).label("total"),
                    func.count(Transaction.id).label("cnt"),
                ).where(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.EXPENSE,
                    Transaction.transaction_date >= start,
                    Transaction.transaction_date <= end,
                    Transaction.merchant.ilike(f"%{merchant_name}%"),
                )
            )
            row = result.one_or_none()
            results.append(
                {
                    "month": f"{year}-{month:02d}",
                    "amount": float(row.total) if row else 0.0,
                    "count": row.cnt if row else 0,
                }
            )
            year, month = self._prev_month(year, month)

        results.reverse()
        return results

    async def detect_anomalies(self, user_id: str, months: int = 3) -> list[dict]:
        """Detect unusual spending: transactions more than 2x the category average.

        Args:
            user_id: The authenticated user's ID.
            months: Number of past months to compute averages from.

        Returns:
            List of anomaly dicts with transaction_id, amount, category, z_score.
        """
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month

        # Compute the lookback start date
        for _ in range(months):
            year, month = self._prev_month(year, month)
        start = f"{year}-{month:02d}-01"
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Compute per-category average and stddev
        stats_result = await self.session.execute(
            select(
                Transaction.category_id,
                func.avg(Transaction.amount).label("avg"),
                func.count(Transaction.id).label("cnt"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
                Transaction.category_id.isnot(None),
            )
            .group_by(Transaction.category_id)
            .having(func.count(Transaction.id) >= 3)
        )
        category_stats: dict[str, float] = {}
        for row in stats_result.all():
            category_stats[row.category_id] = float(row.avg)

        if not category_stats:
            return []

        # Fetch transactions in period
        txns_result = await self.session.execute(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
                Transaction.category_id.in_(list(category_stats.keys())),
            )
            .order_by(Transaction.transaction_date.desc())
        )
        transactions = txns_result.scalars().all()

        # Compute per-category stddev manually
        category_amounts: dict[str, list[float]] = {}
        for t in transactions:
            cid = t.category_id
            if cid:
                category_amounts.setdefault(cid, []).append(float(t.amount))

        def stddev(values: list[float]) -> float:
            if len(values) < 2:
                return 0.0
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
            return variance ** 0.5

        category_stddev: dict[str, float] = {
            cid: stddev(amounts) for cid, amounts in category_amounts.items()
        }

        # Load category names
        cat_ids = list(category_stats.keys())
        cat_result = await self.session.execute(
            select(Category.id, Category.name).where(Category.id.in_(cat_ids))
        )
        cat_names = {row.id: row.name for row in cat_result.all()}

        anomalies: list[dict] = []
        for t in transactions:
            cid = t.category_id
            if not cid or cid not in category_stats:
                continue
            avg = category_stats[cid]
            std = category_stddev.get(cid, 0.0)
            amount = float(t.amount)
            if amount > 2 * avg:
                z_score = (amount - avg) / std if std > 0 else 0.0
                anomalies.append(
                    {
                        "transaction_id": t.id,
                        "amount": amount,
                        "category": cat_names.get(cid, ""),
                        "category_avg": round(avg, 2),
                        "z_score": round(z_score, 2),
                        "transaction_date": t.transaction_date,
                        "description": t.description,
                    }
                )

        return sorted(anomalies, key=lambda x: x["z_score"], reverse=True)

    async def get_recurring_transactions(self, user_id: str, months: int = 3) -> list[dict]:
        """Find transactions that repeat regularly (subscriptions, rent, etc.).

        Groups by merchant or description and looks for patterns that repeat
        monthly with similar amounts.

        Args:
            user_id: The authenticated user's ID.
            months: Number of past months to analyse.

        Returns:
            List of dicts describing detected recurring charges.
        """
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
        for _ in range(months):
            year, month = self._prev_month(year, month)
        start = f"{year}-{month:02d}-01"
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Group by merchant and description to find repeating charges
        result = await self.session.execute(
            select(
                Transaction.merchant,
                Transaction.description,
                func.count(Transaction.id).label("occurrences"),
                func.avg(Transaction.amount).label("avg_amount"),
                func.min(Transaction.amount).label("min_amount"),
                func.max(Transaction.amount).label("max_amount"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
            )
            .group_by(Transaction.merchant, Transaction.description)
            .having(func.count(Transaction.id) >= 2)
            .order_by(func.count(Transaction.id).desc())
        )

        recurring: list[dict] = []
        for row in result.all():
            min_amt = float(row.min_amount)
            max_amt = float(row.max_amount)
            avg_amt = float(row.avg_amount)
            # Check consistency: max vs min within 10%
            is_consistent = (max_amt - min_amt) / avg_amt < 0.10 if avg_amt > 0 else False
            if is_consistent or row.occurrences >= months:
                recurring.append(
                    {
                        "merchant": row.merchant,
                        "description": row.description,
                        "occurrences": row.occurrences,
                        "avg_amount": round(avg_amt, 2),
                        "is_consistent_amount": is_consistent,
                    }
                )

        return recurring
