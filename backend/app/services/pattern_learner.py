"""Pattern learning service – learns categorization patterns from user corrections."""

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Category, CategorizationRule, Transaction
from app.services.categorizer import RuleEngine

logger = logging.getLogger(__name__)

# Vietnamese + English stop-words used during keyword extraction
STOP_WORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "cua",
        "va",
        "la",
        "o",
        "de",
        "tai",
        "hang",
        "khong",
        "tu",
        "cho",
        "co",
        "toi",
    }
)

# Minimum number of corroborating transactions before auto-creating a rule
AUTO_RULE_THRESHOLD = 3


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from free-form text.

    Lowercases the input, strips punctuation, and removes stop-words.

    Args:
        text: Raw text (description or merchant name).

    Returns:
        List of keyword strings.
    """
    import re

    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    words = [w for w in cleaned.split() if w not in STOP_WORDS and len(w) > 2]
    return words[:10]


def _keyword_similarity(kw1: list[str], kw2: list[str]) -> float:
    """Compute Jaccard similarity between two keyword lists.

    Args:
        kw1: First keyword list.
        kw2: Second keyword list.

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    s1, s2 = set(kw1), set(kw2)
    if not s1 and not s2:
        return 0.0
    intersection = len(s1 & s2)
    union = len(s1 | s2)
    return intersection / union if union else 0.0


