"""Tests for Vietnamese currency utilities."""

from decimal import Decimal
from datetime import datetime

import pytest

from app.utils.vn_currency import (
    parse_vnd_amount,
    format_vnd,
    parse_vn_datetime,
    vn_datetime_to_iso,
)


class TestParseVNDAmount:
    """Test Vietnamese dong amount parsing."""

    def test_simple_amount_with_dong_symbol(self) -> None:
        """Test simple amount with đ symbol."""
        assert parse_vnd_amount("10.000 đ") == Decimal("10000")

    def test_amount_with_decimal_places(self) -> None:
        """Test amount with decimal places."""
        assert parse_vnd_amount("1.234.567,89 đ") == Decimal("1234567.89")

    def test_amount_with_vnd_text(self) -> None:
        """Test amount with VND text."""
        assert parse_vnd_amount("1.234.567 VND") == Decimal("1234567")

    def test_plain_number(self) -> None:
        """Test plain number without currency."""
        assert parse_vnd_amount("10000") == Decimal("10000")

    def test_us_format(self) -> None:
        """Test US format with comma thousands separator."""
        assert parse_vnd_amount("1,234,567.89") == Decimal("1234567.89")

    def test_amount_with_extra_spaces(self) -> None:
        """Test amount with extra whitespace."""
        assert parse_vnd_amount("  10.000 đ  ") == Decimal("10000")

    def test_empty_string(self) -> None:
        """Test empty string."""
        assert parse_vnd_amount("") == Decimal("0")

    def test_invalid_amount(self) -> None:
        """Test invalid amount."""
        assert parse_vnd_amount("abc") == Decimal("0")

    def test_decimal_only(self) -> None:
        """Test amount with only decimal part."""
        assert parse_vnd_amount(",89") == Decimal("0.89")

    def test_large_number(self) -> None:
        """Test large number."""
        assert parse_vnd_amount("1.000.000.000 đ") == Decimal("1000000000")

    def test_negative_amount(self) -> None:
        """Test negative amount."""
        result = parse_vnd_amount("-10.000 đ")
        assert result == Decimal("-10000")


class TestFormatVND:
    """Test Vietnamese dong formatting."""

    def test_format_simple_amount(self) -> None:
        """Test formatting simple amount."""
        assert format_vnd(10000) == "10.000,00 ₫"

    def test_format_with_decimal(self) -> None:
        """Test formatting amount with decimal places."""
        result = format_vnd(1234567.89)
        assert "1.234.567,89" in result
        assert "₫" in result

    def test_format_from_decimal(self) -> None:
        """Test formatting from Decimal type."""
        result = format_vnd(Decimal("100000"))
        assert "100.000,00" in result

    def test_format_small_amount(self) -> None:
        """Test formatting small amount."""
        result = format_vnd(100)
        assert "100,00" in result

    def test_format_negative_amount(self) -> None:
        """Test formatting negative amount."""
        result = format_vnd(-10000)
        assert "-" in result
        assert "10.000,00" in result

    def test_format_zero(self) -> None:
        """Test formatting zero."""
        result = format_vnd(0)
        assert "0,00" in result

    def test_format_large_amount(self) -> None:
        """Test formatting large amount."""
        result = format_vnd(1000000000)
        assert "1.000.000.000,00" in result


class TestParseVNDatetime:
    """Test Vietnamese datetime parsing."""

    def test_parse_full_datetime(self) -> None:
        """Test parsing full datetime."""
        result = parse_vn_datetime("14/03/2026, 22:28:37")
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 14
        assert result.hour == 22
        assert result.minute == 28
        assert result.second == 37

    def test_parse_datetime_without_seconds(self) -> None:
        """Test parsing datetime without seconds."""
        result = parse_vn_datetime("14/03/2026, 22:28")
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 14
        assert result.hour == 22
        assert result.minute == 28

    def test_parse_date_only(self) -> None:
        """Test parsing date only."""
        result = parse_vn_datetime("14/03/2026")
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 14
        assert result.hour == 0
        assert result.minute == 0

    def test_parse_with_dash_separator(self) -> None:
        """Test parsing with dash date separator."""
        result = parse_vn_datetime("14-03-2026, 22:28:37")
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 14

    def test_parse_with_space_time_separator(self) -> None:
        """Test parsing with space instead of comma."""
        result = parse_vn_datetime("14/03/2026 22:28:37")
        assert result.year == 2026
        assert result.hour == 22

    def test_parse_invalid_format(self) -> None:
        """Test parsing invalid format raises error."""
        with pytest.raises(ValueError):
            parse_vn_datetime("invalid date")

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string raises error."""
        with pytest.raises(ValueError):
            parse_vn_datetime("")

    def test_parse_with_extra_spaces(self) -> None:
        """Test parsing with extra whitespace."""
        result = parse_vn_datetime("  14/03/2026, 22:28:37  ")
        assert result.year == 2026


class TestVNDatetimeToISO:
    """Test Vietnamese datetime to ISO conversion."""

    def test_convert_to_iso_format(self) -> None:
        """Test conversion to ISO format."""
        result = vn_datetime_to_iso("14/03/2026, 22:28:37")
        assert result == "2026-03-14T22:28:37"

    def test_iso_format_without_seconds(self) -> None:
        """Test ISO conversion without seconds."""
        result = vn_datetime_to_iso("14/03/2026, 22:28")
        assert "2026-03-14" in result
        assert "22:28" in result

    def test_iso_format_date_only(self) -> None:
        """Test ISO conversion with date only."""
        result = vn_datetime_to_iso("14/03/2026")
        assert "2026-03-14" in result

    def test_iso_format_consistency(self) -> None:
        """Test that ISO format is consistent."""
        vn_date = "14/03/2026, 22:28:37"
        iso_result = vn_datetime_to_iso(vn_date)

        # Parse back and verify
        parsed = parse_vn_datetime(vn_date)
        assert parsed.isoformat() == iso_result


class TestIntegration:
    """Integration tests combining multiple utilities."""

    def test_parse_email_with_amount_and_date(self) -> None:
        """Test parsing email content with amount and date."""
        amount_str = "500.000 đ"
        date_str = "14/03/2026, 22:28:37"

        amount = parse_vnd_amount(amount_str)
        date = parse_vn_datetime(date_str)
        formatted_amount = format_vnd(amount)

        assert amount == Decimal("500000")
        assert date.day == 14
        assert "500.000,00" in formatted_amount

    def test_round_trip_formatting(self) -> None:
        """Test that parsing formatted amount works correctly."""
        original = Decimal("1234567.89")
        formatted = format_vnd(original)
        parsed_back = parse_vnd_amount(formatted)

        assert parsed_back == original
