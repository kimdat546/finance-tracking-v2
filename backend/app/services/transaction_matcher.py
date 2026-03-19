"""Transaction matcher service for similarity-based merchant resolution and grouping."""

import logging
import re
from difflib import SequenceMatcher

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.matching import Alias, TransactionGroup, TransactionGroupMember
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# Common business suffixes to strip during normalization
_SUFFIX_PATTERN = re.compile(
    r"\b(co\.?,?\s*ltd\.?|ltd\.?|inc\.?|jsc\.?|corporation|corp\.?|llc\.?|plc\.?)\b",
    re.IGNORECASE,
)

# Strip anything that is not alphanumeric or whitespace
_SPECIAL_CHARS_PATTERN = re.compile(r"[^a-z0-9\s]")


def calculate_similarity(a: str, b: str) -> float:
    """Calculate text similarity ratio between two strings.

    Uses Python's SequenceMatcher algorithm to produce a ratio in the
    range [0.0, 1.0]. Comparison is case-insensitive and ignores
    leading/trailing whitespace.

    Args:
        a: First string.
        b: Second string.

    Returns:
        Similarity ratio between 0.0 (no match) and 1.0 (identical).
    """
    a_clean = a.lower().strip()
    b_clean = b.lower().strip()
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def normalize_merchant_name(name: str) -> str:
    """Normalize a merchant name for consistent comparison.

    Applies the following transformations in order:
    1. Lowercase.
    2. Remove common corporate suffixes (Co., Ltd., Inc., JSC, Corporation, Corp).
    3. Remove special characters (keeps alphanumeric and spaces only).
    4. Collapse multiple whitespace sequences into a single space and strip.

    Args:
        name: Raw merchant name.

    Returns:
        Normalized merchant name string.
    """
    result = name.lower()
    result = _SUFFIX_PATTERN.sub("", result)
    result = _SPECIAL_CHARS_PATTERN.sub("", result)
    result = re.sub(r"\s+", " ", result).strip()
    return result


def find_best_alias(
    name: str,
    aliases: list[Alias],
    threshold: float = 0.8,
) -> Alias | None:
    """Find the best matching alias for a merchant name.

    Computes similarity between *name* and each alias's ``original_name``.
    Returns the alias with the highest score that meets *threshold*, or
    ``None`` if no alias meets the threshold.

    Args:
        name: Merchant name to look up.
        aliases: List of Alias objects to search.
        threshold: Minimum similarity score (0.0-1.0) to accept a match.

    Returns:
        Best matching Alias or None.
    """
    best_alias: Alias | None = None
    best_score: float = -1.0

    for alias in aliases:
        score = calculate_similarity(name, alias.original_name)
        if score >= threshold and score > best_score:
            best_score = score
            best_alias = alias

    return best_alias


