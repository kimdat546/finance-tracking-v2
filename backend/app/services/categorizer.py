"""Automatic transaction categorization service."""

import logging
import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import (
    CategorizationRule,
    Transaction,
    TransactionType,
)

logger = logging.getLogger(__name__)


class CategorizerService:
    """Service for automatic transaction categorization."""

    def __init__(self, db: AsyncSession):
        """Initialize categorizer service.

        Args:
            db: Database session
        """
        self.db = db

    async def categorize_transaction(
        self,
        transaction: Transaction,
        user_id: str,
    ) -> str | None:
        """Automatically categorize a transaction.

        Args:
            transaction: Transaction to categorize
            user_id: User ID

        Returns:
            Category ID if found, None otherwise
        """
        # Get all active rules for the user and account
        result = await self.db.execute(
            select(CategorizationRule)
            .where(
                (CategorizationRule.user_id == user_id)
                & (CategorizationRule.account_id == transaction.account_id)
                & (CategorizationRule.is_active == True)
            )
            .order_by(CategorizationRule.priority.desc())
        )
        rules = result.scalars().all()

        for rule in rules:
            if self._matches_rule(transaction, rule):
                logger.info(
                    f"Transaction {transaction.id} matched rule {rule.id}: {rule.name}"
                )
                # Update rule statistics
                rule.match_count += 1
                self.db.add(rule)
                return rule.category_id

        # Try pattern-based categorization from user history
        category_id = await self._pattern_learn_categorize(transaction, user_id)
        return category_id

    async def _pattern_learn_categorize(
        self,
        transaction: Transaction,
        user_id: str,
    ) -> str | None:
        """Try to categorize based on learned patterns from user history.

        Args:
            transaction: Transaction to categorize
            user_id: User ID

        Returns:
            Category ID if found, None otherwise
        """
        # Find similar transactions from user history
        search_terms = self._extract_search_terms(transaction)

        if not search_terms:
            return None

        # Search for similar transactions that are already categorized
        for term in search_terms:
            similar_result = await self.db.execute(
                select(Transaction)
                .where(
                    (Transaction.user_id == user_id)
                    & (Transaction.account_id == transaction.account_id)
                    & (Transaction.is_categorized == True)
                    & (Transaction.category_id.isnot(None))
                    & (
                        Transaction.merchant.ilike(f"%{term}%")
                        | Transaction.description.ilike(f"%{term}%")
                    )
                )
                .limit(1)
            )
            similar_transaction = similar_result.scalar_one_or_none()

            if similar_transaction:
                logger.info(
                    f"Transaction {transaction.id} pattern-matched "
                    f"similar transaction {similar_transaction.id}"
                )
                return similar_transaction.category_id

        return None

    def _matches_rule(self, transaction: Transaction, rule: CategorizationRule) -> bool:
        """Check if transaction matches a rule.

        Args:
            transaction: Transaction to check
            rule: Categorization rule

        Returns:
            True if transaction matches rule
        """
        # Check merchant pattern
        if rule.merchant_pattern:
            if not self._pattern_matches(
                transaction.merchant or "",
                rule.merchant_pattern,
                rule.is_regex,
            ):
                return False

        # Check description pattern
        if rule.description_pattern:
            if not self._pattern_matches(
                transaction.description,
                rule.description_pattern,
                rule.is_regex,
            ):
                return False

        # Check amount range
        if rule.min_amount is not None:
            if transaction.amount < rule.min_amount:
                return False

        if rule.max_amount is not None:
            if transaction.amount > rule.max_amount:
                return False

        # Check transaction type
        if rule.transaction_type is not None:
            if transaction.type != rule.transaction_type:
                return False

        return True

    def _pattern_matches(
        self,
        text: str,
        pattern: str,
        is_regex: bool,
    ) -> bool:
        """Check if text matches pattern.

        Args:
            text: Text to check
            pattern: Pattern to match
            is_regex: Whether pattern is regex

        Returns:
            True if text matches pattern
        """
        if is_regex:
            try:
                return bool(re.search(pattern, text, re.IGNORECASE))
            except re.error:
                logger.error(f"Invalid regex pattern: {pattern}")
                return False
        else:
            return pattern.lower() in text.lower()

    def _extract_search_terms(self, transaction: Transaction) -> list[str]:
        """Extract search terms from transaction.

        Args:
            transaction: Transaction

        Returns:
            List of search terms
        """
        terms = []

        if transaction.merchant:
            # Extract first meaningful word from merchant name
            words = transaction.merchant.split()
            if words:
                terms.append(words[0])

        if transaction.description:
            # Extract first few meaningful words
            words = transaction.description.split()
            if words:
                terms.append(words[0])
            if len(words) > 1:
                terms.append(f"{words[0]} {words[1]}")

        return [term for term in terms if len(term) > 2]

    async def get_pending_categorizations(
        self,
        user_id: str,
        account_id: str | None = None,
        limit: int = 100,
    ) -> list[Transaction]:
        """Get transactions pending categorization.

        Args:
            user_id: User ID
            account_id: Optional account ID filter
            limit: Maximum number to return

        Returns:
            List of transactions pending categorization
        """
        query = select(Transaction).where(
            (Transaction.user_id == user_id) & (Transaction.is_categorized == False)
        )

        if account_id:
            query = query.where(Transaction.account_id == account_id)

        query = query.limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def batch_categorize(
        self,
        user_id: str,
        auto_apply: bool = False,
    ) -> dict[str, int]:
        """Batch categorize pending transactions.

        Args:
            user_id: User ID
            auto_apply: Whether to auto-apply categorizations

        Returns:
            Statistics about categorization
        """
        pending = await self.get_pending_categorizations(user_id)

        categorized = 0
        failed = 0

        for transaction in pending:
            try:
                category_id = await self.categorize_transaction(transaction, user_id)
                if category_id:
                    if auto_apply:
                        transaction.category_id = category_id
                        transaction.is_categorized = True
                    categorized += 1
            except Exception as e:
                logger.error(f"Error categorizing transaction {transaction.id}: {e}")
                failed += 1

        if auto_apply:
            await self.db.commit()

        return {
            "total": len(pending),
            "categorized": categorized,
            "failed": failed,
        }
