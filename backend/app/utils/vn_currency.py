"""Vietnamese currency utilities."""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


def parse_vnd_amount(amount_str: str) -> Decimal:
    """Parse Vietnamese dong amount from string.

    Examples:
        "10.000 đ" -> Decimal("10000")
        "1.234.567,89 VND" -> Decimal("1234567.89")
        "10000" -> Decimal("10000")
    """
    if not amount_str:
        return Decimal("0")

    # Remove common VN currency symbols
    cleaned = amount_str.replace("đ", "").replace("VND", "").strip()

    # Handle Vietnamese number format: 1.234.567,89 or 1,234,567.89
    # First, try to detect if we have comma or period as decimal separator
    # by checking which comes last
    last_comma = cleaned.rfind(",")
    last_period = cleaned.rfind(".")

    if last_comma > last_period:
        # Vietnamese format: 1.234.567,89
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif last_period > last_comma and last_comma != -1:
        # Mixed or US format but with comma thousands: unlikely, use period as decimal
        cleaned = cleaned.replace(",", "")
    else:
        # Only periods (no commas), could be thousands or decimal
        if last_period != -1:
            period_count = cleaned.count(".")
            after_last_period = cleaned[last_period + 1 :]
            if period_count > 1:
                # Multiple periods → all are thousand separators
                cleaned = cleaned.replace(".", "")
            elif len(after_last_period) == 2 and after_last_period.isdigit():
                # Single period followed by 2 digits → decimal
                pass
            elif len(after_last_period) == 3 and after_last_period.isdigit():
                # Single period followed by 3 digits → thousand separator
                cleaned = cleaned.replace(".", "")
            else:
                # Fallback: remove all periods as thousand separators
                cleaned = cleaned.replace(".", "")

    # Remove any remaining whitespace
    cleaned = cleaned.strip()

    # Extract only digits and decimal point
    cleaned = re.sub(r"[^\d.-]", "", cleaned)

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def format_vnd(amount: Decimal | float | int) -> str:
    """Format amount as Vietnamese dong.

    Examples:
        10000 -> "10.000 ₫"
        1234567.89 -> "1.234.567,89 ₫"
    """
    amount_decimal = Decimal(str(amount))

    # Format with thousand separators
    if "." in str(amount_decimal):
        # Has decimal places
        integer_part, decimal_part = str(amount_decimal).split(".")
        # Pad decimal part to 2 places if needed
        decimal_part = (decimal_part + "00")[:2]
    else:
        integer_part = str(amount_decimal)
        decimal_part = "00"

    # Add thousand separators to integer part
    integer_part = integer_part.lstrip("-")
    is_negative = amount_decimal < 0

    # Reverse for easier processing
    reversed_int = integer_part[::-1]
    groups = [reversed_int[i : i + 3] for i in range(0, len(reversed_int), 3)]
    formatted_int = ".".join(groups)[::-1]

    # Combine parts
    result = f"{formatted_int},{decimal_part} ₫"

    if is_negative:
        result = f"-{result}"

    return result


def parse_vn_datetime(datetime_str: str) -> datetime:
    """Parse Vietnamese datetime string.

    Examples:
        "14/03/2026, 22:28:37" -> datetime(2026, 3, 14, 22, 28, 37)
        "14/03/2026" -> datetime(2026, 3, 14, 0, 0, 0)
    """
    if not datetime_str:
        raise ValueError("Empty datetime string")

    datetime_str = datetime_str.strip()

    # Try different formats
    formats = [
        "%d/%m/%Y, %H:%M:%S",  # 14/03/2026, 22:28:37
        "%d/%m/%Y %H:%M:%S",   # 14/03/2026 22:28:37
        "%d/%m/%Y, %H:%M",     # 14/03/2026, 22:28
        "%d/%m/%Y %H:%M",      # 14/03/2026 22:28
        "%d/%m/%Y",            # 14/03/2026
        "%d-%m-%Y, %H:%M:%S",  # 14-03-2026, 22:28:37
        "%d-%m-%Y %H:%M:%S",   # 14-03-2026 22:28:37
        "%d-%m-%Y, %H:%M",     # 14-03-2026, 22:28
        "%d-%m-%Y %H:%M",      # 14-03-2026 22:28
        "%d-%m-%Y",            # 14-03-2026
    ]

    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse datetime: {datetime_str}")


def vn_datetime_to_iso(datetime_str: str) -> str:
    """Convert Vietnamese datetime string to ISO format.

    Examples:
        "14/03/2026, 22:28:37" -> "2026-03-14T22:28:37"
    """
    dt = parse_vn_datetime(datetime_str)
    return dt.isoformat()
