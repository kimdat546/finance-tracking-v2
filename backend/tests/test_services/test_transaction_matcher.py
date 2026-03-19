"""Tests for the TransactionMatcherService and its helper functions."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.matching import Alias, TransactionGroup
from app.models.transaction import Transaction
from app.services.transaction_matcher import (
    TransactionMatcherService,
    calculate_similarity,
    find_best_alias,
    normalize_merchant_name,
)
from tests.conftest import create_test_user


# ---------------------------------------------------------------------------
# Pure-function tests (no DB required)
# ---------------------------------------------------------------------------


def test_calculate_similarity_identical() -> None:
    """Identical strings should yield a similarity score of 1.0."""
    assert calculate_similarity("Grab", "Grab") == 1.0


def test_calculate_similarity_different() -> None:
    """Completely different strings should yield a low similarity score."""
    score = calculate_similarity("Grab", "XYZ123")
    assert score < 0.5


def test_calculate_similarity_case_insensitive() -> None:
    """Case differences should not reduce the similarity score."""
    score = calculate_similarity("Grab", "GRAB")
    assert score == pytest.approx(1.0)


def test_normalize_merchant_removes_suffixes() -> None:
    """Common corporate suffixes should be stripped from merchant names."""
    # Various suffix forms
    assert normalize_merchant_name("Grab Co., Ltd.") == "grab"
    assert normalize_merchant_name("Vietcombank JSC") == "vietcombank"
    assert normalize_merchant_name("Apple Inc.") == "apple"
    assert normalize_merchant_name("Some Corp") == "some"
    assert normalize_merchant_name("Acme Corporation") == "acme"


def test_normalize_merchant_removes_extra_spaces() -> None:
    """Extra whitespace in merchant names should be collapsed."""
    assert normalize_merchant_name("  Grab  Food  ") == "grab food"


def test_normalize_merchant_removes_special_characters() -> None:
    """Special characters other than alphanumeric/spaces should be removed."""
    result = normalize_merchant_name("7-Eleven #42!")
    assert "#" not in result
    assert "!" not in result


def test_find_best_alias_match() -> None:
    """find_best_alias should return the alias with the highest similarity score."""
    alias_a = Alias(
        id="00000000-0000-0000-0000-000000000021",
        user_id="00000000-0000-0000-0000-000000000001",
        original_name="grab food",
        canonical_name="grab",
        confidence=1.0,
        source="manual",
    )
    alias_b = Alias(
        id="00000000-0000-0000-0000-000000000022",
        user_id="00000000-0000-0000-0000-000000000001",
        original_name="gojek ride",
        canonical_name="gojek",
        confidence=1.0,
        source="manual",
    )

    result = find_best_alias("grab food", [alias_a, alias_b], threshold=0.8)
    assert result is not None
    assert result.canonical_name == "grab"


def test_find_best_alias_below_threshold() -> None:
    """find_best_alias should return None when no alias meets the threshold."""
    alias = Alias(
        id="00000000-0000-0000-0000-000000000021",
        user_id="00000000-0000-0000-0000-000000000001",
        original_name="completely different name xyz",
        canonical_name="something",
        confidence=1.0,
        source="manual",
    )

    result = find_best_alias("grab", [alias], threshold=0.8)
    assert result is None


# ---------------------------------------------------------------------------
# Service integration tests (require test_db fixture)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_matcher_service_find_similar_empty_db(test_db: AsyncSession) -> None:
    """find_similar_merchants should return an empty list when no transactions exist."""
    service = TransactionMatcherService(test_db)
    results = await service.find_similar_merchants(
        user_id="00000000-0000-0000-0000-000000000099",
        merchant_name="Grab",
    )
    assert results == []


@pytest.mark.asyncio
async def test_matcher_service_get_canonical_no_alias(test_db: AsyncSession) -> None:
    """get_canonical_name should return the normalized form when no alias exists."""
    service = TransactionMatcherService(test_db)
    canonical = await service.get_canonical_name(
        user_id="00000000-0000-0000-0000-000000000098",
        merchant_name="Grab Co., Ltd.",
    )
    # No alias exists, so should return the normalized form
    assert canonical == normalize_merchant_name("Grab Co., Ltd.")


@pytest.mark.asyncio
async def test_matcher_service_create_alias(test_db: AsyncSession) -> None:
    """Creating an alias should persist it and allow retrieval."""
    await create_test_user(test_db, user_id="00000000-0000-0000-0000-000000000010")
    service = TransactionMatcherService(test_db)
    alias = await service.get_or_create_alias(
        user_id="00000000-0000-0000-0000-000000000010",
        original_name="VCB",
        canonical_name="Vietcombank",
    )

    assert alias.id is not None
    assert alias.original_name == "VCB"
    assert alias.canonical_name == "Vietcombank"
    assert alias.source == "manual"
    assert alias.confidence == pytest.approx(1.0)

    # Calling again should return the same record, not create a duplicate
    alias_again = await service.get_or_create_alias(
        user_id="00000000-0000-0000-0000-000000000010",
        original_name="VCB",
        canonical_name="Vietcombank",
    )
    assert alias_again.id == alias.id


@pytest.mark.asyncio
async def test_matcher_service_bulk_aliases(test_db: AsyncSession) -> None:
    """bulk_create_aliases should create all provided aliases."""
    await create_test_user(test_db, user_id="00000000-0000-0000-0000-000000000011")
    service = TransactionMatcherService(test_db)
    mappings = [
        {"original": "VCB", "canonical": "Vietcombank"},
        {"original": "MB Bank", "canonical": "Military Bank"},
        {"original": "TCB", "canonical": "Techcombank"},
    ]
    aliases = await service.bulk_create_aliases(user_id="00000000-0000-0000-0000-000000000011", mappings=mappings)

    assert len(aliases) == 3
    canonical_names = {a.canonical_name for a in aliases}
    assert canonical_names == {"Vietcombank", "Military Bank", "Techcombank"}


@pytest.mark.asyncio
async def test_matcher_service_create_group(test_db: AsyncSession) -> None:
    """create_transaction_group should persist a group with the correct attributes."""
    await create_test_user(test_db, user_id="00000000-0000-0000-0000-000000000012")
    service = TransactionMatcherService(test_db)
    group = await service.create_transaction_group(
        user_id="00000000-0000-0000-0000-000000000012",
        name="Grab rides",
        merchant_name=None,
    )

    assert group.id is not None
    assert group.name == "Grab rides"
    assert group.user_id == "00000000-0000-0000-0000-000000000012"
    assert group.transaction_count == 0


@pytest.mark.asyncio
async def test_matcher_service_list_groups(test_db: AsyncSession) -> None:
    """list_groups should return groups with correct pagination metadata."""
    user_id = "00000000-0000-0000-0000-000000000013"
    await create_test_user(test_db, user_id=user_id)
    service = TransactionMatcherService(test_db)

    # Create 3 groups
    for i in range(3):
        await service.create_transaction_group(
            user_id=user_id,
            name=f"Group {i}",
        )

    # Fetch all with generous page size
    items, total = await service.list_groups(user_id=user_id, page=1, page_size=10)
    assert total == 3
    assert len(items) == 3

    # Fetch first page of size 2
    page1, total2 = await service.list_groups(user_id=user_id, page=1, page_size=2)
    assert total2 == 3
    assert len(page1) == 2

    # Fetch second page
    page2, _ = await service.list_groups(user_id=user_id, page=2, page_size=2)
    assert len(page2) == 1

    # Groups from different users are isolated
    other_items, other_total = await service.list_groups(
        user_id="00000000-0000-0000-0000-000000000097", page=1, page_size=10
    )
    assert other_total == 0
    assert other_items == []
