"""Contacts API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.social import Contact
from app.schemas.social import (
    ContactCreateRequest,
    ContactListResponse,
    ContactSchema,
    ContactUpdateRequest,
)

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    user_id: str = Query(..., description="User ID"),
    search: str | None = Query(None, description="Search by name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> ContactListResponse:
    """List contacts with optional name search and pagination."""
    base_where = Contact.user_id == user_id

    query = select(Contact).where(base_where)
    count_query = select(func.count()).select_from(Contact).where(base_where)

    if search:
        like_expr = f"%{search}%"
        query = query.where(Contact.name.ilike(like_expr))
        count_query = count_query.where(Contact.name.ilike(like_expr))

    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(Contact.name.asc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    contacts = result.scalars().all()

    items = [ContactSchema.model_validate(c) for c in contacts]
    total_pages = max(1, (total + page_size - 1) // page_size)

    return ContactListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=ContactSchema, status_code=201)
async def create_contact(
    data: ContactCreateRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> ContactSchema:
    """Create a new contact."""
    contact = Contact(
        user_id=user_id,
        name=data.name,
        phone=data.phone,
        email=data.email,
        notes=data.notes,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return ContactSchema.model_validate(contact)


@router.get("/{contact_id}", response_model=ContactSchema)
async def get_contact(
    contact_id: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> ContactSchema:
    """Get a single contact by ID."""
    result = await db.execute(
        select(Contact).where(
            (Contact.id == contact_id) & (Contact.user_id == user_id)
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return ContactSchema.model_validate(contact)


@router.put("/{contact_id}", response_model=ContactSchema)
async def update_contact(
    contact_id: str,
    data: ContactUpdateRequest,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> ContactSchema:
    """Update a contact."""
    result = await db.execute(
        select(Contact).where(
            (Contact.id == contact_id) & (Contact.user_id == user_id)
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(contact, key, value)

    contact.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(contact)
    return ContactSchema.model_validate(contact)


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a contact (cascades to split participants)."""
    result = await db.execute(
        select(Contact).where(
            (Contact.id == contact_id) & (Contact.user_id == user_id)
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await db.delete(contact)
    await db.commit()