class PatternLearner:
    """Learns categorization patterns from user corrections and history."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise PatternLearner.

        Args:
            session: Async SQLAlchemy database session.
        """
        self.session = session
        self._rule_engine = RuleEngine(session)

    async def learn_from_correction(
        self,
        user_id: str,
        transaction_id: str,
        old_category_id: str | None,
        new_category_id: str,
        description: str,
        merchant: str | None,
    ) -> CategorizationRule | None:
        """Learn from a user's manual category correction.

        Counts how many times the same merchant has been assigned
        *new_category_id*. When the count reaches AUTO_RULE_THRESHOLD a
        "merchant" → "exact" rule is auto-created so future transactions are
        categorized automatically.

        Args:
            user_id: The user's ID.
            transaction_id: ID of the corrected transaction (for logging).
            old_category_id: Previous category (may be None).
            new_category_id: Category chosen by the user.
            description: Transaction description text.
            merchant: Optional merchant name.

        Returns:
            The newly created CategorizationRule, or None if the threshold
            has not been reached yet.
        """
        logger.info(
            "Learning correction for user %s: txn=%s  %s → %s",
            user_id,
            transaction_id,
            old_category_id,
            new_category_id,
        )

        # We can only create a merchant-based rule when the merchant is known
        if not merchant:
            return None

        # Count categorized transactions for this user+merchant+category
        count_result = await self.session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.merchant == merchant,
                Transaction.category_id == new_category_id,
                Transaction.is_categorized == True,  # noqa: E712
            )
        )
        count: int = count_result.scalar_one()

        if count < AUTO_RULE_THRESHOLD:
            logger.debug(
                "Not enough corroborating transactions yet (%d/%d) for merchant '%s'",
                count,
                AUTO_RULE_THRESHOLD,
                merchant,
            )
            return None

        # Check whether a matching rule already exists to avoid duplicates
        existing_result = await self.session.execute(
            select(CategorizationRule).where(
                CategorizationRule.user_id == user_id,
                CategorizationRule.pattern == merchant,
                CategorizationRule.match_field == "merchant",
                CategorizationRule.match_type == "contains",
                CategorizationRule.category_id == new_category_id,
                CategorizationRule.is_active == True,  # noqa: E712
            )
        )
        if existing_result.scalar_one_or_none():
            logger.debug("Matching rule already exists for merchant '%s'", merchant)
            return None

        # Auto-create a rule
        rule = await self._rule_engine.create_rule(
            user_id=user_id,
            name=f"Auto: {merchant}",
            pattern=merchant,
            category_id=new_category_id,
            priority=30,
            match_type="contains",
            match_field="merchant",
            auto_created=True,
        )
        logger.info(
            "Auto-created rule %s for merchant '%s' → category %s",
            rule.id,
            merchant,
            new_category_id,
        )
        return rule

    async def get_category_suggestion(
        self,
        user_id: str,
        description: str,
        merchant: str | None,
        amount: float | None = None,
    ) -> tuple[str | None, float]:
        """Suggest a category based on historical patterns.

        Strategy (in order):
        1. Exact merchant match – find most-used category for this merchant.
        2. Fuzzy merchant match (>80% Jaccard keyword similarity).
        3. Description pattern match.

        Args:
            user_id: The user's ID.
            description: Transaction description.
            merchant: Optional merchant name.
            amount: Optional transaction amount (not currently used in scoring).

        Returns:
            Tuple of (category_id, confidence). Returns (None, 0.0) when no
            suggestion can be made.
        """
        # 1. Exact merchant match
        if merchant:
            cat_id, conf = await self._exact_merchant_suggestion(user_id, merchant)
            if cat_id:
                return cat_id, conf

        # 2. Fuzzy merchant match
        if merchant:
            cat_id, conf = await self._fuzzy_merchant_suggestion(user_id, merchant)
            if cat_id:
                return cat_id, conf

        # 3. Description-based pattern match
        cat_id, conf = await self._description_suggestion(user_id, description)
        if cat_id:
            return cat_id, conf

        return None, 0.0

    async def get_learning_stats(self, user_id: str) -> dict:
        """Return statistics about auto-learned patterns.

        Args:
            user_id: The user's ID.

        Returns:
            Dictionary with keys: rules_created, total_active_rules,
            auto_categorized_count, manual_count.
        """
        auto_rules_result = await self.session.execute(
            select(func.count())
            .select_from(CategorizationRule)
            .where(
                CategorizationRule.user_id == user_id,
                CategorizationRule.auto_created == True,  # noqa: E712
                CategorizationRule.is_active == True,  # noqa: E712
            )
        )
        auto_rules: int = auto_rules_result.scalar_one()

        total_rules_result = await self.session.execute(
            select(func.count())
            .select_from(CategorizationRule)
            .where(
                CategorizationRule.user_id == user_id,
                CategorizationRule.is_active == True,  # noqa: E712
            )
        )
        total_rules: int = total_rules_result.scalar_one()

        auto_cat_result = await self.session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.categorization_source == "rule",
                Transaction.is_categorized == True,  # noqa: E712
            )
        )
        auto_categorized: int = auto_cat_result.scalar_one()

        manual_result = await self.session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.categorization_source == "manual",
                Transaction.is_categorized == True,  # noqa: E712
            )
        )
        manual: int = manual_result.scalar_one()

        return {
            "auto_rules_created": auto_rules,
            "total_active_rules": total_rules,
            "auto_categorized_count": auto_categorized,
            "manual_count": manual,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _exact_merchant_suggestion(
        self, user_id: str, merchant: str
    ) -> tuple[str | None, float]:
        """Find the most-used category for an exact merchant name."""
        result = await self.session.execute(
            select(Transaction.category_id, func.count().label("cnt"))
            .where(
                Transaction.user_id == user_id,
                Transaction.merchant == merchant,
                Transaction.category_id.isnot(None),
                Transaction.is_categorized == True,  # noqa: E712
            )
            .group_by(Transaction.category_id)
            .order_by(func.count().desc())
            .limit(1)
        )
        row = result.first()
        if row and row.cnt >= 1:
            confidence = min(0.5 + row.cnt * 0.05, 0.95)
            return row.category_id, round(confidence, 3)
        return None, 0.0

    async def _fuzzy_merchant_suggestion(
        self, user_id: str, merchant: str
    ) -> tuple[str | None, float]:
        """Find a category from a fuzzy merchant name match (>80% similarity)."""
        query_kw = _extract_keywords(merchant)
        if not query_kw:
            return None, 0.0

        # Load a sample of recent categorized merchants for this user
        result = await self.session.execute(
            select(Transaction.merchant, Transaction.category_id)
            .where(
                Transaction.user_id == user_id,
                Transaction.merchant.isnot(None),
                Transaction.category_id.isnot(None),
                Transaction.is_categorized == True,  # noqa: E712
            )
            .limit(200)
        )
        rows = result.all()

        best_sim = 0.0
        best_cat: str | None = None
        for row in rows:
            if not row.merchant:
                continue
            sim = _keyword_similarity(query_kw, _extract_keywords(row.merchant))
            if sim > best_sim:
                best_sim = sim
                best_cat = row.category_id

        if best_sim >= 0.8 and best_cat:
            return best_cat, round(best_sim * 0.9, 3)
        return None, 0.0

    async def _description_suggestion(
        self, user_id: str, description: str
    ) -> tuple[str | None, float]:
        """Suggest a category from historical description patterns."""
        query_kw = _extract_keywords(description)
        if not query_kw:
            return None, 0.0

        result = await self.session.execute(
            select(Transaction.description, Transaction.category_id)
            .where(
                Transaction.user_id == user_id,
                Transaction.category_id.isnot(None),
                Transaction.is_categorized == True,  # noqa: E712
            )
            .limit(200)
        )
        rows = result.all()

        best_sim = 0.0
        best_cat: str | None = None
        for row in rows:
            if not row.description:
                continue
            sim = _keyword_similarity(query_kw, _extract_keywords(row.description))
            if sim > best_sim:
                best_sim = sim
                best_cat = row.category_id

        if best_sim >= 0.5 and best_cat:
            return best_cat, round(best_sim * 0.7, 3)
        return None, 0.0
