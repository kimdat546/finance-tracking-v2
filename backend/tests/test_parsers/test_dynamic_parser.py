"""Tests for the DynamicParser runtime and related utilities."""

import pytest
from pydantic import ValidationError

from app.parsers.base import TransactionDirection
from app.parsers.dynamic_parser import DynamicParser, load_parser_from_dict
from app.schemas.parser_spec import ParserSpecSchema


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

MINIMAL_SPEC: dict = {
    "name": "test_parser",
    "version": "1.0.0",
    "enabled": True,
    "priority": 50,
    "description": "Unit-test parser",
    "matchers": [
        {"field": "sender", "pattern": "testbank", "type": "substring"},
    ],
    "extractors": [
        {
            "name": "amount",
            "source": "body",
            "pattern": r"Amount:\s*([\d.,]+)",
            "type": "regex",
            "group": 1,
            "transform": "parse_vnd",
            "required": True,
        }
    ],
    "rules": [],
}

FULL_SPEC: dict = {
    "name": "full_test_parser",
    "version": "1.0.0",
    "enabled": True,
    "priority": 80,
    "description": "Full featured test parser",
    "matchers": [
        {"field": "sender", "pattern": "testbank", "type": "substring"},
        {"field": "subject", "pattern": r"giao d[ịi]ch", "type": "regex"},
    ],
    "extractors": [
        {
            "name": "amount",
            "source": "body",
            "pattern": r"Amount:\s*([\d.,]+)",
            "type": "regex",
            "group": 1,
            "transform": "parse_vnd",
            "required": True,
        },
        {
            "name": "merchant",
            "source": "body",
            "pattern": r"Merchant:\s*(.+?)(?:\n|$)",
            "type": "regex",
            "group": 1,
            "transform": "normalize_merchant",
        },
        {
            "name": "date",
            "source": "body",
            "pattern": r"(\d{1,2}/\d{1,2}/\d{4})",
            "type": "regex",
            "group": 1,
            "transform": "parse_vn_date",
        },
        {
            "name": "reference",
            "source": "body",
            "pattern": r"Ref:\s*(\w+)",
            "type": "regex",
            "group": 1,
        },
        {
            "name": "optional_field",
            "source": "body",
            "pattern": r"NOTPRESENT:\s*(.+)",
            "type": "regex",
            "group": 1,
            "required": False,
            "default": "default_value",
        },
    ],
    "rules": [
        {
            "condition": {"field": "direction", "operator": "contains", "value": "in"},
            "action": {"field": "direction", "value": "incoming"},
        }
    ],
}


@pytest.fixture
def minimal_parser() -> DynamicParser:
    """Return a DynamicParser built from MINIMAL_SPEC."""
    return load_parser_from_dict(MINIMAL_SPEC)


@pytest.fixture
def full_parser() -> DynamicParser:
    """Return a DynamicParser built from FULL_SPEC."""
    return load_parser_from_dict(FULL_SPEC)


# ---------------------------------------------------------------------------
# Matcher tests
# ---------------------------------------------------------------------------


class TestMatchers:
    """Tests for DynamicParser matcher logic."""

    def test_matcher_regex_match(self, minimal_parser: DynamicParser) -> None:
        """Regex matcher should match when the pattern is found in the field."""
        spec = ParserSpecSchema.model_validate(
            {
                **MINIMAL_SPEC,
                "matchers": [
                    {"field": "sender", "pattern": r"no-reply@testbank\.com", "type": "regex"}
                ],
            }
        )
        parser = DynamicParser(spec)
        assert parser.matches_email("no-reply@testbank.com", "Transaction") is True

    def test_matcher_regex_no_match(self, minimal_parser: DynamicParser) -> None:
        """Regex matcher should return False when the pattern is absent."""
        spec = ParserSpecSchema.model_validate(
            {
                **MINIMAL_SPEC,
                "matchers": [
                    {"field": "sender", "pattern": r"otherbank\.com", "type": "regex"}
                ],
            }
        )
        parser = DynamicParser(spec)
        assert parser.matches_email("no-reply@testbank.com", "Transaction") is False

    def test_matcher_substring(self) -> None:
        """Substring matcher should pass when pattern is a substring of the field."""
        spec = ParserSpecSchema.model_validate(
            {
                **MINIMAL_SPEC,
                "matchers": [
                    {"field": "sender", "pattern": "testbank", "type": "substring"}
                ],
            }
        )
        parser = DynamicParser(spec)
        assert parser.matches_email("alerts@testbank.vn", "subject") is True
        assert parser.matches_email("alerts@otherbank.vn", "subject") is False

    def test_matcher_multiple_must_all_match(self) -> None:
        """All matchers must match (AND logic); failing one fails the whole check."""
        spec = ParserSpecSchema.model_validate(FULL_SPEC)
        parser = DynamicParser(spec)

        # Both sender+subject match
        assert parser.matches_email("alerts@testbank.vn", "Giao Dịch mới") is True

        # Only sender matches, subject does not
        assert parser.matches_email("alerts@testbank.vn", "Welcome") is False

        # Neither matches
        assert parser.matches_email("alerts@otherbank.vn", "Welcome") is False


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------


