"""Base parser classes and abstractions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class TransactionDirection(str, Enum):
    """Direction of transaction."""

    INCOMING = "incoming"
    OUTGOING = "outgoing"


class TransactionType(str, Enum):
    """Type of transaction for parsing."""

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


@dataclass
class ParsedTransaction:
    """Parsed transaction data."""

    amount: float
    currency: str
    description: str
    direction: TransactionDirection
    merchant: str | None = None
    transaction_date: str | None = None
    booking_date: str | None = None
    reference_id: str | None = None
    raw_text: str | None = None
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "amount": self.amount,
            "currency": self.currency,
            "description": self.description,
            "direction": self.direction.value,
            "merchant": self.merchant,
            "transaction_date": self.transaction_date,
            "booking_date": self.booking_date,
            "reference_id": self.reference_id,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
        }


@dataclass
class EmailFingerprint:
    """Email fingerprint for deduplication."""

    sender: str
    subject: str
    received_date: str
    amount: float

    def hash(self) -> str:
        """Generate hash of fingerprint."""
        import hashlib

        data = f"{self.sender}|{self.subject}|{self.received_date}|{self.amount}"
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class ParserSuggestion:
    """Parser suggestion for email."""

    parser_name: str
    confidence: float
    reason: str


class BaseBankParser(ABC):
    """Abstract base class for bank email parsers."""

    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    supported_senders: list[str] = []

    @abstractmethod
    async def parse(self, email_body: str) -> ParsedTransaction | None:
        """Parse email body and extract transaction.

        Args:
            email_body: Email body content (HTML or plain text)

        Returns:
            ParsedTransaction if parsing successful, None otherwise
        """
        pass

    @abstractmethod
    def matches_email(self, sender: str, subject: str) -> bool:
        """Check if parser can handle this email.

        Args:
            sender: Email sender address
            subject: Email subject

        Returns:
            True if parser can handle this email
        """
        pass

    def get_fingerprint(
        self,
        sender: str,
        subject: str,
        received_date: str,
        amount: float,
    ) -> EmailFingerprint:
        """Generate email fingerprint for deduplication."""
        return EmailFingerprint(
            sender=sender,
            subject=subject,
            received_date=received_date,
            amount=amount,
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name={self.name}, version={self.version})"
