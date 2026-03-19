"""Subscription service - business logic for managing recurring subscriptions."""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from statistics import mean, stdev

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import BudgetPeriod, Subscription
from app.models.transaction import Transaction, TransactionType
from app.schemas.planning import (
    SubscriptionCreateRequest,
    SubscriptionDetectionResult,
    SubscriptionUpdateRequest,
)

# Multipliers to compute annual cost from a per-cycle amount
_ANNUAL_MULTIPLIERS: dict[BudgetPeriod, Decimal] = {
    BudgetPeriod.DAILY: Decimal("365"),
    BudgetPeriod.WEEKLY: Decimal("52"),
    BudgetPeriod.MONTHLY: Decimal("12"),
    BudgetPeriod.QUARTERLY: Decimal("4"),
    BudgetPeriod.YEARLY: Decimal("1"),
}


def _compute_annual_cost(amount: Decimal, cycle: BudgetPeriod) -> Decimal:
    """Compute annual cost given a per-cycle amount and billing period.

    Args:
        amount: Amount per billing cycle.
        cycle: Billing period.

    Returns:
        Estimated annual cost as Decimal.
    """
    multiplier = _ANNUAL_MULTIPLIERS.get(cycle, Decimal("12"))
    return (amount * multiplier).quantize(Decimal("0.01"))


def _is_regular_interval(intervals: list[int], target: int, tolerance: int) -> bool:
    """Check whether a list of day-intervals clusters near a target value.

    Args:
        intervals: List of day-count intervals between transactions.
        target: Expected interval in days (e.g., 30 for monthly).
        tolerance: Acceptable deviation in days.

    Returns:
        True if the mean interval is within tolerance of target.
    """
    if not intervals:
        return False
    avg = mean(intervals)
    return abs(avg - target) <= tolerance


def _detect_cycle(intervals: list[int]) -> tuple[str, float]:
    """Infer billing cycle and confidence from a list of day intervals.

    Args:
        intervals: List of day-count intervals between transactions.

    Returns:
        Tuple of (cycle_name, confidence_score).
    """
    if not intervals:
        return "monthly", 0.5

    avg = mean(intervals)
    spread = stdev(intervals) if len(intervals) > 1 else 0.0

    cycle_targets = [
        ("weekly", 7, 2),
        ("monthly", 30, 4),
        ("yearly", 365, 10),
    ]

    for name, target, tol in cycle_targets:
        if abs(avg - target) <= tol:
            # Higher confidence when spread is low
            confidence = max(0.5, 1.0 - (spread / max(target, 1)) * 2)
            return name, round(min(confidence, 1.0), 2)

    return "monthly", 0.4