class TransactionMatcherService:
    """Service for finding and grouping similar transactions.

    Provides utilities to resolve merchant names via aliases, compute
    similarity between merchants found in the database, and manage
    transaction groups built around canonical merchant names.
    """

    DEFAULT_SIMILARITY_THRESHOLD = 0.80

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with an async database session.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    # ------------------------------------------------------------------
    # Similarity helpers
    # ------------------------------------------------------------------

    async def find_similar_merchants(
        self,
        user_id: str,
        merchant_name: str,
        threshold: float | None = None,
        limit: int = 10,
    ) -> list[tuple[str, float]]:
        """Find merchants similar to the given name.

        Queries all unique, non-null merchant names for *user_id* from the
        transactions table, calculates similarity against *merchant_name*,
        filters by *threshold* and returns the top *limit* results sorted
        by descending score.

        Args:
            user_id: Owning user's ID.
            merchant_name: Reference merchant name to compare against.
            threshold: Minimum similarity score; defaults to
                ``DEFAULT_SIMILARITY_THRESHOLD``.
            limit: Maximum number of results to return.

        Returns:
            List of ``(merchant_name, score)`` tuples sorted by score desc.
        """
        effective_threshold = (
            threshold if threshold is not None else self.DEFAULT_SIMILARITY_THRESHOLD
        )

        result = await self.session.execute(
            select(Transaction.merchant)
            .where(
                (Transaction.user_id == user_id) & (Transaction.merchant.isnot(None))
            )
            .distinct()
        )
        merchants: list[str] = [row[0] for row in result.fetchall() if row[0]]

        scored: list[tuple[str, float]] = []
        for merchant in merchants:
            score = calculate_similarity(merchant_name, merchant)
            if score >= effective_threshold:
                scored.append((merchant, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    # ------------------------------------------------------------------
    # Alias management
    # ------------------------------------------------------------------

    async def get_or_create_alias(
        self,
        user_id: str,
        original_name: str,
        canonical_name: str | None = None,
    ) -> Alias:
        """Retrieve an existing alias or create a new one.

        If *canonical_name* is ``None`` it is derived by calling
        :func:`normalize_merchant_name` on *original_name*.

        Args:
            user_id: Owning user's ID.
            original_name: Raw merchant name.
            canonical_name: Desired canonical form; auto-derived if omitted.

        Returns:
            Persisted Alias instance.
        """
        resolved_canonical = canonical_name or normalize_merchant_name(original_name)

        result = await self.session.execute(
            select(Alias).where(
                (Alias.user_id == user_id) & (Alias.original_name == original_name)
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            # Update canonical if it has changed
            if existing.canonical_name != resolved_canonical:
                existing.canonical_name = resolved_canonical
                self.session.add(existing)
                await self.session.commit()
                await self.session.refresh(existing)
            return existing

        alias = Alias(
            user_id=user_id,
            original_name=original_name,
            canonical_name=resolved_canonical,
            confidence=1.0,
            source="manual",
        )
        self.session.add(alias)
        await self.session.commit()
        await self.session.refresh(alias)
        logger.info("Created alias '%s' -> '%s' for user %s", original_name, resolved_canonical, user_id)
        return alias

    async def get_canonical_name(
        self,
        user_id: str,
        merchant_name: str,
    ) -> str:
        """Resolve a merchant name to its canonical form.

        Checks the alias table for an exact match on ``original_name``.
        Falls back to :func:`normalize_merchant_name` if no alias exists.

        Args:
            user_id: Owning user's ID.
            merchant_name: Raw merchant name to resolve.

        Returns:
            Canonical merchant name string.
        """
        result = await self.session.execute(
            select(Alias).where(
                (Alias.user_id == user_id) & (Alias.original_name == merchant_name)
            )
        )
        alias = result.scalar_one_or_none()
        if alias:
            return alias.canonical_name

        return normalize_merchant_name(merchant_name)

    async def bulk_create_aliases(
        self,
        user_id: str,
        mappings: list[dict],
    ) -> list[Alias]:
        """Bulk create or update merchant aliases.

        Each mapping dict must contain ``"original"`` and ``"canonical"`` keys.
        Existing aliases for the same ``original_name`` are updated in place.

        Args:
            user_id: Owning user's ID.
            mappings: List of ``{"original": str, "canonical": str}`` dicts.

        Returns:
            List of persisted Alias instances.
        """
        aliases: list[Alias] = []
        for mapping in mappings:
            original = mapping["original"]
            canonical = mapping["canonical"]
            alias = await self.get_or_create_alias(user_id, original, canonical)
            aliases.append(alias)
        logger.info("Bulk-created/updated %d aliases for user %s", len(aliases), user_id)
        return aliases

    async def list_aliases(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Alias], int]:
        """List merchant aliases for a user with pagination.

        Args:
            user_id: Owning user's ID.
            page: 1-based page number.
            page_size: Number of items per page.

        Returns:
            Tuple of ``(items, total_count)``.
        """
        count_result = await self.session.execute(
            select(func.count()).select_from(Alias).where(Alias.user_id == user_id)
        )
        total: int = count_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(Alias)
            .where(Alias.user_id == user_id)
            .order_by(Alias.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(result.scalars().all())
        return items, total

    # ------------------------------------------------------------------
    # Group management
    # ------------------------------------------------------------------

    async def create_transaction_group(
        self,
        user_id: str,
        name: str,
        merchant_name: str | None = None,
    ) -> TransactionGroup:
        """Create a new transaction group.

        Args:
            user_id: Owning user's ID.
            name: Human-readable display name for the group.
            merchant_name: Optional canonical merchant name for the group.

        Returns:
            Persisted TransactionGroup instance.
        """
        canonical: str | None = None
        if merchant_name:
            canonical = await self.get_canonical_name(user_id, merchant_name)

        group = TransactionGroup(
            user_id=user_id,
            name=name,
            canonical_merchant=canonical,
            transaction_count=0,
        )
        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)
        logger.info("Created transaction group '%s' (id=%s) for user %s", name, group.id, user_id)
        return group

    async def add_to_group(
        self,
        group_id: str,
        transaction_id: str,
        similarity_score: float = 1.0,
    ) -> TransactionGroupMember:
        """Add a transaction to a group.

        If the transaction is already a member of the group, the existing
        membership record is returned unchanged.

        Args:
            group_id: Target group ID.
            transaction_id: Transaction to add.
            similarity_score: Score (0.0-1.0) representing match quality.

        Returns:
            Persisted TransactionGroupMember instance.
        """
        # Return existing membership if present
        result = await self.session.execute(
            select(TransactionGroupMember).where(
                (TransactionGroupMember.group_id == group_id)
                & (TransactionGroupMember.transaction_id == transaction_id)
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        member = TransactionGroupMember(
            group_id=group_id,
            transaction_id=transaction_id,
            similarity_score=similarity_score,
        )
        self.session.add(member)

        # Increment cached count on the group
        group_result = await self.session.execute(
            select(TransactionGroup).where(TransactionGroup.id == group_id)
        )
        group = group_result.scalar_one_or_none()
        if group:
            group.transaction_count = (group.transaction_count or 0) + 1
            self.session.add(group)

        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def auto_group_by_merchant(
        self,
        user_id: str,
        merchant_name: str,
        threshold: float | None = None,
    ) -> TransactionGroup | None:
        """Find or create a group for a merchant and auto-assign similar transactions.

        Queries transactions whose ``merchant`` field matches *merchant_name*
        (or is similar enough given *threshold*), then assigns them to a
        group named after the canonical merchant. Returns ``None`` if no
        transactions are found.

        Args:
            user_id: Owning user's ID.
            merchant_name: Merchant name to group by.
            threshold: Minimum similarity score for inclusion; defaults to
                ``DEFAULT_SIMILARITY_THRESHOLD``.

        Returns:
            TransactionGroup instance, or None if no matching transactions exist.
        """
        effective_threshold = (
            threshold if threshold is not None else self.DEFAULT_SIMILARITY_THRESHOLD
        )
        canonical = await self.get_canonical_name(user_id, merchant_name)

        # Find all transactions for this user with a non-null merchant
        result = await self.session.execute(
            select(Transaction).where(
                (Transaction.user_id == user_id) & (Transaction.merchant.isnot(None))
            )
        )
        all_transactions = result.scalars().all()

        matching = [
            (t, calculate_similarity(merchant_name, t.merchant or ""))
            for t in all_transactions
            if calculate_similarity(merchant_name, t.merchant or "") >= effective_threshold
        ]

        if not matching:
            logger.info(
                "No transactions matched merchant '%s' for user %s", merchant_name, user_id
            )
            return None

        # Find or create the group
        group_result = await self.session.execute(
            select(TransactionGroup).where(
                (TransactionGroup.user_id == user_id)
                & (TransactionGroup.canonical_merchant == canonical)
            )
        )
        group = group_result.scalar_one_or_none()
        if not group:
            group = await self.create_transaction_group(
                user_id=user_id,
                name=canonical,
                merchant_name=merchant_name,
            )

        # Add each matching transaction to the group
        for transaction, score in matching:
            await self.add_to_group(group.id, transaction.id, similarity_score=score)

        await self.session.refresh(group)
        logger.info(
            "Auto-grouped %d transactions under merchant '%s' (group id=%s)",
            len(matching),
            canonical,
            group.id,
        )
        return group

    async def list_groups(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TransactionGroup], int]:
        """List transaction groups for a user with pagination.

        Args:
            user_id: Owning user's ID.
            page: 1-based page number.
            page_size: Number of items per page.

        Returns:
            Tuple of ``(items, total_count)``.
        """
        count_result = await self.session.execute(
            select(func.count())
            .select_from(TransactionGroup)
            .where(TransactionGroup.user_id == user_id)
        )
        total: int = count_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(TransactionGroup)
            .where(TransactionGroup.user_id == user_id)
            .order_by(TransactionGroup.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(result.scalars().all())
        return items, total

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    async def get_similarity_report(
        self,
        user_id: str,
        merchant_name: str,
    ) -> dict:
        """Generate a similarity report for a merchant name.

        Returns information about the normalized form, any known alias,
        and the top similar merchants found in the user's transaction history.

        Args:
            user_id: Owning user's ID.
            merchant_name: Merchant name to analyse.

        Returns:
            Dictionary with keys ``input``, ``normalized``, ``alias``,
            and ``similar_merchants``.
        """
        normalized = normalize_merchant_name(merchant_name)

        # Check alias table
        alias_result = await self.session.execute(
            select(Alias).where(
                (Alias.user_id == user_id) & (Alias.original_name == merchant_name)
            )
        )
        alias_obj = alias_result.scalar_one_or_none()
        alias_canonical: str | None = alias_obj.canonical_name if alias_obj else None

        similar = await self.find_similar_merchants(
            user_id=user_id,
            merchant_name=merchant_name,
        )

        return {
            "input": merchant_name,
            "normalized": normalized,
            "alias": alias_canonical,
            "similar_merchants": [{"name": name, "score": score} for name, score in similar],
        }
