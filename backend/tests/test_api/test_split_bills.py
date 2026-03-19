"""Tests for the split bills and contacts API."""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import Contact, SplitGroup
from app.models.system import User
from app.schemas.social import (
    ContactCreateRequest,
    SplitBillCreateRequest,
    SplitParticipantInput,
)
from app.services.settlement_service import SettlementService
from app.services.split_bill_service import SplitBillService
from tests.conftest import create_test_user

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_USER_ID = "00000000-0000-0000-0000-000000000002"


@pytest_asyncio.fixture
async def split_test_user(test_db: AsyncSession) -> User:
    """Create the test user required by FK constraints."""
    return await create_test_user(test_db, user_id=USER_ID)


@pytest_asyncio.fixture
async def user_contact(test_db: AsyncSession, split_test_user: User) -> Contact:
    """Create a contact for the test user (acts as 'myself' / payer)."""
    contact = Contact(user_id=USER_ID, name="Nguyễn Văn A", phone="0901234567")
    test_db.add(contact)
    await test_db.commit()
    await test_db.refresh(contact)
    return contact


@pytest_asyncio.fixture
async def friend_contact(test_db: AsyncSession, split_test_user: User) -> Contact:
    """Create a friend contact for the test user."""
    contact = Contact(user_id=USER_ID, name="Trần Thị B", email="b@example.com")
    test_db.add(contact)
    await test_db.commit()
    await test_db.refresh(contact)
    return contact


@pytest_asyncio.fixture
async def split_group(test_db: AsyncSession, split_test_user: User) -> SplitGroup:
    """Create a split group for the test user."""
    group = SplitGroup(user_id=USER_ID, name="Nhóm bạn bè")
    test_db.add(group)
    await test_db.commit()
    await test_db.refresh(group)
    return group


# ---------------------------------------------------------------------------
# Contact tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_contact(test_db: AsyncSession, split_test_user: User) -> None:
    """Creating a contact stores it in the database."""
    contact = Contact(
        user_id=USER_ID,
        name="Lê Văn C",
        phone="0912345678",
        email="c@example.com",
        notes="Bạn thân",
    )
    test_db.add(contact)
    await test_db.commit()
    await test_db.refresh(contact)

    assert contact.id is not None
    assert contact.name == "Lê Văn C"
    assert contact.phone == "0912345678"
    assert contact.email == "c@example.com"
    assert contact.notes == "Bạn thân"
    assert contact.user_id == USER_ID


@pytest.mark.asyncio
async def test_list_contacts_empty(test_db: AsyncSession) -> None:
    """A user with no contacts gets an empty list."""
    from sqlalchemy import select

    result = await test_db.execute(
        select(Contact).where(Contact.user_id == "00000000-0000-0000-0000-000000000099")
    )
    contacts = result.scalars().all()
    assert contacts == []


# ---------------------------------------------------------------------------
# Split bill tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_split_bill_even_split(
    test_db: AsyncSession,
    user_contact: Contact,
    friend_contact: Contact,
) -> None:
    """Creating a split bill with all-zero shares auto-calculates an even split."""
    service = SplitBillService(test_db)
    data = SplitBillCreateRequest(
        title="Bữa ăn tối",
        total_amount=Decimal("300000"),
        payer_contact_id=user_contact.id,
        splits=[
            SplitParticipantInput(
                contact_id=user_contact.id,
                share_amount=Decimal("0"),
            ),
            SplitParticipantInput(
                contact_id=friend_contact.id,
                share_amount=Decimal("0"),
            ),
        ],
    )
    bill = await service.create_bill(USER_ID, data)

    assert bill is not None
    assert bill.name == "Bữa ăn tối"
    assert bill.total_amount == Decimal("300000")
    assert len(bill.participants) == 2

    for participant in bill.participants:
        assert participant.share_amount == Decimal("150000.00")


@pytest.mark.asyncio
async def test_create_split_bill_custom_amounts(
    test_db: AsyncSession,
    user_contact: Contact,
    friend_contact: Contact,
) -> None:
    """Creating a split bill with explicit amounts records them correctly."""
    service = SplitBillService(test_db)
    data = SplitBillCreateRequest(
        title="Tiền taxi",
        total_amount=Decimal("200000"),
        payer_contact_id=user_contact.id,
        splits=[
            SplitParticipantInput(
                contact_id=user_contact.id,
                share_amount=Decimal("120000"),
            ),
            SplitParticipantInput(
                contact_id=friend_contact.id,
                share_amount=Decimal("80000"),
            ),
        ],
    )
    bill = await service.create_bill(USER_ID, data)

    assert bill is not None
    amount_map = {p.contact_id: p.share_amount for p in bill.participants}
    assert amount_map[user_contact.id] == Decimal("120000")
    assert amount_map[friend_contact.id] == Decimal("80000")


@pytest.mark.asyncio
async def test_settle_participant(
    test_db: AsyncSession,
    user_contact: Contact,
    friend_contact: Contact,
) -> None:
    """Settling a participant marks them as paid."""
    service = SplitBillService(test_db)
    data = SplitBillCreateRequest(
        title="Cà phê",
        total_amount=Decimal("100000"),
        payer_contact_id=user_contact.id,
        splits=[
            SplitParticipantInput(
                contact_id=user_contact.id,
                share_amount=Decimal("50000"),
            ),
            SplitParticipantInput(
                contact_id=friend_contact.id,
                share_amount=Decimal("50000"),
            ),
        ],
    )
    bill = await service.create_bill(USER_ID, data)

    # Settle friend's portion
    updated = await service.settle_participant(bill.id, friend_contact.id, 50000.0)

    assert updated is not None
    assert updated.is_paid is True
    assert updated.paid_date is not None

    # Reload bill and confirm overall status
    refreshed = await service.get_bill_with_participants(bill.id)
    assert refreshed is not None
    settled_count = sum(1 for p in refreshed.participants if p.is_paid)
    # Only friend_contact settled
    assert settled_count == 1


# ---------------------------------------------------------------------------
# Balance / summary tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_net_balances_empty(test_db: AsyncSession) -> None:
    """A user with no bills has empty net balances."""
    service = SettlementService(test_db)
    balances = await service.calculate_net_balances("00000000-0000-0000-0000-000000000098")
    assert balances == []


@pytest.mark.asyncio
async def test_settlement_summary_structure(test_db: AsyncSession) -> None:
    """Settlement summary returns a dict with the expected keys."""
    service = SettlementService(test_db)
    summary = await service.get_settlement_summary("00000000-0000-0000-0000-000000000098")

    expected_keys = {"total_owed_to_me", "total_i_owe", "net_position", "unsettled_bills_count"}
    assert set(summary.keys()) == expected_keys
    assert summary["unsettled_bills_count"] == 0
    assert summary["net_position"] == Decimal("0")
