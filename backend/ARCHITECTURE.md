# Finance Tracker Backend - Architecture

## Overview

This is a production-ready FastAPI backend for personal finance tracking with email-based transaction parsing, multi-tenant support, and extensible parser architecture.

## Technology Stack

- **Framework**: FastAPI 0.104+
- **ASGI Server**: Uvicorn with Hypercorn support
- **Database**: PostgreSQL with SQLAlchemy async ORM
- **Caching**: Redis
- **Task Queue**: Celery with APScheduler
- **Email**: Google Gmail API
- **Web Scraping**: BeautifulSoup4 with lxml
- **Testing**: pytest with pytest-asyncio
- **Code Quality**: ruff, mypy

## Architecture Layers

### 1. API Layer (`app/api/`)

Entry points for HTTP requests using FastAPI:

- **`health.py`** - Health check and status endpoints
- **`transactions.py`** - Transaction CRUD and batch operations
- **`router.py`** - Main router combining all sub-routers

Features:
- Pagination support on all list endpoints
- Comprehensive filtering (date range, category, account, status)
- Sorting with configurable order
- Dependency injection for database sessions
- Full request/response validation with Pydantic

### 2. Service Layer (`app/services/`)

Business logic and data processing:

- **`categorizer.py`** - Automatic transaction categorization
  - Rule-based matching with regex support
  - Pattern learning from user history
  - Amount range filtering
  - Statistics tracking

### 3. Parser Layer (`app/parsers/`)

Email parsing and transaction extraction:

- **`base.py`** - Abstract base classes and data models
  - `BaseBankParser` - Abstract parser interface
  - `ParsedTransaction` - Parsed transaction data
  - `TransactionDirection` - Enum for direction
  - `EmailFingerprint` - For deduplication

- **`registry.py`** - Parser discovery and management
  - Singleton registry pattern
  - Auto-discovery from `banks/` directory
  - Priority-based parser selection
  - Parser versioning

- **`banks/cake_vpbank.py`** - Cake/VPBank parser
  - HTML email parsing with BeautifulSoup
  - Vietnamese number format handling
  - Direction detection via keywords
  - Date parsing for Vietnamese format

### 4. Data Layer (`app/models/`, `app/database.py`)

SQLAlchemy ORM models:

**Transaction Models** (`models/transaction.py`):
- `Account` - Bank accounts with balance tracking
- `Category` - Hierarchical transaction categories
- `Transaction` - Individual transactions with full metadata
- `CategorizationRule` - Auto-categorization rules with patterns

**Social Models** (`models/social.py`):
- `Contact` - People for split bills
- `SplitGroup` - Group for shared expenses
- `SplitBill` - Individual shared expenses
- `SplitParticipant` - Participants and amounts

**Planning Models** (`models/planning.py`):
- `Budget` - Period-based expense budgets
- `Goal` - Financial goals with target amounts
- `Debt` - Debt tracking with interest rates
- `Subscription` - Recurring subscriptions

**System Models** (`models/system.py`):
- `User` - Multi-tenant users with schema isolation
- `EmailSyncLog` - Email sync history and statistics
- `ParserRegistry` - Available parsers metadata
- `ParserVersion` - Parser version history
- `ParserError` - Error logs from parsing
- `UnrecognizedEmail` - Unparseable emails for review
- `ParserHealthAlert` - Parser system health monitoring
- `UserSetting` - User preferences and configuration

Database Setup (`database.py`):
- Async SQLAlchemy engine with connection pooling
- `Base` declarative class with UUID pk and timestamps
- Session dependency injection for FastAPI
- Health check and migration support

### 5. Schema Layer (`app/schemas/`)

Pydantic models for request/response validation:

- **`common.py`** - Reusable schemas
  - `PaginationParams` - Pagination query parameters
  - `PaginatedResponse[T]` - Generic paginated response
  - `ErrorResponse` - Error format
  - `SuccessResponse[T]` - Success format

- **`transaction.py`** - Transaction schemas
  - `CategoryCreate`, `CategoryUpdate`, `CategoryResponse`
  - `TransactionCreate`, `TransactionUpdate`, `TransactionResponse`
  - `TransactionIngest` - Batch ingestion
  - `TransactionListResponse` - Paginated list

### 6. Utility Layer (`app/utils/`)

Helper functions and utilities:

- **`vn_currency.py`** - Vietnamese currency handling
  - `parse_vnd_amount()` - Parse Vietnamese format (1.234.567,89)
  - `format_vnd()` - Format to display format
  - `parse_vn_datetime()` - Parse Vietnamese date format
  - `vn_datetime_to_iso()` - Convert to ISO 8601

### 7. Configuration (`app/config.py`)

Pydantic Settings for environment-based configuration:

- Database connection strings
- Redis configuration
- Gmail API credentials paths
- Email sync interval
- CORS origins
- JWT secrets
- Environment detection
- Feature flags

