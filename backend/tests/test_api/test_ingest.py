"""Tests for the transaction ingest API."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Account, Category, Transaction
from app.schemas.ingest import ParsedTransactionInput
from app.services.ingest_service import IngestService
from tests.conftest import create_test_user

USER_ID = "00000000-0000-0000-0000-000000000010"
ACCOUNT_ID = "00000000-0000-0000-0000-000000000011"


@pytest_asyncio.fixture
async def account(test_db: AsyncSession) -> Account:
    await create_test_user(test_db, user_id=USER_ID)
    acct = Account(
        user_id=USER_ID,
        name="Test Bank",
        account_type="checking",
        currency="VND",
        balance=1_000_000,
    )
    test_db.add(acct)
    await test_db.commit()
    await test_db.refresh(acct)
    return acct


@pytest.mark.asyncio
async def test_ingest_single_expense(test_db: AsyncSession, account: Account) -> None:
    svc = IngestService(test_db)
    tx = ParsedTransactionInput(
        amount=500_000,
        currency="VND",
        description="Mua cà phê",
        direction="outgoing",
        merchant="Starbucks",
        transaction_date="2026-03-15",
        reference_id="REF-001",
        source="client_parser",
        confidence=0.95,
    )
    created, skipped, errors = await svc.ingest_transactions(USER_ID, account.id, [tx])
    assert created == 1
    assert skipped == 0
    assert errors == []


@pytest.mark.asyncio
async def test_ingest_deduplicates_by_reference_id(test_db: AsyncSession, account: Account) -> None:
    svc = IngestService(test_db)
    tx = ParsedTransactionInput(
        amount=100_000,
        currency="VND",
        description="Duplicate test",
        direction="outgoing",
        reference_id="REF-DUP-001",
        source="client_parser",
        confidence=1.0,
    )
    created1, skipped1, _ = await svc.ingest_transactions(USER_ID, account.id, [tx])
    created2, skipped2, _ = await svc.ingest_transactions(USER_ID, account.id, [tx])

    assert created1 == 1
    assert skipped1 == 0
    assert created2 == 0
    assert skipped2 == 1


@pytest.mark.asyncio
async def test_ingest_income_direction(test_db: AsyncSession, account: Account) -> None:
    from app.models.transaction import TransactionType
    from sqlalchemy import select

    svc = IngestService(test_db)
    tx = ParsedTransactionInput(
        amount=8_000_000,
        currency="VND",
        description="Lương tháng 3",
        direction="incoming",
        reference_id="SALARY-MAR",
        source="client_parser",
        confidence=1.0,
    )
    await svc.ingest_transactions(USER_ID, account.id, [tx])

    result = await test_db.execute(
        select(Transaction).where(Transaction.source_id == "SALARY-MAR")
    )
    saved = result.scalar_one()
    assert saved.type == TransactionType.INCOME
    assert float(saved.amount) == 8_000_000


@pytest.mark.asyncio
async def test_ingest_multiple_transactions(test_db: AsyncSession, account: Account) -> None:
    svc = IngestService(test_db)
    txs = [
        ParsedTransactionInput(
            amount=200_000 * (i + 1),
            currency="VND",
            description=f"TX {i}",
            direction="outgoing",
            reference_id=f"MULTI-{i}",
            source="client_parser",
            confidence=0.9,
        )
        for i in range(5)
    ]
    created, skipped, errors = await svc.ingest_transactions(USER_ID, account.id, txs)
    assert created == 5
    assert skipped == 0
    assert errors == []


@pytest.mark.asyncio
async def test_ingest_email_no_parser(test_db: AsyncSession, account: Account) -> None:
    svc = IngestService(test_db)
    created, errors = await svc.ingest_email(
        USER_ID,
        account.id,
        "random body",
        sender="unknown@unknown.com",
        subject="nothing",
    )
    assert created == 0
    assert len(errors) == 1
    assert "No parser found" in errors[0]
