# Finance Tracker Backend

A comprehensive FastAPI-based backend for personal finance tracking with email-based transaction parsing, automatic categorization, and multi-tenant support.

## Features

- **FastAPI** modern async framework
- **SQLAlchemy** async ORM with PostgreSQL
- **Email Integration** automatic transaction parsing from bank emails
- **Parser System** extensible architecture for bank email parsers
- **Auto-Categorization** rule-based and pattern-learning categorization
- **Multi-Tenant** ready with per-user database schemas
- **Full Test Suite** unit and integration tests
- **Docker Support** multi-stage builds for production

## Project Structure

```
backend/
├── app/
│   ├── api/              # FastAPI route handlers
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response schemas
│   ├── parsers/          # Email transaction parsers
│   │   └── banks/        # Bank-specific parsers
│   ├── services/         # Business logic services
│   ├── utils/            # Utility functions
│   ├── config.py         # Application settings
│   ├── database.py       # Database setup
│   └── main.py           # FastAPI application entry point
├── alembic/              # Database migrations
├── tests/                # Test suite
├── pyproject.toml        # Poetry dependencies
├── Dockerfile            # Container configuration
└── alembic.ini           # Migration configuration
```

## Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 12+
- Redis 6+
- Poetry

### Installation

1. Install dependencies:
```bash
cd backend
poetry install
```

2. Create `.env` file from example:
```bash
cp .env.example .env
```

3. Update `.env` with your configuration:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/finance_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
```

4. Create database and run migrations:
```bash
poetry run alembic upgrade head
```

5. Run the application:
```bash
poetry run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
- `GET /health/ping` - Simple health check
- `GET /health/status` - Detailed health status

### Transactions
- `GET /transactions` - List transactions with pagination
- `GET /transactions/{id}` - Get transaction details
- `PUT /transactions/{id}` - Update transaction
- `GET /transactions/pending` - Get uncategorized transactions
- `POST /transactions` - Create manual transaction
- `POST /transactions/{id}/categorize` - Categorize transaction
- `POST /transactions/ingest` - Batch ingest transactions

## Database Models

### Core Models
- **User** - Multi-tenant user accounts
- **Account** - Bank accounts
- **Category** - Transaction categories (hierarchical)
- **Transaction** - Individual financial transactions
- **CategorizationRule** - Auto-categorization rules

### Social Features
- **Contact** - People for split bills
- **SplitGroup** - Groups for shared expenses
- **SplitBill** - Shared expenses
- **SplitParticipant** - Bill participants

### Planning Models
- **Budget** - Expense budgets
- **Goal** - Financial goals
- **Debt** - Debt tracking
- **Subscription** - Recurring subscriptions

### System Models
- **EmailSyncLog** - Email sync history
- **ParserRegistry** - Available parsers
- **ParserError** - Parse errors
- **UnrecognizedEmail** - Unparseable emails

## Parsers

### Cake/VPBank Parser

Parses transaction emails from Cake by VPBank with:
- HTML and plain text email support
- Vietnamese number format handling (1.234.567,89)
- Vietnamese date parsing (14/03/2026, 22:28:37)
- Direction detection (incoming/outgoing)
- Amount, merchant, and reference extraction

**Supported Senders:**
- noreply@cake.vn
- cake@vpbank.com.vn
- notifications@cake.vn

### Creating Custom Parsers

1. Create a new file in `app/parsers/banks/`:
```python
from app.parsers.base import BaseBankParser, ParsedTransaction, TransactionDirection

class CustomBankParser(BaseBankParser):
    name = "custom_bank"
    description = "Parser for Custom Bank"
    supported_senders = ["noreply@custombank.com"]

    async def parse(self, email_body: str) -> ParsedTransaction | None:
        # Implement parsing logic
        pass

    def matches_email(self, sender: str, subject: str) -> bool:
        # Check if parser can handle email
        pass
```

2. Parser auto-discovery will register it automatically

## Utilities

### Vietnamese Currency (`app/utils/vn_currency.py`)

```python
from app.utils.vn_currency import parse_vnd_amount, format_vnd, parse_vn_datetime

# Parse amounts
amount = parse_vnd_amount("10.000 đ")  # Decimal(10000)

# Format for display
formatted = format_vnd(10000)  # "10.000,00 ₫"

# Parse dates
dt = parse_vn_datetime("14/03/2026, 22:28:37")
```

## Testing

Run all tests:
```bash
poetry run pytest
```

Run with coverage:
```bash
poetry run pytest --cov=app --cov-report=html
```

Run specific test file:
```bash
poetry run pytest tests/test_parsers/test_cake_vpbank.py -v
```

## Code Quality

Format code with ruff:
```bash
poetry run ruff check --fix .
```

Type checking with mypy:
```bash
poetry run mypy app
```

## Docker

Build image:
```bash
docker build -t finance-tracker-backend .
```

Run container:
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@db/finance_db \
  -e REDIS_URL=redis://redis:6379/0 \
  finance-tracker-backend
```

## Configuration

All configuration is managed through environment variables in `.env`:

- `APP_ENV` - Environment (dev/staging/prod)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT secret key
- `CORS_ORIGINS` - Allowed CORS origins
- `GMAIL_*` - Gmail API credentials
- `EMAIL_SYNC_INTERVAL_MINUTES` - Email sync frequency

## License

MIT