class SubscriptionService:
    """Service for managing subscriptions and detecting recurring charges."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the service with a database session.

        Args:
            session: The async SQLAlchemy session to use for all queries.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def create_subscription(
        self, user_id: str, data: SubscriptionCreateRequest
    ) -> Subscription:
        """Create a new subscription record.

        Args:
            user_id: The authenticated user's ID.
            data: Validated subscription creation data.

        Returns:
            The newly created Subscription instance.
        """
        sub = Subscription(
            user_id=user_id,
            category_id=data.category_id,
            name=data.name,
            description=data.description,
            amount=data.amount,
            currency=data.currency,
            billing_period=data.billing_cycle,
            start_date=data.start_date,
            next_billing_date=data.next_billing_date,
            end_date=data.end_date,
            is_active=True,
            is_auto_renew=data.is_auto_renew,
        )
        self.session.add(sub)
        await self.session.commit()
        await self.session.refresh(sub)
        return sub

    async def get_subscriptions(
        self, user_id: str, active_only: bool = True
    ) -> list[Subscription]:
        """Retrieve all subscriptions for a user.

        Args:
            user_id: The authenticated user's ID.
            active_only: When True, only return active subscriptions.

        Returns:
            List of Subscription instances.
        """
        query = select(Subscription).where(Subscription.user_id == user_id)
        if active_only:
            query = query.where(Subscription.is_active.is_(True))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_subscription(
        self, sub_id: str, user_id: str
    ) -> Subscription | None:
        """Fetch a single subscription by ID.

        Args:
            sub_id: The subscription's UUID.
            user_id: The authenticated user's ID.

        Returns:
            The Subscription instance or None if not found.
        """
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.id == sub_id, Subscription.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def update_subscription(
        self, sub_id: str, user_id: str, data: SubscriptionUpdateRequest
    ) -> Subscription | None:
        """Update an existing subscription.

        Args:
            sub_id: The subscription's UUID.
            user_id: The authenticated user's ID.
            data: Fields to update (only non-None values are applied).

        Returns:
            Updated Subscription instance, or None if not found.
        """
        sub = await self.get_subscription(sub_id, user_id)
        if sub is None:
            return None

        if data.name is not None:
            sub.name = data.name
        if data.description is not None:
            sub.description = data.description
        if data.amount is not None:
            sub.amount = data.amount
        if data.currency is not None:
            sub.currency = data.currency
        if data.billing_cycle is not None:
            sub.billing_period = data.billing_cycle
        if data.next_billing_date is not None:
            sub.next_billing_date = data.next_billing_date
        if data.end_date is not None:
            sub.end_date = data.end_date
        if data.category_id is not None:
            sub.category_id = data.category_id
        if data.is_active is not None:
            sub.is_active = data.is_active
        if data.is_auto_renew is not None:
            sub.is_auto_renew = data.is_auto_renew

        await self.session.commit()
        await self.session.refresh(sub)
        return sub

    async def cancel_subscription(self, sub_id: str, user_id: str) -> bool:
        """Mark a subscription as inactive (cancelled).

        Args:
            sub_id: The subscription's UUID.
            user_id: The authenticated user's ID.

        Returns:
            True if found and cancelled, False otherwise.
        """
        sub = await self.get_subscription(sub_id, user_id)
        if sub is None:
            return False
        sub.is_active = False
        await self.session.commit()
        return True

    async def detect_subscriptions(
        self, user_id: str
    ) -> list[SubscriptionDetectionResult]:
        """Detect recurring charges from transaction history.

        Analyses the last 90 days of expense transactions, groups them by
        merchant, and identifies those with at least two occurrences at a
        regular interval (weekly, monthly, or yearly).

        Args:
            user_id: The authenticated user's ID.

        Returns:
            List of SubscriptionDetectionResult describing detected subscriptions.
        """
        cutoff = (date.today() - timedelta(days=90)).isoformat()
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= cutoff,
                Transaction.merchant.isnot(None),
            )
        )
        transactions = list(result.scalars().all())

        # Group by (merchant, amount) rounded to nearest 1000 for fuzzy match
        groups: dict[tuple[str, int], list[Transaction]] = defaultdict(list)
        for txn in transactions:
            merchant = (txn.merchant or "").strip()
            if not merchant:
                continue
            rounded_amount = int(round(float(txn.amount) / 1000) * 1000)
            groups[(merchant, rounded_amount)].append(txn)

        results: list[SubscriptionDetectionResult] = []

        for (merchant, _), txns in groups.items():
            if len(txns) < 2:
                continue

            # Sort by date and compute intervals
            sorted_txns = sorted(txns, key=lambda t: t.transaction_date)
            dates = [t.transaction_date for t in sorted_txns]
            intervals: list[int] = []
            for i in range(len(dates) - 1):
                try:
                    d1 = date.fromisoformat(dates[i])
                    d2 = date.fromisoformat(dates[i + 1])
                    intervals.append((d2 - d1).days)
                except ValueError:
                    pass

            if not intervals:
                continue

            # Check whether any known cycle matches
            has_match = (
                _is_regular_interval(intervals, 7, 2)
                or _is_regular_interval(intervals, 30, 4)
                or _is_regular_interval(intervals, 365, 10)
            )
            if not has_match:
                continue

            cycle_name, confidence = _detect_cycle(intervals)
            avg_amount = Decimal(str(mean([float(t.amount) for t in txns]))).quantize(
                Decimal("0.01")
            )

            results.append(
                SubscriptionDetectionResult(
                    name=merchant,
                    amount=avg_amount,
                    suggested_category=None,
                    confidence=confidence,
                    transaction_ids=[t.id for t in txns],
                    billing_cycle=cycle_name,
                )
            )

        # Sort by confidence descending
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    async def get_subscription_summary(self, user_id: str) -> dict:
        """Return aggregate cost statistics for active subscriptions.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            Dict with monthly_cost, yearly_cost, active_count, upcoming_count.
        """
        subs = await self.get_subscriptions(user_id, active_only=True)

        total_annual = Decimal("0")
        for sub in subs:
            total_annual += _compute_annual_cost(
                Decimal(str(sub.amount)), sub.billing_period
            )

        monthly_cost = (total_annual / 12).quantize(Decimal("0.01"))
        today = date.today().isoformat()
        upcoming_cutoff = (date.today() + timedelta(days=7)).isoformat()
        upcoming = [
            s for s in subs if today <= s.next_billing_date <= upcoming_cutoff
        ]

        return {
            "active_count": len(subs),
            "monthly_cost": float(monthly_cost),
            "yearly_cost": float(total_annual),
            "upcoming_renewals_count": len(upcoming),
        }

    async def get_upcoming_renewals(
        self, user_id: str, days: int = 7
    ) -> list[Subscription]:
        """Return active subscriptions renewing within the next N days.

        Args:
            user_id: The authenticated user's ID.
            days: Number of days to look ahead (default 7).

        Returns:
            List of Subscription instances sorted by next_billing_date ascending.
        """
        today = date.today().isoformat()
        cutoff = (date.today() + timedelta(days=days)).isoformat()

        result = await self.session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active.is_(True),
                Subscription.next_billing_date >= today,
                Subscription.next_billing_date <= cutoff,
            )
        )
        subs = list(result.scalars().all())
        subs.sort(key=lambda s: s.next_billing_date)
        return subs
