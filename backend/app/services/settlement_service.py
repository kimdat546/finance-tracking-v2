"""Settlement service - net balance calculation and auto-settlement detection."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.social import Contact, SplitBill, SplitParticipant
from app.models.transaction import Transaction


class SettlementService:
    """Detects settlements and calculates net balances between contacts."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session."""
        self.session = session

    async def calculate_net_balances(self, user_id: str) -> list[dict]:
        """Calculate net balances between the user and each contact.

        For each contact, computes:
        - ``they_owe_me``: sum of share amounts across unsettled bills where the
          user is the payer and the contact is a participant.
        - ``i_owe_them``: sum of share amounts across unsettled bills where the
          contact is the payer and the user is a participant (identified by
          having contacts that belong to the user).

        Args:
            user_id: The authenticated user's ID.

        Returns:
            A list of dicts, each containing ``contact_id``, ``contact_name``,
            ``they_owe_me``, ``i_owe_them``, and ``net``.
        """
        # Fetch all contacts for this user
        contacts_result = await self.session.execute(
            select(Contact).where(Contact.user_id == user_id)
        )
        contacts = contacts_result.scalars().all()
        if not contacts:
            return []

        contact_map = {c.id: c for c in contacts}

        # Bills where the user's contacts are involved (user is the bill owner)
        bills_result = await self.session.execute(
            select(SplitBill)
            .options(
                selectinload(SplitBill.participants).selectinload(SplitParticipant.contact)
            )
            .where((SplitBill.user_id == user_id) & (SplitBill.is_settled == False))  # noqa: E712
        )
        bills = bills_result.scalars().all()

        balances: dict[str, dict] = {}

        def _init(contact_id: str, contact_name: str) -> None:
            if contact_id not in balances:
                balances[contact_id] = {
                    "contact_id": contact_id,
                    "contact_name": contact_name,
                    "they_owe_me": Decimal("0.00"),
                    "i_owe_them": Decimal("0.00"),
                }

        for bill in bills:
            for participant in bill.participants:
                if participant.is_paid:
                    continue
                cid = participant.contact_id
                cname = participant.contact.name if participant.contact else cid

                # The payer is a user contact → the participant owes the payer
                if bill.payer_contact_id in contact_map:
                    # Payer is one of the user's contacts — track participant as debtor
                    # Only relevant when payer != participant
                    if cid != bill.payer_contact_id and cid in contact_map:
                        _init(cid, cname)
                        balances[cid]["they_owe_me"] += participant.share_amount

                # If this participant is the user's payer contact and payer is different
                # from bill payer, track what the user owes
                # (Bills created by this user where payer != user → user owes payer)
                if cid in contact_map and bill.payer_contact_id not in contact_map:
                    payer_id = bill.payer_contact_id
                    # payer_contact might not be in user's contact list
                    payer_name = (
                        bill.payer_contact.name if bill.payer_contact else payer_id
                    )
                    _init(payer_id, payer_name)
                    balances[payer_id]["i_owe_them"] += participant.share_amount

        result = []
        for data in balances.values():
            net = data["they_owe_me"] - data["i_owe_them"]
            result.append(
                {
                    "contact_id": data["contact_id"],
                    "contact_name": data["contact_name"],
                    "they_owe_me": data["they_owe_me"],
                    "i_owe_them": data["i_owe_them"],
                    "net": net,
                }
            )

        return result

    async def detect_settlement_transaction(
        self,
        user_id: str,
        transaction_id: str,
    ) -> SplitParticipant | None:
        """Try to match a transaction as a settlement payment.

        The match is performed by:
        1. Finding the transaction and reading its amount and description.
        2. Looking for an unsettled participant whose share_amount equals the
           transaction amount (within ±1 VND tolerance).
        3. Checking that the contact's name appears in the transaction description
           (case-insensitive).

        Args:
            user_id: The authenticated user's ID.
            transaction_id: The transaction to attempt matching.

        Returns:
            The matched :class:`SplitParticipant` if found and settled, else ``None``.
        """
        tx_result = await self.session.execute(
            select(Transaction).where(
                (Transaction.id == transaction_id) & (Transaction.user_id == user_id)
            )
        )
        transaction = tx_result.scalar_one_or_none()
        if not transaction:
            return None

        tx_amount = transaction.amount
        tx_description = (transaction.description or "").lower()

        # Find unsettled participants whose share matches this amount
        participants_result = await self.session.execute(
            select(SplitParticipant)
            .options(
                selectinload(SplitParticipant.contact),
                selectinload(SplitParticipant.split_bill),
            )
            .join(SplitBill, SplitParticipant.split_bill_id == SplitBill.id)
            .where(
                (SplitBill.user_id == user_id)
                & (SplitParticipant.is_paid == False)  # noqa: E712
            )
        )
        participants = participants_result.scalars().all()

        for participant in participants:
            if abs(participant.share_amount - tx_amount) > Decimal("1.00"):
                continue
            contact_name = (participant.contact.name if participant.contact else "").lower()
            if contact_name and contact_name in tx_description:
                # Match found — mark as settled
                participant.is_paid = True
                participant.paid_date = datetime.now(timezone.utc).isoformat()

                # Check whole-bill settlement
                bill_result = await self.session.execute(
                    select(SplitBill)
                    .options(selectinload(SplitBill.participants))
                    .where(SplitBill.id == participant.split_bill_id)
                )
                bill = bill_result.scalar_one_or_none()
                if bill and all(p.is_paid for p in bill.participants):
                    bill.is_settled = True
                    bill.settled_date = datetime.now(timezone.utc).isoformat()

                await self.session.commit()
                await self.session.refresh(participant)
                return participant

        return None

    async def mark_bill_settled(self, bill_id: str, user_id: str) -> SplitBill | None:
        """Mark an entire split bill and all its participants as settled.

        Args:
            bill_id: The split bill ID.
            user_id: The authenticated user's ID (used for authorization).

        Returns:
            The updated :class:`SplitBill`, or ``None`` if not found.
        """
        result = await self.session.execute(
            select(SplitBill)
            .options(selectinload(SplitBill.participants))
            .where((SplitBill.id == bill_id) & (SplitBill.user_id == user_id))
        )
        bill = result.scalar_one_or_none()
        if not bill:
            return None

        now_str = datetime.now(timezone.utc).isoformat()
        for participant in bill.participants:
            if not participant.is_paid:
                participant.is_paid = True
                participant.paid_date = now_str

        bill.is_settled = True
        bill.settled_date = now_str

        await self.session.commit()
        await self.session.refresh(bill)
        return bill

    async def get_settlement_summary(self, user_id: str) -> dict:
        """Return a high-level summary of the user's settlement position.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            A dict containing ``total_owed_to_me``, ``total_i_owe``,
            ``net_position``, and ``unsettled_bills_count``.
        """
        balances = await self.calculate_net_balances(user_id)

        total_owed_to_me = sum(b["they_owe_me"] for b in balances)
        total_i_owe = sum(b["i_owe_them"] for b in balances)
        net_position = total_owed_to_me - total_i_owe

        count_result = await self.session.execute(
            select(SplitBill).where(
                (SplitBill.user_id == user_id) & (SplitBill.is_settled == False)  # noqa: E712
            )
        )
        unsettled_bills_count = len(count_result.scalars().all())

        return {
            "total_owed_to_me": total_owed_to_me,
            "total_i_owe": total_i_owe,
            "net_position": net_position,
            "unsettled_bills_count": unsettled_bills_count,
        }