class TestExtractors:
    """Tests for DynamicParser extractor logic."""

    def test_extractor_regex_captures_group(self) -> None:
        """Regex extractor should capture the correct capture group."""
        spec = ParserSpecSchema.model_validate(
            {
                **MINIMAL_SPEC,
                "extractors": [
                    {
                        "name": "reference",
                        "source": "body",
                        "pattern": r"Ref:\s*(\w+)",
                        "type": "regex",
                        "group": 1,
                    }
                ],
            }
        )
        parser = DynamicParser(spec)
        fields = parser._extract_fields("Ref: ABC123\n", "", "")
        assert fields.get("reference") == "ABC123"

    def test_extractor_with_transform_parse_vnd(self) -> None:
        """Regex extractor with parse_vnd transform should return numeric string."""
        spec = ParserSpecSchema.model_validate(MINIMAL_SPEC)
        parser = DynamicParser(spec)
        fields = parser._extract_fields("Amount: 1.500.000\n", "", "")
        # parse_vnd should strip thousand separators
        assert fields.get("amount") == "1500000"

    def test_extractor_required_missing(self) -> None:
        """Missing required extractor field should add an error message."""
        spec = ParserSpecSchema.model_validate(MINIMAL_SPEC)
        parser = DynamicParser(spec)
        # Body has no Amount line
        fields = parser._extract_fields("No useful content here", "", "")
        assert "amount" not in fields
        errors = parser.get_errors()
        assert any("amount" in e for e in errors)

    def test_extractor_default_value(self) -> None:
        """Optional extractor with default should use the default when not found."""
        spec = ParserSpecSchema.model_validate(FULL_SPEC)
        parser = DynamicParser(spec)
        body = "Amount: 50.000\n"
        fields = parser._extract_fields(body, "", "")
        assert fields.get("optional_field") == "default_value"


# ---------------------------------------------------------------------------
# Rule tests
# ---------------------------------------------------------------------------


class TestRules:
    """Tests for DynamicParser rule/condition logic."""

    def test_rule_condition_contains(self) -> None:
        """Rule should fire when the 'contains' condition is satisfied."""
        spec = ParserSpecSchema.model_validate(
            {
                **MINIMAL_SPEC,
                "rules": [
                    {
                        "condition": {
                            "field": "description",
                            "operator": "contains",
                            "value": "transfer",
                        },
                        "action": {"field": "direction", "value": "incoming"},
                    }
                ],
            }
        )
        parser = DynamicParser(spec)
        fields = {"description": "bank transfer received", "direction": "outgoing"}
        updated = parser._apply_rules(fields)
        assert updated["direction"] == "incoming"

    def test_rule_condition_not_met(self) -> None:
        """Rule should NOT fire when the condition is not satisfied."""
        spec = ParserSpecSchema.model_validate(
            {
                **MINIMAL_SPEC,
                "rules": [
                    {
                        "condition": {
                            "field": "description",
                            "operator": "contains",
                            "value": "transfer",
                        },
                        "action": {"field": "direction", "value": "incoming"},
                    }
                ],
            }
        )
        parser = DynamicParser(spec)
        fields = {"description": "payment for coffee", "direction": "outgoing"}
        updated = parser._apply_rules(fields)
        assert updated["direction"] == "outgoing"


# ---------------------------------------------------------------------------
# Full parse flow tests
# ---------------------------------------------------------------------------


class TestBuildTransaction:
    """Tests for the full parse-to-ParsedTransaction flow."""

    @pytest.mark.asyncio
    async def test_build_transaction_success(
        self, full_parser: DynamicParser
    ) -> None:
        """A well-formed email body should produce a valid ParsedTransaction."""
        body = (
            "Amount: 250.000\n"
            "Merchant: Trà Sữa Gong Cha (Quán 1)\n"
            "Date: 14/03/2026\n"
            "Ref: TXN9876\n"
        )
        result = await full_parser.parse(body)
        assert result is not None
        assert result.amount == 250000.0
        assert result.currency == "VND"
        assert result.merchant == "Trà Sữa Gong Cha"
        assert result.reference_id == "TXN9876"
        assert result.direction == TransactionDirection.OUTGOING
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_build_transaction_no_amount(
        self, full_parser: DynamicParser
    ) -> None:
        """Email body without amount should return None and record an error."""
        body = "Merchant: Some Shop\nRef: TXN0001\n"
        result = await full_parser.parse(body)
        assert result is None
        errors = full_parser.get_errors()
        assert any("amount" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# load_parser_from_dict tests
# ---------------------------------------------------------------------------


class TestLoadParserFromDict:
    """Tests for the load_parser_from_dict factory function."""

    def test_load_parser_from_dict_valid(self) -> None:
        """Valid spec dict should produce a DynamicParser with correct attributes."""
        parser = load_parser_from_dict(MINIMAL_SPEC)
        assert isinstance(parser, DynamicParser)
        assert parser.name == "test_parser"
        assert parser.version == "1.0.0"

    def test_load_parser_from_dict_invalid(self) -> None:
        """Invalid spec dict (missing required fields) should raise ValidationError."""
        bad_spec = {"name": "broken"}  # Missing 'matchers' and 'extractors'
        with pytest.raises(ValidationError):
            load_parser_from_dict(bad_spec)


# ---------------------------------------------------------------------------
# matches_email integration tests
# ---------------------------------------------------------------------------


class TestMatchesEmail:
    """Integration tests for matches_email using full parser instances."""

    def test_matches_email_true(self, full_parser: DynamicParser) -> None:
        """Parser should match when sender and subject satisfy all matchers."""
        assert full_parser.matches_email("alerts@testbank.vn", "Giao Dịch thành công") is True

    def test_matches_email_false(self, full_parser: DynamicParser) -> None:
        """Parser should not match when a matcher fails."""
        assert full_parser.matches_email("alerts@otherbank.vn", "Giao Dịch thành công") is False
