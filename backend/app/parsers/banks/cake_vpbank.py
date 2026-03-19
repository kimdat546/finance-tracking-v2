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

            # Fall back to enhanced text parsing
            return self._parse_plain_text_enhanced(email_body)
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

        # Normalise keys: strip trailing colons/whitespace for lookup
        normalised_data: dict[str, str] = {}
        for k, v in data.items():
            normalised_data[k.rstrip(":").strip()] = v

        # Determine direction by looking for keywords
        amount_str = (
            normalised_data.get("Amount")
            or normalised_data.get("amount")
            or normalised_data.get("Số tiền")
            or ""
        )
        description = (
            normalised_data.get("Description")
            or normalised_data.get("description")
            or normalised_data.get("Nội dung")
            or ""
        )

        # Parse amount
        try:
            amount = float(parse_vnd_amount(amount_str))
        except (ValueError, TypeError):
            logger.warning(f"Could not parse amount: {amount_str}")
            return None

        # Determine transaction direction from email content
        direction = self._detect_direction(html_content, description)

        # Parse date
        date_str = (
            normalised_data.get("Date")
            or normalised_data.get("date")
            or normalised_data.get("Time")
            or normalised_data.get("Thời gian")
            or ""
        )
        transaction_date = None
        if date_str:
            try:
                transaction_date = parse_vn_datetime(date_str).isoformat()
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")

        # Extract merchant/counterparty using enhanced method
        merchant = self._extract_merchant(html_content, normalised_data)
        if not merchant:
            merchant = (
                normalised_data.get("Counterparty")
                or normalised_data.get("counterparty")
                or normalised_data.get("From")
                or normalised_data.get("from")
                or normalised_data.get("Người gửi")
                or None
            )

        # Extract reference ID using enhanced method
        reference_id = self._extract_reference(normalised_data)
        if not reference_id:
            reference_id = (
                normalised_data.get("Reference")
                or normalised_data.get("reference")
                or normalised_data.get("ID")
                or normalised_data.get("Mã tham chiếu")
                or None
            )

        # Determine transaction type and prefix description
        transaction_type = self._determine_transaction_type(html_content, description, direction)
        prefixed_description = f"[{transaction_type.upper()}] {description or 'Cake/VPBank transaction'}"

        return ParsedTransaction(
            amount=amount,
            currency="VND",
            description=prefixed_description,
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
        return self._parse_plain_text_enhanced(text_content)

    def _parse_plain_text_enhanced(self, text_content: str) -> ParsedTransaction | None:
        """Parse plain text email content with enhanced extraction.

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

        # Extract merchant from known label patterns
        merchant_match = re.search(
            r"(?:Gửi cho|Người nhận|To|Receiver):\s*(.+?)(?:\n|$)",
            text_content,
            re.IGNORECASE,
        )
        merchant: str | None = None
        if merchant_match:
            raw_merchant = merchant_match.group(1).strip()
            merchant = self._clean_merchant(raw_merchant)

        # Extract reference from known label patterns
        ref_match = re.search(
            r"(?:Mã GD|Ref|Reference|Transaction ID):\s*(\w+)",
            text_content,
            re.IGNORECASE,
        )
        reference_id: str | None = ref_match.group(1) if ref_match else None

        # Determine transaction type and build description
        description = "Cake/VPBank transaction"
        transaction_type = self._determine_transaction_type(text_content, description, direction)
        prefixed_description = f"[{transaction_type.upper()}] {description}"

        return ParsedTransaction(
            amount=amount,
            currency="VND",
            description=prefixed_description,
            direction=direction,
            merchant=merchant,
            transaction_date=transaction_date,
            reference_id=reference_id,
            raw_text=text_content[:500],
        )

    def _clean_merchant(self, raw: str) -> str:
        """Clean a raw merchant/receiver string.

        Strips bank codes in brackets or parentheses, collapses extra spaces.

        Args:
            raw: Raw merchant string

        Returns:
            Cleaned merchant name
        """
        # Remove anything in brackets or parentheses (bank codes, account numbers)
        cleaned = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", raw)
        # Collapse multiple spaces to one and strip edges
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _extract_merchant(self, content: str, data: dict) -> str | None:
        """Extract merchant name from email data dict or content.

        Tries a list of common keys used in Cake/VPBank emails. Strips bank
        codes (text inside parentheses or brackets) and normalises whitespace.

        Args:
            content: Raw email content (unused directly but kept for extensibility)
            data: Key-value pairs extracted from the email

        Returns:
            Cleaned merchant name, or None if not found
        """
        candidate_keys = [
            "Receiver",
            "receiver",
            "Gửi cho",
            "Chuyển đến",
            "Merchant",
            "Người nhận",
            "To",
            "Counterparty",
            "counterparty",
        ]
        for key in candidate_keys:
            value = data.get(key)
            if value:
                return self._clean_merchant(value)
        return None

    def _extract_reference(self, data: dict) -> str | None:
        """Extract transaction reference/ID from email data dict.

        Args:
            data: Key-value pairs extracted from the email

        Returns:
            Reference string, or None if not found
        """
        candidate_keys = [
            "Reference",
            "Ref",
            "Mã giao dịch",
            "Transaction ID",
            "ID",
            "Số tham chiếu",
            "Mã tham chiếu",
        ]
        for key in candidate_keys:
            value = data.get(key)
            if value:
                return value.strip()
        return None

    def _determine_transaction_type(
        self,
        content: str,
        description: str,
        direction: TransactionDirection,
    ) -> str:
        """Determine the specific transaction type from content and direction.

        Args:
            content: Raw email content
            description: Parsed transaction description
            direction: Detected transaction direction

        Returns:
            One of: "income", "expense", "transfer", "withdrawal", "purchase"
        """
        combined = (content + " " + (description or "")).lower()

        if "atm" in combined or "rút tiền" in combined:
            return "withdrawal"

        if "mua" in combined or "purchase" in combined or "pos" in combined:
            return "purchase"

        if direction == TransactionDirection.INCOMING:
            return "income"

        # Outgoing: distinguish transfer vs generic expense
        if (
            "chuyển tiền" in combined
            or "transfer" in combined
            or "gửi" in combined
        ):
            return "transfer"

        return "expense"

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
            # Vietnamese additions
            "nhận tiền",
            "tiền vào",
            "cộng tiền",
            "nhận được",
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
            # Vietnamese additions
            "chuyển tiền",
            "tiền ra",
            "trừ tiền",
            "thanh toán",
            "chi tiêu",
            "giao dịch chi",
        ]

        # Check for incoming keywords first (more specific)
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
