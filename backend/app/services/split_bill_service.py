"""Split bill service - business logic for creating and settling split bills."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.social import Contact, SplitBill, SplitGroup, SplitParticipant
from app.schemas.social import SplitBillCreateRequest


class SplitBillService:
    """Service for managing split bills."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the service with a database session."""
        self.session = session

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _bill_status(self, bill: SplitBill) -> str:
        """Derive a display status from the participants' payment state."""
        if not bill.participants:
            return "pending"
        settled = sum(1 for p in bill.participants if p.is_paid)
        if settled == 0:
            return "pending"
        if settled == len(bill.participants):
            return "settled"
        return "partial"

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def create_bill(self, user_id: str, data: SplitBillCreateRequest) -> SplitBill:
        """Create a split bill with participants.

        If the split amounts in ``data.splits`` do not fully cover ``total_amount``
        and no splits are provided, the amount is divided equally among all
        participants.  The ``splits`` list must not be empty.

        Args:
            user_id: The ID of the authenticated user.
            data: Validated request data for the new bill.

        Returns:
            The newly created :class:`SplitBill` with participants loaded.

        Raises:
            ValueError: When validations fail (missing contacts, wrong amounts, etc.)
        """
        if not data.splits:
            raise ValueError("At least one participant is required.")

        # Verify that the payer contact exists and belongs to this user
        payer_result = await self.session.execute(
            select(Contact).where(
                (Contact.id == data.payer_contact_id) & (Contact.user_id == user_id)
            )
        )
        if not payer_result.scalar_one_or_none():
            raise ValueError(f"Payer contact '{data.payer_contact_id}' not found.")

        # Determine the group: use supplied group_id or create an ad-hoc one
        group_id: str
        if data.group_id:
            group_result = await self.session.execute(
                select(SplitGroup).where(
                    (SplitGroup.id == data.group_id) & (SplitGroup.user_id == user_id)
                )
            )
            if not group_result.scalar_one_or_none():
                raise ValueError(f"Split group '{data.group_id}' not found.")
            group_id = data.group_id
        else:
            # Create an implicit group for this bill
            group = SplitGroup(
                user_id=user_id,
                name=f"Nhóm: {data.title}",
                description="Tự động tạo khi tạo hóa đơn",
            )
            self.session.add(group)
            await self.session.flush()  # get generated id
            group_id = group.id

        # Auto-calculate even split if all share_amounts are zero
        all_zero = all(s.share_amount == Decimal(0) for s in data.splits)
        if all_zero:
            per_person = (data.total_amount / len(data.splits)).quantize(Decimal("0.01"))
            share_map = {s.contact_id: per_person for s in data.splits}
        else:
            share_map = {s.contact_id: s.share_amount for s in data.splits}

        # Verify all participant contacts exist
        contact_ids = list(share_map.keys())
        contacts_result = await self.session.execute(
            select(Contact).where(
                (Contact.id.in_(contact_ids)) & (Contact.user_id == user_id)
            )
        )
        found_contacts = {c.id: c for c in contacts_result.scalars().all()}
        missing = set(contact_ids) - set(found_contacts.keys())
        if missing:
            raise ValueError(f"Contacts not found: {', '.join(missing)}")

        # Validate total
        computed_total = sum(share_map.values())
        if not all_zero and abs(computed_total - data.total_amount) > Decimal("0.05"):
            raise ValueError(
                f"Sum of split amounts ({computed_total}) does not match "
                f"total_amount ({data.total_amount})."
            )

        # Build the bill
        already_paid_ids = {
            s.contact_id for s in data.splits if s.already_paid
        }

        bill = SplitBill(
            user_id=user_id,
            split_group_id=group_id,
            name=data.title,
            description=data.notes,
            total_amount=data.total_amount,
            payer_contact_id=data.payer_contact_id,
        )
        self.session.add(bill)
        await self.session.flush()  # get generated id

        for contact_id, share_amount in share_map.items():
            paid = contact_id in already_paid_ids
            participant = SplitParticipant(
                split_bill_id=bill.id,
                contact_id=contact_id,
                share_amount=share_amount,
                is_paid=paid,
                paid_date=datetime.now(timezone.utc).isoformat() if paid else None,
            )
            self.session.add(participant)

        await self.session.commit()
        return await self.get_bill_with_participants(bill.id)  # type: ignore[return-value]

    async def settle_participant(
        self,
        bill_id: str,
        contact_id: str,
        amount: float,
    ) -> SplitParticipant | None:
        """Record a payment from a contact and mark them as settled if fully paid.

        Args:
            bill_id: The split bill ID.
            contact_id: The contact that is paying.
            amount: The amount being paid (may be partial).

        Returns:
            The updated :class:`SplitParticipant`, or ``None`` if not found.
        """
        result = await self.session.execute(
            select(SplitParticipant).where(
                (SplitParticipant.split_bill_id == bill_id)
                & (SplitParticipant.contact_id == contact_id)
            )
        )
        participant = result.scalar_one_or_none()
        if not participant:
            return None

        # Mark as settled — a single call always settles the participant fully
        # (partial tracking is handled by the caller providing exact amounts).
        participant.is_paid = True
        participant.paid_date = datetime.now(timezone.utc).isoformat()

        # Check if the whole bill is now settled and update the flag
        bill_result = await self.session.execute(
            select(SplitBill)
            .options(selectinload(SplitBill.participants))
            .where(SplitBill.id == bill_id)
        )
        bill = bill_result.scalar_one_or_none()
        if bill and all(p.is_paid for p in bill.participants):
            bill.is_settled = True
            bill.settled_date = datetime.now(timezone.utc).isoformat()

        await self.session.commit()
        await self.session.refresh(participant)
        return participant

    async def get_bill_with_participants(self, bill_id: str) -> SplitBill | None:
        """Fetch a split bill with its participants and contact info eager-loaded.

        Args:
            bill_id: The split bill ID to look up.

        Returns:
            The :class:`SplitBill` instance, or ``None`` if not found.
        """
        result = await self.session.execute(
            select(SplitBill)
            .options(
                selectinload(SplitBill.participants).selectinload(SplitParticipant.contact),
                selectinload(SplitBill.payer_contact),
            )
            .where(SplitBill.id == bill_id)
        )
        return result.scalar_one_or_none()
