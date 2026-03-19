"""Automatic transaction categorization service with rule engine."""

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import (
    CategorizationRule,
    Transaction,
    TransactionType,
)

logger = logging.getLogger(__name__)


class RuleEngine:
    """Evaluates categorization rules against transactions."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the rule engine.

        Args:
            session: Async SQLAlchemy database session.
        """
        self.session = session

    async def get_rules_for_user(self, user_id: str) -> list[CategorizationRule]:
        """Get all active rules for a user, ordered by priority (highest first).

        Args:
            user_id: The user's ID.

        Returns:
            List of active CategorizationRule objects sorted by priority descending.
        """
        result = await self.session.execute(
            select(CategorizationRule)
            .where(
                CategorizationRule.user_id == user_id,
                CategorizationRule.is_active == True,  # noqa: E712
            )
            .order_by(CategorizationRule.priority.desc())
        )
        return list(result.scalars().all())

    async def apply_rules(
        self,
        user_id: str,
        description: str,
        merchant: str | None,
        amount: float,
    ) -> tuple[str | None, float]:
        """Apply rules to find a matching category.

        Evaluates rules in priority order (highest first). Returns the category
        from the first matching rule along with a confidence score.

        Args:
            user_id: The user's ID.
            description: Transaction description text.
            merchant: Optional merchant name.
            amount: Transaction amount.

        Returns:
            Tuple of (category_id, confidence) where confidence is 0.0–1.0.
            Returns (None, 0.0) when no rule matches.
        """
        rules = await self.get_rules_for_user(user_id)
        for rule in rules:
            matched = await self.test_rule(
                pattern=rule.pattern or "",
                match_type=rule.match_type,
                match_field=rule.match_field,
                description=description,
                merchant=merchant,
            )
            if matched:
                confidence = self._calculate_confidence(rule)
                # Update statistics
                rule.match_count = (rule.match_count or 0) + 1
                rule.last_matched_at = datetime.now(timezone.utc).isoformat()
                self.session.add(rule)
                logger.info(
                    "Rule %s matched for user %s → category %s (conf=%.2f)",
                    rule.id,
                    user_id,
                    rule.category_id,
                    confidence,
                )
                return rule.category_id, confidence

        return None, 0.0

    async def create_rule(
        self,
        user_id: str,
        name: str,
        pattern: str,
        category_id: str,
        priority: int = 50,
        match_type: str = "contains",
        match_field: str = "description",
        auto_created: bool = False,
    ) -> CategorizationRule:
        """Create a new categorization rule for the user.

        Args:
            user_id: The user's ID.
            name: Human-readable rule name.
            pattern: The matching pattern string.
            category_id: The category to assign when this rule matches.
            priority: Rule priority (0–100). Higher values are evaluated first.
            match_type: One of "contains", "regex", "startswith", "exact".
            match_field: One of "description", "merchant", "any".
            auto_created: Whether this rule was auto-created by the learner.

        Returns:
            The newly created CategorizationRule instance.
        """
        rule = CategorizationRule(
            user_id=user_id,
            name=name,
            pattern=pattern,
            category_id=category_id,
            priority=priority,
            match_type=match_type,
            match_field=match_field,
            is_active=True,
            is_regex=(match_type == "regex"),
            match_count=0,
            auto_created=auto_created,
        )
        self.session.add(rule)
        await self.session.flush()
        logger.info("Created rule %s for user %s", rule.id, user_id)
        return rule

    async def test_rule(
        self,
        pattern: str,
        match_type: str,
        match_field: str,
        description: str,
        merchant: str | None = None,
    ) -> bool:
        """Test whether a rule pattern matches given transaction data.

        Args:
            pattern: The pattern to test.
            match_type: One of "contains", "regex", "startswith", "exact".
            match_field: One of "description", "merchant", "any".
            description: Transaction description to test against.
            merchant: Optional merchant name to test against.

        Returns:
            True if the pattern matches the specified field(s).
        """
        if not pattern:
            return False

        candidates: list[str] = []
        if match_field == "description":
            candidates = [description]
        elif match_field == "merchant":
            candidates = [merchant] if merchant else []
        else:  # "any"
            candidates = [description]
            if merchant:
                candidates.append(merchant)

        for text in candidates:
            if self._pattern_matches(text, pattern, match_type):
                return True
        return False

    async def get_matching_rules(
        self,
        user_id: str,
        description: str,
        merchant: str | None,
    ) -> list[tuple[CategorizationRule, float]]:
        """Get all matching rules with confidence scores, sorted by priority.

        Args:
            user_id: The user's ID.
            description: Transaction description.
            merchant: Optional merchant name.

        Returns:
            List of (CategorizationRule, confidence) tuples ordered by priority descending.
        """
        rules = await self.get_rules_for_user(user_id)
        matches: list[tuple[CategorizationRule, float]] = []
        for rule in rules:
            matched = await self.test_rule(
                pattern=rule.pattern or "",
                match_type=rule.match_type,
                match_field=rule.match_field,
                description=description,
                merchant=merchant,
            )
            if matched:
                matches.append((rule, self._calculate_confidence(rule)))
        return matches

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _pattern_matches(self, text: str, pattern: str, match_type: str) -> bool:
        """Check whether *text* matches *pattern* according to *match_type*.

        Args:
            text: The text to search within.
            pattern: The pattern to look for.
            match_type: Matching strategy.

        Returns:
            True if the text matches the pattern.
        """
        text_lower = text.lower()
        pattern_lower = pattern.lower()

        if match_type == "regex":
            try:
                return bool(re.search(pattern, text, re.IGNORECASE))
            except re.error:
                logger.warning("Invalid regex pattern: %s", pattern)
                return False
        elif match_type == "startswith":
            return text_lower.startswith(pattern_lower)
        elif match_type == "exact":
            return text_lower == pattern_lower
        else:  # "contains" (default)
            return pattern_lower in text_lower

    def _calculate_confidence(self, rule: CategorizationRule) -> float:
        """Calculate confidence score for a matched rule.

        Rules with a higher priority and more historical matches receive
        a higher confidence score.

        Args:
            rule: The matched rule.

        Returns:
            Confidence value between 0.0 and 1.0.
        """
        base = 0.7
        # Boost for high-priority rules (priority 0–100)
        priority_boost = min((rule.priority or 0) / 100.0, 1.0) * 0.2
        # Boost for rules with many matches (up to 0.1)
        match_boost = min((rule.match_count or 0) / 100.0, 1.0) * 0.1
        return round(min(base + priority_boost + match_boost, 1.0), 3)


