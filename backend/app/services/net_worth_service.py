"""Net worth service - track assets, liabilities, and net worth over time."""

import calendar
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import Debt
from app.models.transaction import Account, Transaction, TransactionType


class NetWorthService:
    """Calculates and tracks net worth (assets minus liabilities)."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the service with a database session.

        Args:
            session: The async SQLAlchemy session to use for all queries.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _prev_month(self, year: int, month: int) -> tuple[int, int]:
        """Return (year, month) for the previous month.

        Args:
            year: Four-digit year.
            month: Month number 1-12.

        Returns:
            (year, month) tuple for the preceding month.
        """
        if month == 1:
            return year - 1, 12
        return year, month - 1

    def _month_range(self, year: int, month: int) -> tuple[str, str]:
        """Return (start_date, end_date) strings for the given year/month.

        Args:
            year: Four-digit year.
            month: Month number 1-12.

        Returns:
            Tuple of ISO date strings.
        """
        _, last_day = calendar.monthrange(year, month)
        return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day:02d}"

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_current_net_worth(self, user_id: str) -> dict:
        """Current net worth: total assets minus total liabilities.

        Assets are the sum of all active account balances.
        Liabilities are the sum of all outstanding (active) debt remaining amounts.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            Dict with assets, liabilities, net_worth, accounts list, debts list.
        """
        # Fetch accounts
        accounts_result = await self.session.execute(
            select(Account).where(Account.user_id == user_id, Account.is_active.is_(True))
        )
        accounts = accounts_result.scalars().all()
        account_list = [
            {"id": a.id, "name": a.name, "balance": float(a.balance), "currency": a.currency}
            for a in accounts
        ]
        total_assets = sum(float(a.balance) for a in accounts)

        # Fetch active debts
        debts_result = await self.session.execute(
            select(Debt).where(Debt.user_id == user_id, Debt.status == "active")
        )
        debts = debts_result.scalars().all()
        debt_list = [
            {
                "id": d.id,
                "name": d.creditor,
                "remaining": float(d.remaining_amount),
                "currency": d.currency,
            }
            for d in debts
        ]
        total_liabilities = sum(float(d.remaining_amount) for d in debts)

        net_worth = total_assets - total_liabilities
        return {
            "assets": round(total_assets, 2),
            "liabilities": round(total_liabilities, 2),
            "net_worth": round(net_worth, 2),
            "accounts": account_list,
            "debts": debt_list,
        }

    async def get_net_worth_history(self, user_id: str, months: int = 12) -> list[dict]:
        """Approximate net worth history by month (estimated from transaction flows).

        Starts from the current net worth and works backwards by reversing
        the net cash flow for each month.

        Args:
            user_id: The authenticated user's ID.
            months: Number of months of history to generate.

        Returns:
            List of dicts: {"month": "YYYY-MM", "net_worth": float} ordered oldest first.
        """
        # Get current net worth as baseline
        current = await self.get_current_net_worth(user_id)
        current_nw = Decimal(str(current["net_worth"]))

        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
        history: list[dict] = []

        running_nw = current_nw
        for i in range(months):
            start, end = self._month_range(year, month)

            # Net cash flow for this month
            income_result = await self.session.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.INCOME,
                    Transaction.transaction_date >= start,
                    Transaction.transaction_date <= end,
                )
            )
            income_val = income_result.scalar_one_or_none()
            income = Decimal(str(income_val)) if income_val is not None else Decimal("0")

            expense_result = await self.session.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.EXPENSE,
                    Transaction.transaction_date >= start,
                    Transaction.transaction_date <= end,
                )
            )
            expense_val = expense_result.scalar_one_or_none()
            expense = Decimal(str(expense_val)) if expense_val is not None else Decimal("0")

            if i == 0:
                # Current month: use actual net worth
                history.append(
                    {"month": f"{year}-{month:02d}", "net_worth": float(current_nw)}
                )
            else:
                history.append(
                    {"month": f"{year}-{month:02d}", "net_worth": round(float(running_nw), 2)}
                )

            # Step back: subtract this month's net inflow to get prior month
            running_nw -= income - expense
            year, month = self._prev_month(year, month)

        history.reverse()
        return history
