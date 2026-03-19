"""Review queue service – manages transactions pending manual review."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services.pattern_learner import PatternLearner

logger = logging.getLogger(__name__)


class ReviewQueueService:
    """Manages transactions in the pending review queue."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise ReviewQueueService.

        Args:
            session: Async SQLAlchemy database session.
        """
        self.session = session

    async def add_to_review(
        self,
        transaction_id: str,
        user_id: str,
        reason: str,
        suggested_category_id: str | None = None,
        confidence: float = 0.0,
    ) -> None:
        """Mark a transaction for manual review.

        Sets needs_review=True and records the reason and optional suggestion.

        Args:
            transaction_id: ID of the transaction to review.
            user_id: Owner of the transaction.
            reason: Human-readable reason why the transaction needs review.
            suggested_category_id: Optional auto-suggested category.
            confidence: Confidence score for the suggestion (0.0–1.0).
        """
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
        )
        txn = result.scalar_one_or_none()
        if txn is None:
            logger.warning(
                "add_to_review: transaction %s not found for user %s",
                transaction_id,
                user_id,
            )
            return

        txn.needs_review = True
        txn.review_reason = reason
        txn.suggested_category_id = suggested_category_id
        txn.categorization_confidence = confidence
        self.session.add(txn)
        await self.session.flush()
        logger.info("Transaction %s added to review queue (reason=%r)", transaction_id, reason)

    async def get_review_queue(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Transaction], int]:
        """Return a paginated list of transactions awaiting review.

        Args:
            user_id: Owner's user ID.
            page: 1-based page number.
            page_size: Number of items per page.

        Returns:
            Tuple of (transactions_list, total_count).
        """
        offset = (page - 1) * page_size

        total_result = await self.session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.needs_review == True,  # noqa: E712
            )
        )
        total: int = total_result.scalar_one()

        items_result = await self.session.execute(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.needs_review == True,  # noqa: E712
            )
            .order_by(Transaction.created_at.asc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(items_result.scalars().all())
        return items, total

    async def approve_category(
        self,
        transaction_id: str,
        user_id: str,
        category_id: str,
        learn: bool = True,
    ) -> Transaction | None:
        """Approve a category for a transaction in the review queue.

        Clears the needs_review flag and optionally records the correction for
        pattern learning.

        Args:
            transaction_id: ID of the transaction to approve.
            user_id: Owner of the transaction.
            category_id: Category to assign.
            learn: Whether to feed the correction to PatternLearner.

        Returns:
            Updated Transaction, or None if not found.
        """
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
        )
        txn = result.scalar_one_or_none()
        if txn is None:
            return None

        old_category_id = txn.category_id

        txn.category_id = category_id
        txn.is_categorized = True
        txn.needs_review = False
        txn.review_reason = None
        txn.suggested_category_id = None
        txn.categorization_source = "manual"
        txn.categorization_confidence = 1.0
        self.session.add(txn)

        if learn:
            learner = PatternLearner(self.session)
            await learner.learn_from_correction(
                user_id=user_id,
                transaction_id=transaction_id,
                old_category_id=old_category_id,
                new_category_id=category_id,
                description=txn.description,
                merchant=txn.merchant,
            )

        await self.session.flush()
        logger.info("Approved category %s for transaction %s", category_id, transaction_id)
        return txn

    async def bulk_approve(
        self,
        user_id: str,
        approvals: list[dict],
    ) -> int:
        """Bulk approve categories for multiple transactions.

        Each entry in *approvals* must have keys "transaction_id" and
        "category_id". Optionally "learn" (default True).

        Args:
            user_id: Owner of all transactions.
            approvals: List of approval dicts.

        Returns:
            Number of transactions successfully approved.
        """
        approved = 0
        for item in approvals:
            txn = await self.approve_category(
                transaction_id=item["transaction_id"],
                user_id=user_id,
                category_id=item["category_id"],
                learn=item.get("learn", True),
            )
            if txn is not None:
                approved += 1
        await self.session.flush()
        logger.info("Bulk approved %d transactions for user %s", approved, user_id)
        return approved

    async def dismiss_from_review(self, transaction_id: str, user_id: str) -> bool:
        """Remove a transaction from the review queue without assigning a category.

        Args:
            transaction_id: ID of the transaction.
            user_id: Owner of the transaction.

        Returns:
            True if the transaction was found and dismissed, False otherwise.
        """
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
        )
        txn = result.scalar_one_or_none()
        if txn is None:
            return False

        txn.needs_review = False
        txn.review_reason = None
        txn.suggested_category_id = None
        self.session.add(txn)
        await self.session.flush()
        logger.info("Transaction %s dismissed from review queue", transaction_id)
        return True

    async def get_queue_stats(self, user_id: str) -> dict:
        """Return statistics about the review queue.

        Args:
            user_id: Owner's user ID.

        Returns:
            Dictionary with keys: total, low_confidence, medium_confidence,
            high_confidence, oldest_date.
        """
        total_result = await self.session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.needs_review == True,  # noqa: E712
            )
        )
        total: int = total_result.scalar_one()

        # Confidence buckets: low <0.4, medium 0.4-0.7, high >=0.7
        low_result = await self.session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.needs_review == True,  # noqa: E712
                Transaction.categorization_confidence < 0.4,
            )
        )
        low: int = low_result.scalar_one()

        high_result = await self.session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.needs_review == True,  # noqa: E712
                Transaction.categorization_confidence >= 0.7,
            )
        )
        high: int = high_result.scalar_one()
        medium = total - low - high

        # Oldest item
        oldest_result = await self.session.execute(
            select(Transaction.created_at)
            .where(
                Transaction.user_id == user_id,
                Transaction.needs_review == True,  # noqa: E712
            )
            .order_by(Transaction.created_at.asc())
            .limit(1)
        )
        oldest_row = oldest_result.scalar_one_or_none()
        oldest_date = oldest_row.isoformat() if oldest_row else None

        return {
            "total": total,
            "by_confidence": {
                "low": low,
                "medium": medium,
                "high": high,
            },
            "oldest_date": oldest_date,
        }