### 8. Main Application (`app/main.py`)

FastAPI application setup:

- CORS middleware configuration
- Lifespan context manager for startup/shutdown
- Database initialization and health checks
- Parser auto-discovery
- Logging configuration
- API router registration

## Data Models

### Transaction Flow

```
Email (Gmail API)
    ↓
Parser Registry (finds best parser)
    ↓
Bank Parser (Cake/VPBank, etc.)
    ↓
ParsedTransaction (validated data)
    ↓
Transaction Model (stored in DB)
    ↓
Categorizer Service (auto-categorize)
    ↓
Category Assignment (rule or learned pattern)
```

### Auto-Categorization Flow

```
Pending Transaction
    ↓
CategorizationRule Matching
    ├─ Merchant pattern (regex or contains)
    ├─ Description pattern (regex or contains)
    ├─ Amount range (min/max)
    └─ Transaction type
    ↓
Pattern Learning (if no rule match)
    ├─ Extract keywords from merchant/description
    └─ Find similar categorized transactions
    ↓
Category ID (assigned or None)
```

## Key Design Patterns

### 1. Repository Pattern
Database access through models and queries

### 2. Service Layer
Business logic isolated in service classes

### 3. Dependency Injection
FastAPI's `Depends()` for database sessions and configuration

### 4. Factory Pattern
Parser registry for dynamic parser selection

### 5. Singleton Pattern
Parser registry as global singleton

### 6. Generic Types
`PaginatedResponse[T]` for type-safe pagination

## Multi-Tenancy

Each user has:
- Isolated `User` record with unique `schema_name`
- All data filtered by `user_id` at the database level
- Separate email sync logs
- User-specific parser preferences and settings

Future: Per-user database schema support via `schema_name` field.

## API Response Format

### Successful Response
```json
{
  "status": "success",
  "data": {...}
}
```

### Paginated Response
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Transaction not found",
  "code": "NOT_FOUND",
  "detail": null
}
```

## Testing Architecture

### Test Fixtures (`tests/conftest.py`)

- **`test_db`** - In-memory SQLite session
- **`test_client`** - FastAPI test client
- **Factories** - TransactionFactory, AccountFactory, CategoryFactory

### Test Organization

- `test_parsers/` - Parser unit tests
  - `test_cake_vpbank.py` - Cake/VPBank parser tests
  - `fixtures/` - Sample emails for testing

- `test_utils/` - Utility function tests
  - `test_vn_currency.py` - Vietnamese currency tests

### Coverage Areas

- Amount parsing (Vietnamese format)
- Date parsing (Vietnamese format)
- Direction detection
- Rule-based matching
- Pattern learning
- Email matching
- Error handling

## Security Considerations

1. **Database**: Async connections with connection pooling
2. **Passwords**: Hashed storage (implementation in User model)
3. **Secrets**: Environment variables for credentials
4. **CORS**: Configurable allowed origins
5. **JWT**: Secret key for authentication (future)
6. **Input Validation**: Pydantic schemas validate all inputs
7. **SQL Injection**: Parameterized queries via SQLAlchemy

## Performance Optimizations

1. **Async/Await**: Non-blocking I/O throughout
2. **Connection Pooling**: Database connection reuse
3. **Pagination**: Limit result sets
4. **Indexing**: Strategic database indexes on frequently queried fields
5. **Caching**: Redis integration ready for response caching
6. **Batch Operations**: Ingest endpoint for bulk transactions

## Deployment

### Docker Deployment

Multi-stage build:
1. **Builder stage** - Install dependencies with Poetry
2. **Runtime stage** - Minimal image with only runtime requirements

### Environment Configuration

All settings via `.env` file:
```
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
SECRET_KEY=...
CORS_ORIGINS=[...]
```

### Health Checks

- `/health/ping` - Simple health check (used by Docker)
- `/health/status` - Detailed database status

## Extensibility Points

1. **Custom Parsers** - Extend `BaseBankParser` in `banks/` directory
2. **Custom Services** - Add services in `app/services/`
3. **Custom Endpoints** - Add routers in `app/api/`
4. **Custom Models** - Add ORM models in `app/models/`
5. **Custom Schemas** - Add Pydantic schemas in `app/schemas/`

## Future Enhancements

1. **Advanced Categorization** - Machine learning-based categorization
2. **Spending Analytics** - Reports and dashboards
3. **Budget Alerts** - Notifications for budget overages
4. **Recurring Transaction Detection** - Automatic detection of subscriptions
5. **Multi-Currency Support** - Conversion rates and analytics
6. **Data Export** - CSV, PDF export capabilities
7. **Webhook Support** - Real-time transaction updates
8. **API Rate Limiting** - Per-user rate limits
9. **Audit Logging** - Track all data modifications
10. **Advanced Splitting** - Group splits and settlements
