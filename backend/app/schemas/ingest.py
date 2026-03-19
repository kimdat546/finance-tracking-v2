"""Schemas for transaction ingest endpoints."""

from pydantic import BaseModel, Field


class ParsedTransactionInput(BaseModel):
    """A parsed transaction ready to be ingested."""

    amount: float = Field(gt=0)
    currency: str = "VND"
    description: str
    direction: str  # "incoming" | "outgoing"
    merchant: str | None = None
    transaction_date: str | None = None
    reference_id: str | None = None
    source: str = "client_parser"  # "client_parser" | "server_parser" | "manual"
    confidence: float = Field(default=1.0, ge=0, le=1)


class IngestTransactionRequest(BaseModel):
    """Request to ingest one or more client-parsed transactions."""

    transactions: list[ParsedTransactionInput]
    account_id: str
    user_id: str = "00000000-0000-0000-0000-000000000001"


class IngestResponse(BaseModel):
    """Response from the ingest endpoint."""

    created: int
    skipped: int
    errors: list[str]


class EmailIngestRequest(BaseModel):
    """Request to parse an email server-side then ingest the result."""

    email_body: str
    sender: str = ""
    subject: str = ""
    account_id: str
    user_id: str = "00000000-0000-0000-0000-000000000001"
