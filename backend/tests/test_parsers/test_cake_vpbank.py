"""Tests for Cake/VPBank parser."""

from pathlib import Path

import pytest

from app.parsers.banks.cake_vpbank import CakeVPBankParser
from app.parsers.base import TransactionDirection


class TestCakeVPBankParser:
    """Test suite for CakeVPBankParser."""

    @pytest.fixture
    def parser(self) -> CakeVPBankParser:
        """Create parser instance."""
        return CakeVPBankParser()

    @pytest.fixture
    def sample_html_email(self) -> str:
        """Load sample email fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "cake_incoming_transfer.html"
        with open(fixture_path, "r", encoding="utf-8") as f:
            return f.read()

    @pytest.mark.asyncio
    async def test_parse_incoming_transfer(
        self,
        parser: CakeVPBankParser,
        sample_html_email: str,
    ) -> None:
        """Test parsing incoming transfer."""
        result = await parser.parse(sample_html_email)

        assert result is not None
        assert result.amount == 500000.0
        assert result.currency == "VND"
        assert result.direction == TransactionDirection.INCOMING
        assert result.merchant == "Nguyễn Văn A (0123456789)"
        assert "14/03/2026" in result.transaction_date or result.transaction_date is None

    @pytest.mark.asyncio
    async def test_amount_parsing(self, parser: CakeVPBankParser) -> None:
        """Test amount parsing with Vietnamese format."""
        html = """
        <html>
            <body>
                <table>
                    <tr>
                        <td>Số tiền:</td>
                        <td>1.234.567,89 đ</td>
                    </tr>
                </table>
            </body>
        </html>
        """
        result = await parser.parse(html)

        assert result is not None
        assert result.amount == 1234567.89

    @pytest.mark.asyncio
    async def test_incoming_direction_detection(self, parser: CakeVPBankParser) -> None:
        """Test direction detection for incoming transactions."""
        html = """
        <html>
            <body>
                <table>
                    <tr>
                        <td>Loại:</td>
                        <td>Nhận tiền chuyển</td>
                    </tr>
                    <tr>
                        <td>Số tiền:</td>
                        <td>100.000 đ</td>
                    </tr>
                </table>
            </body>
        </html>
        """
        result = await parser.parse(html)

        assert result is not None
        assert result.direction == TransactionDirection.INCOMING

    @pytest.mark.asyncio
    async def test_outgoing_direction_detection(self, parser: CakeVPBankParser) -> None:
        """Test direction detection for outgoing transactions."""
        html = """
        <html>
            <body>
                <table>
                    <tr>
                        <td>Loại:</td>
                        <td>Chuyển tiền</td>
                    </tr>
                    <tr>
                        <td>Số tiền:</td>
                        <td>50.000 đ</td>
                    </tr>
                </table>
            </body>
        </html>
        """
        result = await parser.parse(html)

        assert result is not None
        assert result.direction == TransactionDirection.OUTGOING

    def test_matches_email_by_sender(self, parser: CakeVPBankParser) -> None:
        """Test email matching by sender."""
        assert parser.matches_email("noreply@cake.vn", "Transaction")
        assert parser.matches_email("cake@vpbank.com.vn", "Notification")
        assert not parser.matches_email("someone@example.com", "Random email")

    def test_matches_email_by_subject(self, parser: CakeVPBankParser) -> None:
        """Test email matching by subject."""
        assert parser.matches_email("noreply@example.com", "Cake transaction notification")
        assert parser.matches_email("noreply@example.com", "VPBank giao dịch")
        assert parser.matches_email("noreply@example.com", "Transaction from Cake")

    @pytest.mark.asyncio
    async def test_date_parsing(self, parser: CakeVPBankParser) -> None:
        """Test date parsing."""
        html = """
        <html>
            <body>
                <table>
                    <tr>
                        <td>Thời gian:</td>
                        <td>14/03/2026, 22:28:37</td>
                    </tr>
                    <tr>
                        <td>Số tiền:</td>
                        <td>100.000 đ</td>
                    </tr>
                </table>
            </body>
        </html>
        """
        result = await parser.parse(html)

        assert result is not None
        assert result.transaction_date is not None
        # Date should be ISO format
        assert "2026-03-14" in result.transaction_date

    def test_parser_metadata(self, parser: CakeVPBankParser) -> None:
        """Test parser metadata."""
        assert parser.name == "cake_vpbank"
        assert parser.version == "1.0.0"
        assert len(parser.supported_senders) > 0
        assert "noreply@cake.vn" in parser.supported_senders

    @pytest.mark.asyncio
    async def test_parse_invalid_html(self, parser: CakeVPBankParser) -> None:
        """Test parsing invalid HTML."""
        result = await parser.parse("<html><body>No transaction data</body></html>")
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_text_format(self, parser: CakeVPBankParser) -> None:
        """Test parsing plain text format."""
        text = """
        Giao dịch từ VPBank
        Số tiền: 250.000 đ
        Nội dung: Chuyển tiền
        Thời gian: 14/03/2026, 10:30:00
        """
        result = await parser.parse(text)

        assert result is not None
        assert result.amount == 250000.0
        assert result.currency == "VND"

    @pytest.mark.asyncio
    async def test_multiple_formats_vnd_amount(
        self,
        parser: CakeVPBankParser,
    ) -> None:
        """Test VND amount parsing with different formats."""
        test_cases = [
            ("10.000 đ", 10000.0),
            ("1.234.567 VND", 1234567.0),
            ("100000", 100000.0),
        ]

        for amount_text, expected in test_cases:
            html = f"""
            <html>
                <body>
                    <table>
                        <tr>
                            <td>Amount</td>
                            <td>{amount_text}</td>
                        </tr>
                    </table>
                </body>
            </html>
            """
            result = await parser.parse(html)
            assert result is not None
            assert result.amount == expected
