"""Parser for Cake/VPBank transaction emails."""

import logging
import re
from html.parser import HTMLParser

from bs4 import BeautifulSoup

from app.parsers.base import BaseBankParser, ParsedTransaction, TransactionDirection
from app.utils.vn_currency import parse_vnd_amount, parse_vn_datetime

logger = logging.getLogger(__name__)


class TableHTMLParser(HTMLParser):
    """HTML parser to extract table data."""

    def __init__(self):
        """Initialize parser."""
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.table_data: list[list[str]] = []
        self.current_row: list[str] = []
        self.current_cell = ""
        self.cell_style = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle HTML start tags."""
        if tag == "table":
            self.in_table = True
            self.table_data = []
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ("td", "th") and self.in_row:
            self.in_cell = True
            self.current_cell = ""
            # Extract style attributes
            for attr_name, attr_value in attrs:
                if attr_name == "style" and attr_value:
                    self.cell_style = attr_value

    def handle_endtag(self, tag: str) -> None:
        """Handle HTML end tags."""
        if tag == "table":
            self.in_table = False
        elif tag == "tr" and self.in_row:
            self.in_row = False
            if self.current_row:
                self.table_data.append(self.current_row)
        elif tag in ("td", "th") and self.in_cell:
            self.in_cell = False
            self.current_row.append(self.current_cell.strip())
            self.cell_style = ""

    def handle_data(self, data: str) -> None:
        """Handle text data."""
        if self.in_cell:
            self.current_cell += data


class CakeVPBankParser(BaseBankParser):
    """Parser for Cake by VPBank transaction notifications."""

    name = "cake_vpbank"
    description = "Parser for Cake by VPBank transaction emails"
    version = "1.0.0"
    supported_senders = ["noreply@cake.vn", "cake@vpbank.com.vn", "notifications@cake.vn"]

    async def parse(self, email_body: str) -> ParsedTransaction | None:
        """Parse Cake/VPBank email.

        Args:
            email_body: Email body content (HTML or plain text)

        Returns:
            ParsedTransaction if parsing successful, None otherwise
        """
        try:
            # Try to parse as HTML
            if "<html" in email_body.lower() or "<table" in email_body.lower():
                return self._parse_html(email_body)

            # Fall back to text parsing
            return self._parse_text(email_body)
        except Exception as e:
            logger.error(f"Error parsing Cake/VPBank email: {e}")
            return None

    def _parse_html(self, html_content: str) -> ParsedTransaction | None:
        """Parse HTML email content.

        Args:
            html_content: HTML email body

        Returns:
            ParsedTransaction or None
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract key-value pairs from the email structure
        data = self._extract_key_value_pairs(soup)

        if not data:
            return None

        # Determine direction by looking for keywords
        amount_str = data.get("Amount", data.get("amount", ""))
        description = data.get("Description", data.get("description", ""))

        # Parse amount
        try:
            amount = float(parse_vnd_amount(amount_str))
        except (ValueError, TypeError):
            logger.warning(f"Could not parse amount: {amount_str}")
            return None

        # Determine transaction direction from email content
        direction = self._detect_direction(html_content, description)

        # Parse date
        date_str = data.get("Date", data.get("date", data.get("Time", "")))
        transaction_date = None
        if date_str:
            try:
                transaction_date = parse_vn_datetime(date_str).isoformat()
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")

        # Extract merchant/counterparty
        merchant = data.get(
            "Counterparty",
            data.get("counterparty", data.get("From", data.get("from", None))),
        )

        # Extract reference ID
        reference_id = data.get("Reference", data.get("reference", data.get("ID", None)))

        return ParsedTransaction(
            amount=amount,
            currency="VND",
            description=description or "Cake/VPBank transaction",
            direction=direction,
            merchant=merchant,
            transaction_date=transaction_date,
            reference_id=reference_id,
            raw_text=html_content[:500],
        )

    def _parse_text(self, text_content: str) -> ParsedTransaction | None:
        """Parse plain text email content.

        Args:
            text_content: Plain text email body

        Returns:
            ParsedTransaction or None
        """
        # Look for amount pattern: "10.000 đ" or "10,000 VND"
        amount_pattern = r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:đ|VND)"
        amount_match = re.search(amount_pattern, text_content)

        if not amount_match:
            logger.warning("Could not find amount in Cake/VPBank email")
            return None

        try:
            amount = float(parse_vnd_amount(amount_match.group(0)))
        except (ValueError, TypeError):
            logger.warning(f"Could not parse amount: {amount_match.group(0)}")
            return None

        # Determine direction
        direction = self._detect_direction(text_content, "")

        # Extract date
        date_pattern = r"(\d{1,2}/\d{1,2}/\d{4}[,\s]\s?\d{1,2}:\d{2}(?::\d{2})?)"
        date_match = re.search(date_pattern, text_content)
        transaction_date = None
        if date_match:
            try:
                transaction_date = parse_vn_datetime(date_match.group(1)).isoformat()
            except ValueError:
                pass

        return ParsedTransaction(
            amount=amount,
            currency="VND",
            description="Cake/VPBank transaction",
            direction=direction,
            transaction_date=transaction_date,
            raw_text=text_content[:500],
        )

    def _extract_key_value_pairs(self, soup: BeautifulSoup) -> dict[str, str]:
        """Extract key-value pairs from HTML structure.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Dictionary of extracted key-value pairs
        """
        data: dict[str, str] = {}

        # Try to extract from tables
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(("td", "th"))
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        data[key] = value

        # Try to extract from divs with labels
        divs = soup.find_all("div")
        for div in divs:
            text = div.get_text(strip=True)
            if ":" in text:
                parts = text.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value and len(key) < 50:
                        data[key] = value

        # Try to extract from paragraphs
        paragraphs = soup.find_all("p")
        for p in paragraphs:
            text = p.get_text(strip=True)
            if ":" in text:
                parts = text.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value and len(key) < 50:
                        data[key] = value

        return data

    def _detect_direction(self, content: str, description: str) -> TransactionDirection:
        """Detect transaction direction from content.

        Args:
            content: Email content
            description: Transaction description

        Returns:
            TransactionDirection (INCOMING or OUTGOING)
        """
        content_lower = content.lower()
        description_lower = description.lower() if description else ""

        # Keywords for incoming transactions
        incoming_keywords = [
            "received",
            "đã nhận",
            "deposit",
            "income",
            "incoming",
            "transfer in",
            "incoming transfer",
        ]

        # Keywords for outgoing transactions
        outgoing_keywords = [
            "sent",
            "đã gửi",
            "payment",
            "withdrawal",
            "outgoing",
            "transfer out",
            "outgoing transfer",
            "transfer",
        ]

        # Check for incoming keywords
        for keyword in incoming_keywords:
            if keyword in content_lower or keyword in description_lower:
                return TransactionDirection.INCOMING

        # Check for outgoing keywords
        for keyword in outgoing_keywords:
            if keyword in content_lower or keyword in description_lower:
                return TransactionDirection.OUTGOING

        # Default to outgoing if uncertain
        return TransactionDirection.OUTGOING

    def matches_email(self, sender: str, subject: str) -> bool:
        """Check if this parser can handle the email.

        Args:
            sender: Email sender address
            subject: Email subject

        Returns:
            True if parser can handle this email
        """
        sender_lower = sender.lower()
        subject_lower = subject.lower()

        # Check sender
        for supported_sender in self.supported_senders:
            if supported_sender.lower() in sender_lower:
                return True

        # Check subject for Cake/VPBank keywords
        cake_keywords = ["cake", "vpbank", "transaction", "đơn giao dịch"]
        for keyword in cake_keywords:
            if keyword in subject_lower:
                return True

        return False
