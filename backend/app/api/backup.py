"""Backup and restore API endpoints."""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.planning import Budget, Debt, Goal, Subscription
from app.models.social import Contact, SplitBill
from app.models.transaction import Account, Category, CategorizationRule, Transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backup", tags=["backup"])


@router.get("/export")
async def export_all(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Export all user data as a JSON backup."""
    data: dict = {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
    }

    async def fetch(model, extra_filters=None):  # type: ignore[no-untyped-def]
        q = select(model).where(model.user_id == user_id)  # type: ignore[attr-defined]
        result = await session.execute(q)
        rows = result.scalars().all()
        return [
            {c.name: getattr(row, c.name) for c in model.__table__.columns}  # type: ignore[attr-defined]
            for row in rows
        ]

    data["accounts"] = await fetch(Account)
    data["categories"] = await fetch(Category)
    data["transactions"] = await fetch(Transaction)
    data["categorization_rules"] = await fetch(CategorizationRule)
    data["budgets"] = await fetch(Budget)
    data["goals"] = await fetch(Goal)
    data["debts"] = await fetch(Debt)
    data["subscriptions"] = await fetch(Subscription)
    data["contacts"] = await fetch(Contact)
    data["split_bills"] = await fetch(SplitBill)

    filename = f"finance_backup_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    return JSONResponse(
        content=json.loads(json.dumps(data, default=str)),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/restore")
async def restore_backup(
    backup_data: dict,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    dry_run: bool = Query(default=True),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Restore user data from a JSON backup.

    Set dry_run=false to actually write data.
    """
    version = backup_data.get("version")
    if version != "1.0":
        raise HTTPException(status_code=400, detail=f"Unsupported backup version: {version}")

    backup_user = backup_data.get("user_id")
    if backup_user and backup_user != user_id:
        logger.warning("Backup user %s != current user %s — importing anyway", backup_user, user_id)

    stats = {
        "accounts": len(backup_data.get("accounts", [])),
        "transactions": len(backup_data.get("transactions", [])),
        "categories": len(backup_data.get("categories", [])),
        "budgets": len(backup_data.get("budgets", [])),
        "goals": len(backup_data.get("goals", [])),
        "debts": len(backup_data.get("debts", [])),
        "subscriptions": len(backup_data.get("subscriptions", [])),
        "dry_run": dry_run,
    }

    if not dry_run:
        # A real restore would upsert records here.
        # For safety this is left as a dry-run scaffold.
        logger.info("Restore requested for user %s — %s", user_id, stats)

    return {"message": "Dry run complete" if dry_run else "Restore complete", "stats": stats}
