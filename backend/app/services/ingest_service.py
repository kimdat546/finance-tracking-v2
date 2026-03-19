"""Service for ingesting client-parsed transactions into the database."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionType
from app.schemas.ingest import ParsedTransactionInput

logger = logging.getLogger(__name__)


class IngestService:
    """Ingests parsed transactions into the database."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The async SQLAlchemy session.
        """
        self.session = session

    async def ingest_transactions(
        self,
        user_id: str,
        account_id: str,
        transactions: list[ParsedTransactionInput],
    ) -> tuple[int, int, list[str]]:
        """Ingest a list of parsed transactions.

        Skips duplicates detected by reference_id + user_id (when reference_id
        is present) or by amount + direction + transaction_date + user_id.

        Args:
            user_id: Owner of the transactions.
            account_id: Account to attach transactions to.
            transactions: List of parsed transaction inputs.

        Returns:
            Tuple of (created_count, skipped_count, error_messages).
        """
        created = 0
        skipped = 0
        errors: list[str] = []

        for tx_input in transactions:
            try:
                # Duplicate check by reference_id when available
                if tx_input.reference_id:
                    existing = await self.session.execute(
                        select(Transaction).where(
                            Transaction.user_id == user_id,
                            Transaction.source_id == tx_input.reference_id,
                        )
                    )
                    if existing.scalar_one_or_none():
                        skipped += 1
                        continue

                # Map direction to TransactionType
                if tx_input.direction == "incoming":
                    tx_type = TransactionType.INCOME
                else:
                    tx_type = TransactionType.EXPENSE

                # Parse date
                tx_date = tx_input.transaction_date or datetime.now(timezone.utc).date().isoformat()

                transaction = Transaction(
                    user_id=user_id,
                    account_id=account_id,
                    amount=tx_input.amount,
                    currency=tx_input.currency,
                    type=tx_type,
                    description=tx_input.description,
                    merchant=tx_input.merchant,
                    transaction_date=tx_date,
                    source=tx_input.source,
                    source_id=tx_input.reference_id,
                    categorization_confidence=tx_input.confidence,
                    categorization_source=tx_input.source,
                )
                self.session.add(transaction)
                created += 1

            except Exception as exc:
                msg = f"Error ingesting transaction '{tx_input.description}': {exc}"
                logger.error(msg)
                errors.append(msg)

        if created:
            await self.session.commit()

        return created, skipped, errors

    async def ingest_email(
        self,
        user_id: str,
        account_id: str,
        email_body: str,
        sender: str = "",
        subject: str = "",
    ) -> tuple[int, list[str]]:
        """Parse an email server-side using the registry, then ingest.

        Args:
            user_id: Owner of the transaction.
            account_id: Account to attach the transaction to.
            email_body: Raw email HTML or plain-text body.
            sender: Email sender address.
            subject: Email subject line.

        Returns:
            Tuple of (created_count, error_messages).
        """
        from app.parsers.registry import registry

        parser = await registry.find_parser_for_email(sender, subject)
        if not parser:
            return 0, [f"No parser found for sender={sender!r}, subject={subject!r}"]

        result = await parser.parse(email_body)
        if not result:
            return 0, ["Parser returned no transaction"]

        tx = ParsedTransactionInput(
            amount=result.amount,
            currency=result.currency,
            description=result.description,
            direction=result.direction.value,
            merchant=result.merchant,
            transaction_date=result.transaction_date,
            reference_id=result.reference_id,
            source="server_parser",
            confidence=result.confidence,
        )
        created, _, errors = await self.ingest_transactions(user_id, account_id, [tx])
        return created, errors
