"""Split Bills API endpoints - groups, bills, settlement, and balances."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.social import Contact, SplitBill, SplitGroup, SplitParticipant
from app.schemas.social import (
    AddGroupMemberRequest,
    NetBalanceSchema,
    PendingReminderSchema,
    SettleParticipantRequest,
    SettlementSummarySchema,
    SplitBillCreateRequest,
    SplitBillListResponse,
    SplitBillSchema,
    SplitBillUpdateRequest,
    SplitGroupCreateRequest,
    SplitGroupListResponse,
    SplitGroupSchema,
    SplitGroupUpdateRequest,
    SplitParticipantSchema,
)
from app.services.reminder_service import ReminderService
from app.services.settlement_service import SettlementService
from app.services.split_bill_service import SplitBillService

router = APIRouter(prefix="/split-bills", tags=["split-bills"])


# ---------------------------------------------------------------------------
# Helper: serialise a SplitBill ORM object to SplitBillSchema
# ---------------------------------------------------------------------------


def _serialize_bill(bill: SplitBill) -> SplitBillSchema:
    """Convert a :class:`SplitBill` ORM instance to :class:`SplitBillSchema`."""
    participants_data = []
    for p in bill.participants:
        contact_name = p.contact.name if p.contact else p.contact_id
        paid_amount = p.share_amount if p.is_paid else Decimal("0.00")
        participants_data.append(
            SplitParticipantSchema(
                contact_id=p.contact_id,
                contact_name=contact_name,
                share_amount=p.share_amount,
                paid_amount=paid_amount,
                is_settled=p.is_paid,
            )
        )

    # Determine status
    total_p = len(participants_data)
    settled_p = sum(1 for p in participants_data if p.is_settled)
    if total_p == 0 or settled_p == 0:
        status = "pending"
    elif settled_p == total_p:
        status = "settled"
    else:
        status = "partial"

    return SplitBillSchema(
        id=bill.id,
        title=bill.name,
        total_amount=bill.total_amount,
        payer_contact_id=bill.payer_contact_id,
        status=status,
        participants=participants_data,
        notes=bill.description,
        created_at=bill.created_at,
    )


# ---------------------------------------------------------------------------
# Split Bill Groups
# ---------------------------------------------------------------------------


@router.get("/groups", response_model=SplitGroupListResponse)
async def list_groups(
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> SplitGroupListResponse:
    """List all split groups for a user (paginated)."""
    base_where = SplitGroup.user_id == user_id
    count_result = await db.execute(
        select(func.count()).select_from(SplitGroup).where(base_where)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(SplitGroup)
        .options(selectinload(SplitGroup.split_bills).selectinload(SplitBill.participants))
        .where(base_where)
        .order_by(SplitGroup.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    groups = result.scalars().all()

    items = []
    for g in groups:
        # Count unique contacts across all bills in the group
        contact_ids: set[str] = set()
        total_amount = Decimal("0.00")
        for bill in g.split_bills:
            total_amount += bill.total_amount
            for p in bill.participants:
                contact_ids.add(p.contact_id)

        items.append(
            SplitGroupSchema(
                id=g.id,
                name=g.name,
                description=g.description,
                member_count=len(contact_ids),
                total_amount=total_amount,
                created_at=g.created_at,
            )
        )

    total_pages = max(1, (total + page_size - 1) // page_size)
    return SplitGroupListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.post("/groups", response_model=SplitGroupSchema, status_code=201)
async def create_group(
    data: SplitGroupCreateRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> SplitGroupSchema:
    """Create a new split group."""
    group = SplitGroup(
        user_id=user_id,
        name=data.name,
        description=data.description,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)

    return SplitGroupSchema(
        id=group.id,
        name=group.name,
        description=group.description,
        member_count=len(data.contact_ids),
        total_amount=Decimal("0.00"),
        created_at=group.created_at,
    )


@router.get("/groups/{group_id}", response_model=SplitGroupSchema)
async def get_group(
    group_id: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> SplitGroupSchema:
    """Get a split group with its member count and total amount."""
    result = await db.execute(
        select(SplitGroup)
        .options(selectinload(SplitGroup.split_bills).selectinload(SplitBill.participants))
        .where((SplitGroup.id == group_id) & (SplitGroup.user_id == user_id))
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Split group not found")

    contact_ids: set[str] = set()
    total_amount = Decimal("0.00")
    for bill in group.split_bills:
        total_amount += bill.total_amount
        for p in bill.participants:
            contact_ids.add(p.contact_id)

    return SplitGroupSchema(
        id=group.id,
        name=group.name,
        description=group.description,
        member_count=len(contact_ids),
        total_amount=total_amount,
        created_at=group.created_at,
    )


@router.put("/groups/{group_id}", response_model=SplitGroupSchema)
async def update_group(
    group_id: str,
    data: SplitGroupUpdateRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> SplitGroupSchema:
    """Update a split group's name or description."""
    result = await db.execute(
        select(SplitGroup)
        .options(selectinload(SplitGroup.split_bills).selectinload(SplitBill.participants))
        .where((SplitGroup.id == group_id) & (SplitGroup.user_id == user_id))
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Split group not found")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(group, key, value)
    group.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(group)

    contact_ids: set[str] = set()
    total_amount = Decimal("0.00")
    for bill in group.split_bills:
        total_amount += bill.total_amount
        for p in bill.participants:
            contact_ids.add(p.contact_id)

    return SplitGroupSchema(
        id=group.id,
        name=group.name,
        description=group.description,
        member_count=len(contact_ids),
        total_amount=total_amount,
        created_at=group.created_at,
    )


@router.delete("/groups/{group_id}", status_code=204)
async def delete_group(
    group_id: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a split group (cascades to its bills and participants)."""
    result = await db.execute(
        select(SplitGroup).where(
            (SplitGroup.id == group_id) & (SplitGroup.user_id == user_id)
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Split group not found")

    await db.delete(group)
    await db.commit()


@router.post("/groups/{group_id}/members", response_model=SplitGroupSchema, status_code=201)
async def add_group_member(
    group_id: str,
    data: AddGroupMemberRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> SplitGroupSchema:
    """Add a contact as a member of a group (recorded on the schema; actual membership
    is derived from bill participation, so we just validate group and contact exist).
    """
    group_result = await db.execute(
        select(SplitGroup)
        .options(selectinload(SplitGroup.split_bills).selectinload(SplitBill.participants))
        .where((SplitGroup.id == group_id) & (SplitGroup.user_id == user_id))
    )
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Split group not found")

    contact_result = await db.execute(
        select(Contact).where(
            (Contact.id == data.contact_id) & (Contact.user_id == user_id)
        )
    )
    if not contact_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contact not found")

    contact_ids: set[str] = set()
    total_amount = Decimal("0.00")
    for bill in group.split_bills:
        total_amount += bill.total_amount
        for p in bill.participants:
            contact_ids.add(p.contact_id)
    contact_ids.add(data.contact_id)

    return SplitGroupSchema(
        id=group.id,
        name=group.name,
        description=group.description,
        member_count=len(contact_ids),
        total_amount=total_amount,
        created_at=group.created_at,
    )


# ---------------------------------------------------------------------------
# Extra read-only endpoints (must come before /{id} to avoid routing conflicts)
# ---------------------------------------------------------------------------


@router.get("/balances", response_model=list[NetBalanceSchema])
async def get_net_balances(
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> list[NetBalanceSchema]:
    """Return net balances between the user and each contact."""
    service = SettlementService(db)
    balances = await service.calculate_net_balances(user_id)
    return [NetBalanceSchema(**b) for b in balances]


@router.get("/summary", response_model=SettlementSummarySchema)
async def get_settlement_summary(
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> SettlementSummarySchema:
    """Return a high-level settlement summary for the user."""
    service = SettlementService(db)
    summary = await service.get_settlement_summary(user_id)
    return SettlementSummarySchema(**summary)


@router.get("/reminders", response_model=list[PendingReminderSchema])
async def get_reminders(
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> list[PendingReminderSchema]:
    """Return pending reminders for contacts with outstanding debts."""
    service = ReminderService(db)
    reminders = await service.get_pending_reminders(user_id)
    return [PendingReminderSchema(**r) for r in reminders]


# ---------------------------------------------------------------------------
# Split Bills CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=SplitBillListResponse)
async def list_bills(
    user_id: str = Query(..., description="User ID"),
    group_id: str | None = Query(None, description="Filter by group ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> SplitBillListResponse:
    """List split bills (paginated, optionally filtered by group)."""
    base_where = SplitBill.user_id == user_id
    count_where = base_where

    if group_id:
        count_where = count_where & (SplitBill.split_group_id == group_id)

    count_result = await db.execute(
        select(func.count()).select_from(SplitBill).where(count_where)
    )
    total = count_result.scalar() or 0

    query = (
        select(SplitBill)
        .options(
            selectinload(SplitBill.participants).selectinload(SplitParticipant.contact)
        )
        .where(count_where)
        .order_by(SplitBill.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    bills = result.scalars().all()

    items = [_serialize_bill(b) for b in bills]
    total_pages = max(1, (total + page_size - 1) // page_size)
    return SplitBillListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.post("", response_model=SplitBillSchema, status_code=201)
async def create_bill(
    data: SplitBillCreateRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> SplitBillSchema:
    """Create a split bill with participants."""
    service = SplitBillService(db)
    try:
        bill = await service.create_bill(user_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _serialize_bill(bill)


@router.get("/{bill_id}", response_model=SplitBillSchema)
async def get_bill(
    bill_id: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> SplitBillSchema:
    """Get a specific split bill with participant details."""
    service = SplitBillService(db)
    bill = await service.get_bill_with_participants(bill_id)
    if not bill or bill.user_id != user_id:
        raise HTTPException(status_code=404, detail="Split bill not found")
    return _serialize_bill(bill)


@router.put("/{bill_id}", response_model=SplitBillSchema)
async def update_bill(
    bill_id: str,
    data: SplitBillUpdateRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> SplitBillSchema:
    """Update a split bill's title or notes."""
    result = await db.execute(
        select(SplitBill)
        .options(
            selectinload(SplitBill.participants).selectinload(SplitParticipant.contact)
        )
        .where((SplitBill.id == bill_id) & (SplitBill.user_id == user_id))
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Split bill not found")

    if data.title is not None:
        bill.name = data.title
    if data.notes is not None:
        bill.description = data.notes
    bill.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(bill)

    service = SplitBillService(db)
    bill = await service.get_bill_with_participants(bill_id)  # reload with relations
    return _serialize_bill(bill)  # type: ignore[arg-type]


@router.delete("/{bill_id}", status_code=204)
async def delete_bill(
    bill_id: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a split bill (cascades to participants)."""
    result = await db.execute(
        select(SplitBill).where(
            (SplitBill.id == bill_id) & (SplitBill.user_id == user_id)
        )
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Split bill not found")

    await db.delete(bill)
    await db.commit()


@router.post("/{bill_id}/settle", response_model=SplitBillSchema)
async def settle_participant(
    bill_id: str,
    body: SettleParticipantRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> SplitBillSchema:
    """Mark a participant in a split bill as settled."""
    # Verify bill belongs to user
    bill_check = await db.execute(
        select(SplitBill).where(
            (SplitBill.id == bill_id) & (SplitBill.user_id == user_id)
        )
    )
    if not bill_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Split bill not found")

    service = SplitBillService(db)
    participant = await service.settle_participant(bill_id, body.contact_id, float(body.amount))
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="Participant not found in this bill",
        )

    bill = await service.get_bill_with_participants(bill_id)
    return _serialize_bill(bill)  # type: ignore[arg-type]


@router.post("/auto-settle/{bill_id}", response_model=SplitBillSchema)
async def auto_settle_bill(
    bill_id: str,
    transaction_id: str = Query(..., description="Transaction ID to attempt matching"),
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> SplitBillSchema:
    """Attempt to auto-settle a bill by matching a transaction."""
    service = SettlementService(db)
    matched = await service.detect_settlement_transaction(user_id, transaction_id)
    if not matched or matched.split_bill_id != bill_id:
        raise HTTPException(
            status_code=422,
            detail="No matching settlement found for the given transaction and bill",
        )

    bill_service = SplitBillService(db)
    bill = await bill_service.get_bill_with_participants(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Split bill not found")
    return _serialize_bill(bill)