# ---------------------------------------------------------------------------
# Legacy service kept for backward compatibility with existing code
# ---------------------------------------------------------------------------


class CategorizerService:
    """Service for automatic transaction categorization (legacy API)."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize categorizer service.

        Args:
            db: Database session.
        """
        self.db = db
        self._engine = RuleEngine(db)

    async def categorize_transaction(
        self,
        transaction: Transaction,
        user_id: str,
    ) -> str | None:
        """Automatically categorize a transaction.

        Args:
            transaction: Transaction to categorize.
            user_id: User ID.

        Returns:
            Category ID if found, None otherwise.
        """
        category_id, _confidence = await self._engine.apply_rules(
            user_id=user_id,
            description=transaction.description,
            merchant=transaction.merchant,
            amount=float(transaction.amount),
        )
        if category_id:
            return category_id

        # Fallback: pattern-based categorization from user history
        return await self._pattern_learn_categorize(transaction, user_id)

    async def _pattern_learn_categorize(
        self,
        transaction: Transaction,
        user_id: str,
    ) -> str | None:
        """Try to categorize based on learned patterns from user history.

        Args:
            transaction: Transaction to categorize.
            user_id: User ID.

        Returns:
            Category ID if found, None otherwise.
        """
        search_terms = self._extract_search_terms(transaction)
        if not search_terms:
            return None

        for term in search_terms:
            similar_result = await self.db.execute(
                select(Transaction)
                .where(
                    Transaction.user_id == user_id,
                    Transaction.account_id == transaction.account_id,
                    Transaction.is_categorized == True,  # noqa: E712
                    Transaction.category_id.isnot(None),
                    (
                        Transaction.merchant.ilike(f"%{term}%")
                        | Transaction.description.ilike(f"%{term}%")
                    ),
                )
                .limit(1)
            )
            similar_transaction = similar_result.scalar_one_or_none()
            if similar_transaction:
                logger.info(
                    "Transaction %s pattern-matched similar transaction %s",
                    transaction.id,
                    similar_transaction.id,
                )
                return similar_transaction.category_id

        return None

    def _extract_search_terms(self, transaction: Transaction) -> list[str]:
        """Extract search terms from transaction.

        Args:
            transaction: Transaction.

        Returns:
            List of search terms.
        """
        terms: list[str] = []
        if transaction.merchant:
            words = transaction.merchant.split()
            if words:
                terms.append(words[0])
        if transaction.description:
            words = transaction.description.split()
            if words:
                terms.append(words[0])
            if len(words) > 1:
                terms.append(f"{words[0]} {words[1]}")
        return [t for t in terms if len(t) > 2]

    async def get_pending_categorizations(
        self,
        user_id: str,
        account_id: str | None = None,
        limit: int = 100,
    ) -> list[Transaction]:
        """Get transactions pending categorization.

        Args:
            user_id: User ID.
            account_id: Optional account ID filter.
            limit: Maximum number to return.

        Returns:
            List of transactions pending categorization.
        """
        query = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.is_categorized == False,  # noqa: E712
        )
        if account_id:
            query = query.where(Transaction.account_id == account_id)
        query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def batch_categorize(
        self,
        user_id: str,
        auto_apply: bool = False,
    ) -> dict[str, int]:
        """Batch categorize pending transactions.

        Args:
            user_id: User ID.
            auto_apply: Whether to auto-apply categorizations.

        Returns:
            Statistics about categorization.
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
            except Exception as exc:
                logger.error("Error categorizing transaction %s: %s", transaction.id, exc)
                failed += 1

        if auto_apply:
            await self.db.commit()

        return {
            "total": len(pending),
            "categorized": categorized,
            "failed": failed,
        }
