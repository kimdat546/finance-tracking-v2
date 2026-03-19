"""Debt service - business logic for debt tracking and payments."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import Debt, DebtStatus
from app.schemas.planning import DebtCreateRequest, DebtUpdateRequest

# Prefix used to embed debt_type in the description field since the model
# does not have a dedicated debt_type column.
_DEBT_TYPE_PREFIX = "__debt_type__:"


def _encode_description(original_description: str | None, debt_type: str) -> str:
    """Encode debt_type into the description field.

    Args:
        original_description: User-provided description (may be None).
        debt_type: 'owe' or 'owed'.

    Returns:
        Encoded description string.
    """
    base = original_description or ""
    return f"{_DEBT_TYPE_PREFIX}{debt_type}|{base}"


def _decode_description(stored: str | None) -> tuple[str, str | None]:
    """Decode debt_type and original description from the stored description.

    Args:
        stored: The value stored in Debt.description.

    Returns:
        Tuple of (debt_type, original_description). debt_type defaults to 'owe'.
    """
    if stored and stored.startswith(_DEBT_TYPE_PREFIX):
        rest = stored[len(_DEBT_TYPE_PREFIX):]
        parts = rest.split("|", 1)
        debt_type = parts[0] if parts else "owe"
        description = parts[1] if len(parts) > 1 and parts[1] else None
        return debt_type, description
    return "owe", stored


class DebtService:
    """Service for managing debts and recording payments."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the service with a database session.

        Args:
            session: The async SQLAlchemy session to use for all queries.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_debt_dict(self, debt: Debt) -> dict:
        """Convert a Debt ORM instance to a dict matching DebtSchema.

        Computes paid_amount from original_amount - remaining_amount and
        decodes the debt_type from the description field.

        Args:
            debt: The Debt model instance.

        Returns:
            Dict suitable for constructing DebtSchema.
        """
        debt_type, description = _decode_description(debt.description)
        original = Decimal(str(debt.original_amount))
        remaining = Decimal(str(debt.remaining_amount))
        paid = max(original - remaining, Decimal("0"))

        return {
            "id": debt.id,
            "name": debt.creditor,  # stored in creditor for compatibility
            "creditor": debt.creditor,
            "description": description,
            "amount": original,
            "paid_amount": paid,
            "remaining_amount": remaining,
            "currency": debt.currency,
            "interest_rate": debt.interest_rate,
            "monthly_payment": debt.monthly_payment,
            "start_date": debt.start_date,
            "due_date": debt.due_date,
            "paid_off_date": debt.paid_off_date,
            "debt_type": debt_type,
            "status": debt.status.value if hasattr(debt.status, "value") else debt.status,
            "is_active": debt.status == DebtStatus.ACTIVE,
        }

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def create_debt(self, user_id: str, data: DebtCreateRequest) -> Debt:
        """Create a new debt record.

        Args:
            user_id: The authenticated user's ID.
            data: Validated debt creation data.

        Returns:
            The newly created Debt instance.
        """
        encoded_desc = _encode_description(data.description, data.debt_type)
        debt = Debt(
            user_id=user_id,
            creditor=data.creditor,
            description=encoded_desc,
            original_amount=data.amount,
            remaining_amount=data.amount,  # No payments yet
            currency=data.currency,
            interest_rate=data.interest_rate,
            monthly_payment=data.monthly_payment,
            start_date=data.start_date,
            due_date=data.due_date,
            status=DebtStatus.ACTIVE,
        )
        self.session.add(debt)
        await self.session.commit()
        await self.session.refresh(debt)
        return debt

    async def get_debts(
        self, user_id: str, debt_type: str | None = None
    ) -> list[Debt]:
        """Retrieve all debts for a user, optionally filtering by type.

        Args:
            user_id: The authenticated user's ID.
            debt_type: Optional filter: 'owe' or 'owed'. When None, returns all.

        Returns:
            List of Debt instances. Note: debt_type filtering is applied in Python
            since it is encoded in the description field.
        """
        result = await self.session.execute(
            select(Debt).where(Debt.user_id == user_id)
        )
        debts = list(result.scalars().all())

        if debt_type is not None:
            debts = [d for d in debts if _decode_description(d.description)[0] == debt_type]

        return debts

    async def get_debt(self, debt_id: str, user_id: str) -> Debt | None:
        """Fetch a single debt by ID.

        Args:
            debt_id: The debt's UUID.
            user_id: The authenticated user's ID.

        Returns:
            The Debt instance or None if not found.
        """
        result = await self.session.execute(
            select(Debt).where(Debt.id == debt_id, Debt.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def record_payment(
        self, debt_id: str, amount: float, user_id: str
    ) -> Debt | None:
        """Record a payment against a debt, reducing the remaining balance.

        If the payment brings remaining_amount to zero or below, the debt
        status is updated to PAID_OFF and the paid_off_date is set to today.

        Args:
            debt_id: The debt's UUID.
            amount: Payment amount (must be positive).
            user_id: The authenticated user's ID.

        Returns:
            Updated Debt instance, or None if not found.

        Raises:
            ValueError: If the amount is not positive.
        """
        if amount <= 0:
            raise ValueError("Payment amount must be positive.")

        debt = await self.get_debt(debt_id, user_id)
        if debt is None:
            return None

        payment = Decimal(str(amount))
        new_remaining = Decimal(str(debt.remaining_amount)) - payment
        debt.remaining_amount = max(new_remaining, Decimal("0"))

        if debt.remaining_amount <= 0:
            debt.status = DebtStatus.PAID_OFF
            debt.paid_off_date = date.today().isoformat()

        await self.session.commit()
        await self.session.refresh(debt)
        return debt

    async def update_debt(
        self, debt_id: str, user_id: str, data: DebtUpdateRequest
    ) -> Debt | None:
        """Update an existing debt record.

        Args:
            debt_id: The debt's UUID.
            user_id: The authenticated user's ID.
            data: Fields to update (only non-None values are applied).

        Returns:
            Updated Debt instance, or None if not found.
        """
        debt = await self.get_debt(debt_id, user_id)
        if debt is None:
            return None

        if data.creditor is not None:
            debt.creditor = data.creditor
        if data.interest_rate is not None:
            debt.interest_rate = data.interest_rate
        if data.monthly_payment is not None:
            debt.monthly_payment = data.monthly_payment
        if data.due_date is not None:
            debt.due_date = data.due_date
        if data.status is not None:
            debt.status = DebtStatus(data.status)

        # Re-encode description if either description or name changed
        if data.description is not None or data.name is not None:
            current_type, _ = _decode_description(debt.description)
            new_desc = data.description  # may be None if not updating
            debt.description = _encode_description(new_desc, current_type)

        await self.session.commit()
        await self.session.refresh(debt)
        return debt

    async def delete_debt(self, debt_id: str, user_id: str) -> bool:
        """Permanently delete a debt record.

        Args:
            debt_id: The debt's UUID.
            user_id: The authenticated user's ID.

        Returns:
            True if the debt was found and deleted, False otherwise.
        """
        debt = await self.get_debt(debt_id, user_id)
        if debt is None:
            return False
        await self.session.delete(debt)
        await self.session.commit()
        return True

    async def get_debt_summary(self, user_id: str) -> dict:
        """Return an aggregate summary of debts for a user.

        Provides total amounts owed vs owed-to-user, net position, and
        a list of upcoming due dates within 30 days.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            Dict with total_owe, total_owed, net_position, upcoming_due.
        """
        debts = await self.get_debts(user_id)
        total_owe = Decimal("0")
        total_owed = Decimal("0")
        upcoming: list[dict] = []

        today = date.today().isoformat()
        thirty_days_later = (
            date.today().replace(day=min(date.today().day + 30, 28)).isoformat()
        )

        for debt in debts:
            if debt.status == DebtStatus.PAID_OFF:
                continue

            debt_type, _ = _decode_description(debt.description)
            remaining = Decimal(str(debt.remaining_amount))

            if debt_type == "owe":
                total_owe += remaining
            else:
                total_owed += remaining

            if debt.due_date and today <= debt.due_date <= thirty_days_later:
                upcoming.append(
                    {
                        "debt_id": debt.id,
                        "creditor": debt.creditor,
                        "due_date": debt.due_date,
                        "remaining": float(remaining),
                        "debt_type": debt_type,
                    }
                )

        upcoming.sort(key=lambda x: x["due_date"])

        return {
            "total_owe": float(total_owe),
            "total_owed": float(total_owed),
            "net_position": float(total_owed - total_owe),
            "active_debt_count": len(
                [d for d in debts if d.status == DebtStatus.ACTIVE]
            ),
            "upcoming_due": upcoming,
        }
