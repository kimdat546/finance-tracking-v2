"""Transaction ingest API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.ingest import EmailIngestRequest, IngestResponse, IngestTransactionRequest
from app.services.ingest_service import IngestService

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/transactions", response_model=IngestResponse)
async def ingest_transactions(
    request: IngestTransactionRequest,
    session: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Ingest one or more client-parsed transactions."""
    svc = IngestService(session)
    created, skipped, errors = await svc.ingest_transactions(
        request.user_id,
        request.account_id,
        request.transactions,
    )
    return IngestResponse(created=created, skipped=skipped, errors=errors)


@router.post("/email", response_model=IngestResponse)
async def ingest_email(
    request: EmailIngestRequest,
    session: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Parse an email server-side using the registry, then ingest."""
    svc = IngestService(session)
    created, errors = await svc.ingest_email(
        request.user_id,
        request.account_id,
        request.email_body,
        request.sender,
        request.subject,
    )
    return IngestResponse(created=created, skipped=0, errors=errors)
