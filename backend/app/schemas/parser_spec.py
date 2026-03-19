"""Pydantic v2 schemas for JSON-based dynamic parser specs."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class MatcherType(str, Enum):
    """Type of matcher for email field matching."""

    REGEX = "regex"
    SUBSTRING = "substring"
    STARTSWITH = "startswith"


class ExtractorType(str, Enum):
    """Type of extractor for field extraction."""

    REGEX = "regex"
    XPATH = "xpath"
    SUBSTRING = "substring"


class TransformType(str, Enum):
    """Type of transformation to apply to extracted values."""

    PARSE_VND = "parse_vnd"
    PARSE_VN_DATE = "parse_vn_date"
    NORMALIZE_MERCHANT = "normalize_merchant"
    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    TRIM = "trim"


class MatcherSpec(BaseModel):
    """Specification for a single email field matcher."""

    field: str  # "sender" | "subject" | "body"
    pattern: str
    type: MatcherType = MatcherType.REGEX
    case_sensitive: bool = False


class ExtractorSpec(BaseModel):
    """Specification for extracting a single field from email content."""

    name: str  # Field name: "amount" | "merchant" | "date" | "reference" | "description"
    source: str = "body"  # "body" | "subject" | "sender"
    pattern: str  # Regex pattern with capture group, or XPath
    type: ExtractorType = ExtractorType.REGEX
    group: int = 1  # Regex capture group index
    transform: TransformType | None = None
    required: bool = False
    default: str | None = None


class RuleCondition(BaseModel):
    """Condition part of a conditional rule."""

    field: str  # Extracted field name to check
    operator: str  # "contains" | "equals" | "regex" | "startswith"
    value: str


class RuleAction(BaseModel):
    """Action part of a conditional rule."""

    field: str  # Target field to set
    value: str


class RuleSpec(BaseModel):
    """A conditional rule that modifies extracted fields."""

    condition: RuleCondition
    action: RuleAction


class ParserSpecSchema(BaseModel):
    """Complete JSON-based parser specification."""

    name: str
    version: str = "1.0.0"
    enabled: bool = True
    priority: int = 50
    description: str = ""
    matchers: list[MatcherSpec]
    extractors: list[ExtractorSpec]
    rules: list[RuleSpec] = []

    model_config = ConfigDict(extra="forbid")


class ParserSpecCreateRequest(BaseModel):
    """Request body for creating a new parser spec."""

    spec: dict  # Raw JSON spec (will be validated as ParserSpecSchema)
    is_public: bool = False


class ParserSpecResponse(BaseModel):
    """Response schema for a stored parser spec."""

    id: str
    name: str
    version: str
    enabled: bool
    priority: int
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ParserTestRequest(BaseModel):
    """Request body for testing a parser spec against a sample email."""

    spec: dict  # ParserSpecSchema as dict
    email_body: str  # Email body to test against
    sender: str = ""
    subject: str = ""


class ParserTestResponse(BaseModel):
    """Response from testing a parser spec."""

    matched: bool
    parsed: dict | None  # ParsedTransaction as dict
    errors: list[str]
    execution_time_ms: float
