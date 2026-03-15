"""Transaction API endpoints."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.transaction import Transaction, Account, TransactionStatus, TransactionType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
    TransactionIngest,
)
from app.schemas.common import PaginationParams

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    user_id: str = Query(..., description="User ID"),
    account_id: str | None = Query(None, description="Filter by account ID"),
    category_id: str | None = Query(None, description="Filter by category ID"),
    status: TransactionStatus | None = Query(None, description="Filter by status"),
    type_filter: TransactionType | None = Query(None, alias="type", description="Filter by type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    """List transactions with optional filters and pagination."""
    query = select(Transaction).where(Transaction.user_id == user_id)

    if account_id:
        query = query.where(Transaction.account_id == account_id)
    if category_id:
        query = query.where(Transaction.category_id == category_id)
    if status:
        query = query.where(Transaction.status == status)
    if type_filter:
        query = query.where(Transaction.type == type_filter)

    # Count total
    count_query = select(func.count()).select_from(Transaction).where(
        Transaction.user_id == user_id
    )
    if account_id:
        count_query = count_query.where(Transaction.account_id == account_id)
    if category_id:
        count_query = count_query.where(Transaction.category_id == category_id)
    if status:
        count_query = count_query.where(Transaction.status == status)
    if type_filter:
        count_query = count_query.where(Transaction.type == type_filter)

    total = (await db.execute(count_query)).scalar() or 0

    # Add sorting
    if sort_by == "created_at":
        order_column = Transaction.created_at
    elif sort_by == "amount":
        order_column = Transaction.amount
    elif sort_by == "transaction_date":
        order_column = Transaction.transaction_date
    else:
        order_column = Transaction.created_at

    if sort_order == "asc":
        query = query.order_by(order_column.asc())
    else:
        query = query.order_by(order_column.desc())

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    transactions = result.scalars().all()

    items = [TransactionResponse.model_validate(t) for t in transactions]
    total_pages = (total + page_size - 1) // page_size

    return TransactionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Get a specific transaction."""
    result = await db.execute(
        select(Transaction).where(
            (Transaction.id == transaction_id) & (Transaction.user_id == user_id)
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return TransactionResponse.model_validate(transaction)


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    update_data: TransactionUpdate,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Update a transaction."""
    result = await db.execute(
        select(Transaction).where(
            (Transaction.id == transaction_id) & (Transaction.user_id == user_id)
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(transaction, key, value)

    transaction.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(transaction)

    return TransactionResponse.model_validate(transaction)


@router.get("/pending", response_model=list[TransactionResponse])
async def get_pending_transactions(
    user_id: str = Query(..., description="User ID"),
    account_id: str | None = Query(None, description="Filter by account ID"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[TransactionResponse]:
    """Get pending transactions (not categorized)."""
    query = select(Transaction).where(
        (Transaction.user_id == user_id) & (Transaction.is_categorized == False)
    )

    if account_id:
        query = query.where(Transaction.account_id == account_id)

    query = query.limit(limit)

    result = await db.execute(query)
    transactions = result.scalars().all()

    return [TransactionResponse.model_validate(t) for t in transactions]


@router.post("", response_model=TransactionResponse)
async def create_transaction(
    user_id: str = Query(..., description="User ID"),
    transaction_data: TransactionCreate = None,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Create a manual transaction."""
    # Verify account exists and belongs to user
    account_result = await db.execute(
        select(Account).where(
            (Account.id == transaction_data.account_id)
            & (Account.user_id == user_id)
        )
    )
    if not account_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    transaction = Transaction(
        user_id=user_id,
        account_id=transaction_data.account_id,
        category_id=transaction_data.category_id,
        amount=transaction_data.amount,
        currency=transaction_data.currency,
        type=transaction_data.type,
        description=transaction_data.description,
        merchant=transaction_data.merchant,
        notes=transaction_data.notes,
        transaction_date=transaction_data.transaction_date,
        booking_date=transaction_data.booking_date,
        source="manual",
        status=TransactionStatus.CONFIRMED,
    )

    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    return TransactionResponse.model_validate(transaction)


@router.post("/{transaction_id}/categorize", response_model=TransactionResponse)
async def categorize_transaction(
    transaction_id: str,
    category_id: str = Query(..., description="Category ID"),
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Categorize a transaction."""
    result = await db.execute(
        select(Transaction).where(
            (Transaction.id == transaction_id) & (Transaction.user_id == user_id)
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction.category_id = category_id
    transaction.is_categorized = True
    transaction.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(transaction)

    return TransactionResponse.model_validate(transaction)


@router.post("/ingest", response_model=dict[str, int | str])
async def ingest_transactions(
    user_id: str = Query(..., description="User ID"),
    ingest_data: TransactionIngest = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    """Ingest multiple transactions from client-side processing."""
    # Verify account exists and belongs to user
    account_result = await db.execute(
        select(Account).where(
            (Account.id == ingest_data.account_id) & (Account.user_id == user_id)
        )
    )
    if not account_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    created_count = 0
    for transaction_data in ingest_data.transactions:
        transaction = Transaction(
            user_id=user_id,
            account_id=transaction_data.account_id,
            category_id=transaction_data.category_id,
            amount=transaction_data.amount,
            currency=transaction_data.currency,
            type=transaction_data.type,
            description=transaction_data.description,
            merchant=transaction_data.merchant,
            notes=transaction_data.notes,
            transaction_date=transaction_data.transaction_date,
            booking_date=transaction_data.booking_date,
            source="ingest",
            status=TransactionStatus.PENDING,
        )
        db.add(transaction)
        created_count += 1

    await db.commit()

    return {
        "status": "success",
        "created": created_count,
        "total": len(ingest_data.transactions),
    }
