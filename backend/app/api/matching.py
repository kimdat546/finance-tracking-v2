"""API endpoints for merchant alias management and transaction group matching."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.matching import Alias, TransactionGroup
from app.schemas.matching import (
    AliasCreateRequest,
    AliasListResponse,
    AliasSchema,
    AutoGroupRequest,
    BulkAliasRequest,
    SimilarityReportResponse,
    TransactionGroupCreateRequest,
    TransactionGroupListResponse,
    TransactionGroupSchema,
)
from app.services.transaction_matcher import TransactionMatcherService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matching", tags=["matching"])


# ---------------------------------------------------------------------------
# Alias endpoints
# ---------------------------------------------------------------------------


@router.get("/aliases", response_model=AliasListResponse)
async def list_aliases(
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> AliasListResponse:
    """List all merchant aliases for the given user with pagination."""
    service = TransactionMatcherService(db)
    items, total = await service.list_aliases(user_id=user_id, page=page, page_size=page_size)
    return AliasListResponse(
        items=[AliasSchema.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/aliases", response_model=AliasSchema, status_code=201)
async def create_alias(
    body: AliasCreateRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> AliasSchema:
    """Create or update a merchant alias for the given user."""
    service = TransactionMatcherService(db)
    alias = await service.get_or_create_alias(
        user_id=user_id,
        original_name=body.original_name,
        canonical_name=body.canonical_name,
    )
    return AliasSchema.model_validate(alias)


@router.put("/aliases/{alias_id}", response_model=AliasSchema)
async def update_alias(
    alias_id: str,
    body: AliasCreateRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> AliasSchema:
    """Update an existing merchant alias."""
    from sqlalchemy import select

    result = await db.execute(
        select(Alias).where((Alias.id == alias_id) & (Alias.user_id == user_id))
    )
    alias = result.scalar_one_or_none()
    if not alias:
        raise HTTPException(status_code=404, detail="Alias not found")

    alias.original_name = body.original_name
    alias.canonical_name = body.canonical_name
    db.add(alias)
    await db.commit()
    await db.refresh(alias)
    logger.info("Updated alias %s for user %s", alias_id, user_id)
    return AliasSchema.model_validate(alias)


@router.delete("/aliases/{alias_id}", status_code=204)
async def delete_alias(
    alias_id: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a merchant alias."""
    from sqlalchemy import select

    result = await db.execute(
        select(Alias).where((Alias.id == alias_id) & (Alias.user_id == user_id))
    )
    alias = result.scalar_one_or_none()
    if not alias:
        raise HTTPException(status_code=404, detail="Alias not found")

    await db.delete(alias)
    await db.commit()
    logger.info("Deleted alias %s for user %s", alias_id, user_id)


@router.post("/aliases/bulk", response_model=list[AliasSchema], status_code=201)
async def bulk_create_aliases(
    body: BulkAliasRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> list[AliasSchema]:
    """Bulk create or update merchant aliases."""
    service = TransactionMatcherService(db)
    mappings = [
        {"original": m.original_name, "canonical": m.canonical_name} for m in body.mappings
    ]
    aliases = await service.bulk_create_aliases(user_id=user_id, mappings=mappings)
    return [AliasSchema.model_validate(a) for a in aliases]


# ---------------------------------------------------------------------------
# Transaction group endpoints
# ---------------------------------------------------------------------------


@router.get("/groups", response_model=TransactionGroupListResponse)
async def list_groups(
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> TransactionGroupListResponse:
    """List all transaction groups for the given user with pagination."""
    service = TransactionMatcherService(db)
    items, total = await service.list_groups(user_id=user_id, page=page, page_size=page_size)
    return TransactionGroupListResponse(
        items=[TransactionGroupSchema.model_validate(g) for g in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/groups", response_model=TransactionGroupSchema, status_code=201)
async def create_group(
    body: TransactionGroupCreateRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> TransactionGroupSchema:
    """Create a new transaction group."""
    service = TransactionMatcherService(db)
    group = await service.create_transaction_group(
        user_id=user_id,
        name=body.name,
        merchant_name=body.merchant_name,
    )
    return TransactionGroupSchema.model_validate(group)


@router.post("/groups/auto/{merchant}", response_model=TransactionGroupSchema)
async def auto_group_by_merchant(
    merchant: str,
    body: AutoGroupRequest | None = None,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> TransactionGroupSchema:
    """Auto-group transactions by merchant name.

    Finds or creates a group for *merchant* and assigns all transactions
    whose merchant field is similar enough (per *threshold*) to the group.
    """
    threshold: float = body.threshold if body else 0.8
    service = TransactionMatcherService(db)
    group = await service.auto_group_by_merchant(
        user_id=user_id,
        merchant_name=merchant,
        threshold=threshold,
    )
    if not group:
        raise HTTPException(
            status_code=404,
            detail=f"No transactions found matching merchant '{merchant}'",
        )
    return TransactionGroupSchema.model_validate(group)


# ---------------------------------------------------------------------------
# Similarity report endpoint
# ---------------------------------------------------------------------------


@router.get("/similarity/{merchant}", response_model=SimilarityReportResponse)
async def get_similarity_report(
    merchant: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> SimilarityReportResponse:
    """Get a similarity report for a merchant name.

    Returns the normalized form, any known alias, and the most similar
    merchants found in the user's transaction history.
    """
    service = TransactionMatcherService(db)
    report = await service.get_similarity_report(user_id=user_id, merchant_name=merchant)
    return SimilarityReportResponse(**report)
