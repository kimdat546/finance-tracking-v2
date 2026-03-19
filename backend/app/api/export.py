"""Data export API endpoints (CSV / JSON)."""

import csv
import io
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.transaction import Account, Category, Transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/transactions/csv")
async def export_transactions_csv(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Export transactions as CSV."""
    q = select(Transaction).where(Transaction.user_id == user_id)
    if start_date:
        q = q.where(Transaction.transaction_date >= start_date)
    if end_date:
        q = q.where(Transaction.transaction_date <= end_date)
    q = q.order_by(Transaction.transaction_date.desc())

    result = await session.execute(q)
    transactions = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "transaction_date", "description", "amount", "currency",
        "type", "merchant", "category_id", "account_id", "reference_id",
        "source", "created_at",
    ])
    for tx in transactions:
        writer.writerow([
            tx.id, tx.transaction_date, tx.description, tx.amount,
            tx.currency, tx.type.value if tx.type else "",
            tx.merchant or "", tx.category_id or "", tx.account_id or "",
            tx.reference_id or "", tx.source or "", tx.created_at,
        ])

    filename = f"transactions_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/transactions/json")
async def export_transactions_json(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Export transactions as JSON."""
    q = select(Transaction).where(Transaction.user_id == user_id)
    if start_date:
        q = q.where(Transaction.transaction_date >= start_date)
    if end_date:
        q = q.where(Transaction.transaction_date <= end_date)
    q = q.order_by(Transaction.transaction_date.desc())

    result = await session.execute(q)
    transactions = result.scalars().all()

    data = [
        {
            "id": tx.id,
            "transaction_date": tx.transaction_date,
            "description": tx.description,
            "amount": float(tx.amount),
            "currency": tx.currency,
            "type": tx.type.value if tx.type else None,
            "merchant": tx.merchant,
            "category_id": tx.category_id,
            "account_id": tx.account_id,
            "reference_id": tx.reference_id,
            "source": tx.source,
            "created_at": str(tx.created_at) if tx.created_at else None,
        }
        for tx in transactions
    ]

    filename = f"transactions_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    return Response(
        content=json.dumps(data, default=str, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/categories/csv")
async def export_categories_csv(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Export categories as CSV."""
    result = await session.execute(
        select(Category).where(Category.user_id == user_id)
    )
    categories = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "type", "color", "icon", "is_default"])
    for cat in categories:
        writer.writerow([
            cat.id, cat.name,
            cat.category_type.value if hasattr(cat, "category_type") and cat.category_type else "",
            getattr(cat, "color", ""),
            getattr(cat, "icon", ""),
            getattr(cat, "is_default", False),
        ])

    filename = f"categories_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/accounts/csv")
async def export_accounts_csv(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Export accounts as CSV."""
    result = await session.execute(
        select(Account).where(Account.user_id == user_id)
    )
    accounts = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "account_type", "currency", "balance", "institution", "is_active"])
    for acc in accounts:
        writer.writerow([
            acc.id, acc.name, acc.account_type, acc.currency,
            float(acc.balance), acc.institution or "", acc.is_active,
        ])

    filename = f"accounts_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
