"""Dynamic parser that executes JSON-based parser specifications at runtime."""

import logging
import re
import time

from bs4 import BeautifulSoup
from lxml import etree

from app.parsers.base import BaseBankParser, ParsedTransaction, TransactionDirection
from app.schemas.parser_spec import (
    ExtractorSpec,
    ExtractorType,
    MatcherSpec,
    MatcherType,
    ParserSpecSchema,
    RuleCondition,
    TransformType,
)
from app.utils.vn_currency import parse_vn_datetime, parse_vnd_amount

logger = logging.getLogger(__name__)


class DynamicParser(BaseBankParser):
    """Runtime parser that executes JSON-based parser specifications."""

    def __init__(self, spec: ParserSpecSchema) -> None:
        """Initialize the DynamicParser with a validated spec.

        Args:
            spec: A validated ParserSpecSchema instance.
        """
        self.spec = spec
        self.name = spec.name
        self.version = spec.version
        self.description = spec.description
        self.supported_senders: list[str] = []
        self._errors: list[str] = []

    def matches_email(self, sender: str, subject: str) -> bool:
        """Check if this spec matches the given email.

        All matchers must pass (AND logic).

        Args:
            sender: Email sender address.
            subject: Email subject line.

        Returns:
            True if all matchers pass.
        """
        for matcher in self.spec.matchers:
            field_value = self._get_matcher_field(matcher.field, sender, subject, "")
            if not self._apply_matcher(matcher, field_value):
                return False
        return True

    def _get_matcher_field(
        self, field: str, sender: str, subject: str, body: str
    ) -> str:
        """Resolve the value for a matcher's target field.

        Args:
            field: Field name ("sender", "subject", or "body").
            sender: Email sender string.
            subject: Email subject string.
            body: Email body string.

        Returns:
            The corresponding field value.
        """
        if field == "sender":
            return sender
        elif field == "subject":
            return subject
        return body

    def _apply_matcher(self, matcher: MatcherSpec, value: str) -> bool:
        """Apply a single matcher against a value.

        Args:
            matcher: The matcher specification.
            value: The string to test against.

        Returns:
            True if the matcher passes.
        """
        pattern = matcher.pattern
        target = value if matcher.case_sensitive else value.lower()
        pat = pattern if matcher.case_sensitive else pattern.lower()

        if matcher.type == MatcherType.REGEX:
            flags = 0 if matcher.case_sensitive else re.IGNORECASE
            return bool(re.search(pattern, value, flags))
        elif matcher.type == MatcherType.SUBSTRING:
            return pat in target
        elif matcher.type == MatcherType.STARTSWITH:
            return target.startswith(pat)
        return False

    async def parse(self, email_body: str) -> ParsedTransaction | None:
        """Parse email body using the JSON spec.

        Args:
            email_body: Raw email body (HTML or plain text).

        Returns:
            ParsedTransaction if successful, None otherwise.
        """
        self._errors = []
        start_time = time.time()

        try:
            extracted = self._extract_fields(email_body, "", "")
            extracted = self._apply_rules(extracted)
            return self._build_transaction(extracted, email_body)
        except Exception as e:
            logger.error(f"DynamicParser [{self.name}] parse error: {e}")
            self._errors.append(str(e))
            return None
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(f"DynamicParser [{self.name}] took {elapsed_ms:.1f}ms")

    async def parse_with_context(
        self,
        email_body: str,
        sender: str = "",
        subject: str = "",
    ) -> tuple[ParsedTransaction | None, list[str], float]:
        """Parse email with full sender/subject context.

        Args:
            email_body: Raw email body (HTML or plain text).
            sender: Email sender address.
            subject: Email subject line.

        Returns:
            Tuple of (ParsedTransaction or None, list of error strings, elapsed ms).
        """
        self._errors = []
        start_time = time.time()

        try:
            extracted = self._extract_fields(email_body, sender, subject)
            extracted = self._apply_rules(extracted)
            result = self._build_transaction(extracted, email_body)
        except Exception as e:
            logger.error(f"DynamicParser [{self.name}] parse_with_context error: {e}")
            self._errors.append(str(e))
            result = None
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(f"DynamicParser [{self.name}] took {elapsed_ms:.1f}ms")

        return result, self._errors.copy(), elapsed_ms

    def _extract_fields(
        self, body: str, sender: str, subject: str
    ) -> dict[str, str]:
        """Run all extractors and collect field values.

        Args:
            body: Email body text.
            sender: Email sender address.
            subject: Email subject line.

        Returns:
            Dictionary of field name to extracted string value.
        """
        result: dict[str, str] = {}
        for extractor in self.spec.extractors:
            source_text = self._get_source_text(extractor.source, body, sender, subject)
            value = self._run_extractor(extractor, source_text)
            if value is not None:
                result[extractor.name] = value
            elif extractor.default is not None:
                result[extractor.name] = extractor.default
            elif extractor.required:
                self._errors.append(f"Required field '{extractor.name}' not found")
        return result

    def _get_source_text(
        self, source: str, body: str, sender: str, subject: str
    ) -> str:
        """Resolve the source text for an extractor.

        Args:
            source: Source identifier ("body", "sender", or "subject").
            body: Email body text.
            sender: Email sender address.
            subject: Email subject line.

        Returns:
            The selected source string.
        """
        if source == "sender":
            return sender
        elif source == "subject":
            return subject
        return body

    def _run_extractor(
        self, extractor: ExtractorSpec, source_text: str
    ) -> str | None:
        """Run a single extractor against source text.

        Args:
            extractor: The extractor specification.
            source_text: The text to extract from.

        Returns:
            Extracted (and optionally transformed) string, or None if not found.
        """
        try:
            if extractor.type == ExtractorType.REGEX:
                match = re.search(extractor.pattern, source_text, re.IGNORECASE)
                if match:
                    value = match.group(extractor.group)
                    return self._apply_transform(value, extractor.transform)

            elif extractor.type == ExtractorType.XPATH:
                soup = BeautifulSoup(source_text, "html.parser")
                try:
                    tree = etree.fromstring(str(soup), parser=etree.HTMLParser())
                    results = tree.xpath(extractor.pattern)
                    if results:
                        value = str(results[0]).strip()
                        return self._apply_transform(value, extractor.transform)
                except Exception:
                    pass

            elif extractor.type == ExtractorType.SUBSTRING:
                idx = source_text.lower().find(extractor.pattern.lower())
                if idx >= 0:
                    end = source_text.find("\n", idx + len(extractor.pattern))
                    snippet_end = (
                        end if end > 0 else idx + len(extractor.pattern) + 100
                    )
                    value = source_text[
                        idx + len(extractor.pattern) : snippet_end
                    ].strip()
                    return self._apply_transform(value, extractor.transform)

        except Exception as e:
            self._errors.append(f"Extractor '{extractor.name}' error: {e}")
        return None

    def _apply_transform(
        self, value: str, transform: TransformType | None
    ) -> str:
        """Apply a named transformation to an extracted value.

        Args:
            value: The raw extracted string.
            transform: The transform type, or None to skip.

        Returns:
            Transformed string value.
        """
        if transform is None:
            return value
        if transform == TransformType.PARSE_VND:
            try:
                return str(parse_vnd_amount(value))
            except Exception:
                return value
        elif transform == TransformType.PARSE_VN_DATE:
            try:
                return parse_vn_datetime(value).isoformat()
            except Exception:
                return value
        elif transform == TransformType.NORMALIZE_MERCHANT:
            return re.sub(r"\s+", " ", re.sub(r"\(.*?\)", "", value)).strip()
        elif transform == TransformType.UPPERCASE:
            return value.upper()
        elif transform == TransformType.LOWERCASE:
            return value.lower()
        elif transform == TransformType.TRIM:
            return value.strip()
        return value

    def _apply_rules(self, fields: dict[str, str]) -> dict[str, str]:
        """Apply conditional rules to modify extracted fields.

        Args:
            fields: Current extracted fields dictionary.

        Returns:
            Updated fields dictionary after applying rules.
        """
        for rule in self.spec.rules:
            field_val = fields.get(rule.condition.field, "")
            if self._check_condition(rule.condition, field_val):
                fields[rule.action.field] = rule.action.value
        return fields

    def _check_condition(self, condition: RuleCondition, value: str) -> bool:
        """Evaluate a rule condition against a value.

        Args:
            condition: The rule condition specification.
            value: The field value to evaluate.

        Returns:
            True if the condition is met.
        """
        op = condition.operator.lower()
        target = condition.value.lower()
        val = value.lower()

        if op == "contains":
            return target in val
        elif op == "equals":
            return val == target
        elif op == "regex":
            return bool(re.search(condition.value, value, re.IGNORECASE))
        elif op == "startswith":
            return val.startswith(target)
        return False

    def _build_transaction(
        self, fields: dict[str, str], raw_body: str
    ) -> ParsedTransaction | None:
        """Build a ParsedTransaction from the extracted fields dictionary.

        Args:
            fields: Extracted field values.
            raw_body: Original email body for raw_text storage.

        Returns:
            ParsedTransaction if amount is available, None otherwise.
        """
        amount_str = fields.get("amount")
        if not amount_str:
            self._errors.append("No amount extracted")
            return None

        try:
            amount = float(amount_str)
        except ValueError:
            self._errors.append(f"Cannot parse amount: {amount_str}")
            return None

        direction_str = fields.get("direction", "outgoing").lower()
        direction = (
            TransactionDirection.INCOMING
            if direction_str == "incoming"
            else TransactionDirection.OUTGOING
        )

        return ParsedTransaction(
            amount=amount,
            currency=fields.get("currency", "VND"),
            description=fields.get("description", f"{self.name} transaction"),
            direction=direction,
            merchant=fields.get("merchant"),
            transaction_date=fields.get("date"),
            reference_id=fields.get("reference"),
            raw_text=raw_body[:500],
            confidence=0.9,
        )

    def get_errors(self) -> list[str]:
        """Return the list of errors from the last parse operation.

        Returns:
            Copy of the internal errors list.
        """
        return self._errors.copy()


def load_parser_from_dict(spec_dict: dict) -> DynamicParser:
    """Create a DynamicParser from a raw dictionary by validating it via Pydantic.

    Args:
        spec_dict: Raw parser spec as a plain dictionary.

    Returns:
        Instantiated DynamicParser.

    Raises:
        pydantic.ValidationError: If the spec_dict does not conform to ParserSpecSchema.
    """
    spec = ParserSpecSchema.model_validate(spec_dict)
    return DynamicParser(spec)
