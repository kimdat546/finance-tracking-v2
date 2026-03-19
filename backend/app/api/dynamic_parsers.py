"""FastAPI endpoints for managing and testing dynamic JSON parser specs."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.parsers.registry import registry
from app.schemas.parser_spec import (
    ParserSpecCreateRequest,
    ParserSpecResponse,
    ParserTestRequest,
    ParserTestResponse,
)
from app.services.dynamic_parser_service import DynamicParserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dynamic-parsers", tags=["dynamic-parsers"])


@router.get("", response_model=list[ParserSpecResponse])
async def list_specs(
    user_id: str | None = Query(None, description="Filter specs by user ID"),
    include_public: bool = Query(True, description="Include public specs"),
    db: AsyncSession = Depends(get_db),
) -> list[ParserSpecResponse]:
    """List all parser specs accessible to the given user.

    Args:
        user_id: Optional user ID to scope the listing.
        include_public: Whether to include publicly shared specs.
        db: Database session.

    Returns:
        List of ParserSpecResponse objects.
    """
    service = DynamicParserService(db)
    specs = await service.list_specs(user_id=user_id, include_public=include_public)
    return [ParserSpecResponse.model_validate(s) for s in specs]


@router.post("", response_model=ParserSpecResponse, status_code=201)
async def create_spec(
    body: ParserSpecCreateRequest,
    user_id: str | None = Query(None, description="Owner user ID (None = system spec)"),
    db: AsyncSession = Depends(get_db),
) -> ParserSpecResponse:
    """Create and persist a new JSON parser spec.

    Args:
        body: Request body containing the raw spec dict and visibility flag.
        user_id: Optional owner user ID.
        db: Database session.

    Returns:
        Created ParserSpecResponse.

    Raises:
        HTTPException 422: If the spec JSON fails schema validation.
    """
    service = DynamicParserService(db)
    try:
        record = await service.create_spec(
            user_id=user_id,
            spec_dict=body.spec,
            is_public=body.is_public,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    return ParserSpecResponse.model_validate(record)


@router.get("/{spec_id}", response_model=ParserSpecResponse)
async def get_spec(
    spec_id: str,
    db: AsyncSession = Depends(get_db),
) -> ParserSpecResponse:
    """Retrieve a single parser spec by ID.

    Args:
        spec_id: UUID of the parser spec.
        db: Database session.

    Returns:
        ParserSpecResponse for the requested spec.

    Raises:
        HTTPException 404: If the spec is not found.
    """
    service = DynamicParserService(db)
    record = await service.get_spec(spec_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Parser spec not found")
    return ParserSpecResponse.model_validate(record)


@router.put("/{spec_id}", response_model=ParserSpecResponse)
async def update_spec(
    spec_id: str,
    body: ParserSpecCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ParserSpecResponse:
    """Replace an existing parser spec with new data.

    Args:
        spec_id: UUID of the parser spec to update.
        body: Request body with the new spec dict.
        db: Database session.

    Returns:
        Updated ParserSpecResponse.

    Raises:
        HTTPException 404: If the spec is not found.
        HTTPException 422: If the new spec fails validation.
    """
    service = DynamicParserService(db)
    try:
        record = await service.update_spec(spec_id=spec_id, spec_dict=body.spec)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Parser spec not found")
    return ParserSpecResponse.model_validate(record)


@router.delete("/{spec_id}", status_code=204)
async def delete_spec(
    spec_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a parser spec by ID.

    Args:
        spec_id: UUID of the parser spec to delete.
        db: Database session.

    Raises:
        HTTPException 404: If the spec is not found.
    """
    service = DynamicParserService(db)
    deleted = await service.delete_spec(spec_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Parser spec not found")


@router.patch("/{spec_id}/toggle", response_model=ParserSpecResponse)
async def toggle_spec(
    spec_id: str,
    enabled: bool = Query(..., description="New enabled state"),
    db: AsyncSession = Depends(get_db),
) -> ParserSpecResponse:
    """Enable or disable a parser spec.

    Args:
        spec_id: UUID of the parser spec.
        enabled: Desired enabled state.
        db: Database session.

    Returns:
        Updated ParserSpecResponse.

    Raises:
        HTTPException 404: If the spec is not found.
    """
    service = DynamicParserService(db)
    record = await service.toggle_enabled(spec_id=spec_id, enabled=enabled)
    if record is None:
        raise HTTPException(status_code=404, detail="Parser spec not found")
    return ParserSpecResponse.model_validate(record)


@router.post("/test", response_model=ParserTestResponse)
async def test_spec(
    body: ParserTestRequest,
    db: AsyncSession = Depends(get_db),
) -> ParserTestResponse:
    """Test a parser spec against a sample email without persisting.

    Args:
        body: Request body with spec dict, email body, sender, and subject.
        db: Database session.

    Returns:
        ParserTestResponse with match status, parsed result, errors, and timing.

    Raises:
        HTTPException 422: If the spec fails schema validation.
    """
    service = DynamicParserService(db)
    try:
        matched, result_dict, errors, elapsed_ms = await service.test_spec(
            spec_dict=body.spec,
            email_body=body.email_body,
            sender=body.sender,
            subject=body.subject,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    return ParserTestResponse(
        matched=matched,
        parsed=result_dict,
        errors=errors,
        execution_time_ms=elapsed_ms,
    )


@router.post("/{spec_id}/load", response_model=dict)
async def load_spec_into_registry(
    spec_id: str,
    user_id: str | None = Query(None, description="User ID context for loading"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Load a single stored spec (or all user specs) into the in-memory parser registry.

    When spec_id is provided, the service loads all enabled specs for user_id
    (plus public specs) into the global registry. Returns the count of loaded parsers.

    Args:
        spec_id: UUID of the spec (used to confirm the spec exists).
        user_id: Optional user ID context for loading related specs.
        db: Database session.

    Returns:
        Dictionary with "loaded" count.

    Raises:
        HTTPException 404: If the spec is not found.
    """
    service = DynamicParserService(db)
    record = await service.get_spec(spec_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Parser spec not found")

    count = await service.load_into_registry(registry=registry, user_id=user_id)
    return {"loaded": count}
