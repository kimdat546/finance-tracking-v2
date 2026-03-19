"""Reminder service - generate pending reminders for overdue split bills."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.social import Contact, SplitBill, SplitParticipant


class ReminderService:
    """Service for generating split bill reminders."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session."""
        self.session = session

    async def get_pending_reminders(self, user_id: str) -> list[dict]:
        """Get the list of contacts with outstanding debts for reminder.

        Groups unsettled participants by contact and returns one entry per
        contact with the total outstanding amount and the oldest bill date.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            A list of dicts each containing ``contact_id``, ``contact_name``,
            ``total_owed``, ``oldest_bill_date``, ``bill_titles``, and
            ``reminder_message``.
        """
        bills_result = await self.session.execute(
            select(SplitBill)
            .options(
                selectinload(SplitBill.participants).selectinload(SplitParticipant.contact)
            )
            .where(
                (SplitBill.user_id == user_id) & (SplitBill.is_settled == False)  # noqa: E712
            )
            .order_by(SplitBill.created_at.asc())
        )
        bills = bills_result.scalars().all()

        # Aggregate per contact
        aggregated: dict[str, dict] = {}

        for bill in bills:
            for participant in bill.participants:
                if participant.is_paid:
                    continue
                cid = participant.contact_id
                cname = participant.contact.name if participant.contact else cid

                if cid not in aggregated:
                    aggregated[cid] = {
                        "contact_id": cid,
                        "contact_name": cname,
                        "total_owed": Decimal("0.00"),
                        "oldest_bill_date": bill.created_at,
                        "bill_titles": [],
                    }

                aggregated[cid]["total_owed"] += participant.share_amount
                if bill.created_at < aggregated[cid]["oldest_bill_date"]:
                    aggregated[cid]["oldest_bill_date"] = bill.created_at
                if bill.name not in aggregated[cid]["bill_titles"]:
                    aggregated[cid]["bill_titles"].append(bill.name)

        result = []
        for data in aggregated.values():
            message = await self.format_reminder_message(
                contact_name=data["contact_name"],
                amount=float(data["total_owed"]),
                bill_titles=data["bill_titles"],
            )
            result.append(
                {
                    "contact_id": data["contact_id"],
                    "contact_name": data["contact_name"],
                    "total_owed": data["total_owed"],
                    "oldest_bill_date": data["oldest_bill_date"],
                    "bill_titles": data["bill_titles"],
                    "reminder_message": message,
                }
            )

        return result

    async def format_reminder_message(
        self,
        contact_name: str,
        amount: float,
        bill_titles: list[str],
    ) -> str:
        """Format a Vietnamese reminder message.

        Args:
            contact_name: Name of the contact who owes money.
            amount: Amount owed in VND.
            bill_titles: List of bill titles included in the reminder.

        Returns:
            A formatted Vietnamese reminder string.
        """
        amount_formatted = f"{int(amount):,}".replace(",", ".")
        bills_str = ", ".join(bill_titles) if bill_titles else "các hóa đơn"
        return (
            f"Nhắc nhở: {contact_name} chưa thanh toán "
            f"{amount_formatted} VND cho {bills_str}"
        )

    async def get_overdue_bills(
        self,
        user_id: str,
        overdue_days: int = 7,
    ) -> list[SplitBill]:
        """Get split bills older than N days that are not settled.

        Args:
            user_id: The authenticated user's ID.
            overdue_days: Number of days after which a bill is considered overdue.

        Returns:
            A list of overdue, unsettled :class:`SplitBill` instances.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=overdue_days)

        result = await self.session.execute(
            select(SplitBill)
            .options(
                selectinload(SplitBill.participants).selectinload(SplitParticipant.contact)
            )
            .where(
                (SplitBill.user_id == user_id)
                & (SplitBill.is_settled == False)  # noqa: E712
                & (SplitBill.created_at < cutoff)
            )
            .order_by(SplitBill.created_at.asc())
        )
        return result.scalars().all()
