# WBS-001: Email Parser Engine

**Feature**: Email Parser Engine - Email-based Transaction Parsing
**Status**: NOT STARTED
**Priority**: P0 (Critical)
**Total Effort**: 200-250 hours (10 tasks, 20-25 hours each)
**Created**: 2026-03-15

---

## WBS-001-01: Implement Gmail API Connection (OAuth2 Setup, Token Management)

**Status**: NOT STARTED
**Priority**: P0
**Estimated Effort**: 25 hours
**Dependencies**: None

### Description

Implement Gmail API connection with OAuth2 authentication and secure token management. This task covers setting up Google OAuth2 flow for user authorization, storing/refreshing access tokens securely, and initializing Gmail API client. Token refresh must be automatic and handle expiration gracefully.

### Acceptance Criteria

1. Google OAuth2 flow implemented (authorization code flow)
2. Access tokens stored encrypted in database (TokenStore model with encryption)
3. Automatic token refresh before expiration (>= 5 min before expiry)
4. Secure token storage (never log tokens, use environment variables for secrets)
5. Error handling for invalid/expired tokens (re-authenticate flow)
6. Unit tests for token lifecycle (creation, refresh, expiration)
7. Integration test with real Gmail API (using test account)
8. Documentation: OAuth setup guide, credentials configuration

### Files to Create

- `/backend/app/models/email.py` - EmailAccount model with encrypted token storage
- `/backend/app/services/gmail_service.py` - Gmail API client wrapper
- `/backend/app/services/oauth_service.py` - OAuth2 token management service
- `/backend/app/schemas/oauth.py` - OAuth request/response schemas
- `/backend/app/api/oauth.py` - OAuth endpoints (authorize, callback, refresh)
- `/backend/tests/test_oauth.py` - OAuth token lifecycle tests
- `/backend/app/utils/encryption.py` - Token encryption/decryption utilities

### Files to Modify

- `/backend/app/main.py` - Add OAuth routes
- `/backend/app/database.py` - Initialize token encryption
- `/backend/app/config.py` - Add Google OAuth credentials config
- `/backend/alembic/versions/001_initial.py` - Add EmailAccount table

### Test Requirements

- Unit tests for token encryption/decryption
- Unit tests for token refresh logic
- Integration test with Gmail API (mock or test account)
- Test error cases: invalid token, network error, etc.
- **Minimum coverage**: 90% (services + utils)

### Technical Notes for AI Agent

1. **OAuth2 Flow**:
   - Use `google-auth-oauthlib` (already in pyproject.toml)
   - Store: `access_token`, `refresh_token`, `token_expiry`
   - Implement refresh logic using `google-auth` with automatic retry

2. **Token Storage**:
   - Create `TokenStore` model with:
     - `user_id` (FK to users table)
     - `encrypted_access_token` (VARBINARY)
     - `encrypted_refresh_token` (VARBINARY)
     - `token_expiry` (DateTime)
     - `provider` (email 'gmail')
   - Use `cryptography` library for encryption (add to poetry)

3. **API Endpoints**:
   ```
   POST /oauth/authorize       - Start OAuth flow
   GET /oauth/callback         - Redirect from Google
   POST /oauth/refresh         - Manual token refresh
   DELETE /oauth/disconnect    - Revoke access
   ```

4. **Security**:
   - Never log tokens (use `***` for logging)
   - Store secrets in environment only
   - Use HTTPS for callbacks
   - Implement rate limiting on token refresh

5. **Error Scenarios**:
   - Token expired → automatic refresh
   - Network error → retry with backoff
   - Invalid token → redirect to re-auth
   - Multiple accounts → support per-user

6. **Configuration**:
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` in .env
   - `GOOGLE_REDIRECT_URI` = `https://yourapp.com/oauth/callback`
   - Encryption key in `ENCRYPTION_KEY` env var

7. **Database Migration**:
   - Create `email_accounts` table
   - Add unique constraint on `(user_id, provider)`

### Documentation Needed

- OAuth flow diagram (ASCII art in comments)
- Setup guide: registering app in Google Cloud Console
- Token refresh behavior documentation
- Error handling guide

---

## WBS-001-02: Implement Email Sync Service (Fetch, Filter, Incremental Sync)

**Status**: NOT STARTED
**Priority**: P0
**Estimated Effort**: 30 hours
**Dependencies**: WBS-001-01

### Description

Implement email synchronization service that fetches emails from Gmail using `historyId` for incremental sync (only new emails since last sync). Service filters by labels/senders, handles network failures with exponential backoff, and tracks sync state in database. Must efficiently sync thousands of emails per user.

### Acceptance Criteria

1. Incremental sync with `historyId` (fetch only new emails since last sync)
2. Label filtering (configurable via settings: "Finance/Cake", "Finance/VPBank", etc.)
3. Sender filtering (whitelist specific bank email addresses)
4. Full sync fallback (if historyId invalid, full re-sync)
5. Network resilience with exponential backoff (3 retries, max 10 min wait)
6. `EmailSyncLog` tracking (timestamps, email count, status, errors)
7. Batch processing of large email lists (>1000 emails per page)
8. Duplicate email detection (using message ID)
9. Raw email body storage (for parser to process)
10. Scheduled sync service ready (AsyncScheduler/APScheduler integration)

### Files to Create

- `/backend/app/services/email_sync_service.py` - Main sync service
- `/backend/app/models/email.py` - Email model (store raw email body)
- `/backend/app/schemas/email.py` - Email schemas
- `/backend/app/api/email_sync.py` - Email sync endpoints
- `/backend/tests/test_email_sync.py` - Email sync tests
- `/backend/app/utils/email_utils.py` - Email parsing utilities

### Files to Modify

- `/backend/app/models/system.py` - Update EmailSyncLog model
- `/backend/app/services/gmail_service.py` - Add Gmail API fetch methods
- `/backend/app/main.py` - Add email sync routes
- `/backend/alembic/versions/002_email_sync.py` - Add Email, EmailSyncLog tables

### Test Requirements

- Unit tests for sync logic (mocked Gmail API)
- Test incremental sync with historyId
- Test full sync fallback
- Test duplicate detection
- Test network failures and retries
- Test batch processing
- Test label/sender filtering
- **Minimum coverage**: 85%

### Technical Notes for AI Agent

1. **Email Fetch Strategy**:
   - Use `gmail.users().messages().list(userId='me', q=query)`
   - Query format: `label:Finance/Cake from:cake@vietcombank.com.vn`
   - Return: messageId, internalDate, from, subject, snippet
   - Get full message with: `messages().get(id=msg_id, format='full')`

2. **Incremental Sync with historyId**:
   ```python
   # Get historyId from last sync
   history_id = user_settings.gmail_history_id

   if history_id:
       # Incremental sync
       result = gmail_service.users().history().list(
           userId='me',
           startHistoryId=history_id
       ).execute()
       messages = extract_messages_from_history(result['history'])
   else:
       # Full sync
       result = gmail_service.users().messages().list(
           userId='me',
           q=query
       ).execute()
       messages = result['messages']

   # Save new historyId
   user_settings.gmail_history_id = result['historyId']
   ```

3. **Email Model**:
   ```python
   class Email(Base):
       __tablename__ = "emails"

       id: Mapped[str]
       user_id: Mapped[str]  # FK to users
       gmail_message_id: Mapped[str]  # Gmail's message ID
       sender: Mapped[str]
       subject: Mapped[str]
       received_at: Mapped[datetime]
       raw_body: Mapped[str]  # Full email HTML/plain text
       parsed: Mapped[bool] = default(False)
       sync_log_id: Mapped[str | None]  # FK to EmailSyncLog

       __table_args__ = (
           Index('ix_emails_user_gmail_id', 'user_id', 'gmail_message_id'),
       )
   ```

4. **Sync State Tracking**:
   - Store `gmail_history_id` in UserSettings
   - Track last_sync_at, last_sync_count, last_sync_error
   - Use EmailSyncLog for audit trail

5. **Error Handling**:
   - Network error → Retry with backoff (1s, 2s, 4s, 8s, max 10s)
   - Rate limit (429) → Wait 60s, then retry
   - Auth error (401) → Refresh token (WBS-001-01)
   - Invalid historyId → Fall back to full sync

6. **Configuration**:
   - Default labels: "Finance/Cake", "Finance/VPBank"
   - Default senders: bank email addresses (configurable)
   - Batch size: 100 messages per fetch
   - Max emails per sync: 5000

7. **Async/Await**:
   - Sync service is async
   - Use `asyncio.sleep()` for backoff
   - Use `asyncio.gather()` for parallel operations

### Documentation Needed

- Email sync flow diagram
- historyId explanation
- Query format guide for filters
- Error handling flowchart

---

## WBS-001-03: Implement Cake/VPBank Parser for Outgoing Transfers

**Status**: NOT STARTED
**Priority**: P0
**Estimated Effort**: 20 hours
**Dependencies**: WBS-001-02

### Description

Extend the existing Cake/VPBank parser to handle outgoing transfers (not just incoming). Parse both HTML and plain text email formats. Handle multiple transaction types: transfers, withdrawals, purchases. Extract merchant names, verify amounts, and detect transaction direction reliably.

### Acceptance Criteria

1. Outgoing transfer parsing (in addition to existing incoming)
2. Multiple transaction types: TRANSFER, WITHDRAWAL, PURCHASE
3. Merchant name extraction (clean, deduplicated names)
4. Reference number extraction (for reconciliation)
5. HTML and plain text parsing (fallback if HTML fails)
6. Amount validation (non-zero, positive/negative correct)
7. Date/time parsing (handle timezone)
8. Parser detects direction: INCOMING or OUTGOING
9. Error messages recorded (for debugging unrecognized emails)
10. 95%+ parsing success rate for valid bank emails

### Files to Create

- `/backend/app/parsers/banks/cake_vpbank_outgoing.py` - Outgoing transfer parser (or enhance existing)
- `/backend/tests/test_parsers/fixtures/cake_outgoing_transfer.html` - Test fixture
- `/backend/tests/test_parsers/fixtures/cake_outgoing_withdrawal.txt` - Plain text fixture

### Files to Modify

- `/backend/app/parsers/banks/cake_vpbank.py` - Enhance existing parser
- `/backend/tests/test_parsers/test_cake_vpbank.py` - Add outgoing tests

### Test Requirements

- Test incoming transfer (existing)
- Test outgoing transfer
- Test withdrawal (outgoing)
- Test purchase (outgoing)
- Test HTML parsing
- Test plain text fallback
- Test error cases (malformed emails)
- Test direction detection accuracy
- **Minimum coverage**: 95%

### Technical Notes for AI Agent

1. **Parser Enhancement**:
   - Enhance existing `CakeVpbankParser` class
   - Add method: `_detect_direction()` using keywords
   - Add method: `_extract_merchant()` using regex
   - Add method: `_parse_plain_text()` fallback

2. **Outgoing Keywords**:
   - "Chuyển tiền", "Transfer to", "Gửi", "Chi", "Rút tiền"
   - Use fuzzy matching for robustness

3. **Amount Parsing**:
   - Incoming: positive amount, transaction_type = INCOME
   - Outgoing: negative amount, transaction_type = EXPENSE
   - Handle multiple formats: `1.234.567,89` and `1,234,567.89`

4. **Merchant Extraction**:
   - From "Gửi cho: <merchant>"
   - From "Receiver name: <merchant>"
   - Clean: remove bank codes, trim whitespace
   - Store in normalized form

5. **Test Fixtures**:
   - Use real Cake/VPBank email templates
   - Test both outgoing formats
   - Include edge cases

6. **Error Handling**:
   - Return None if can't parse
   - Log reason in UnrecognizedEmail table
   - Allow for manual correction

### Documentation Needed

- Supported email formats list
- Merchant extraction rules
- Direction detection algorithm

---

## WBS-001-04: Implement Email Fingerprinting System

**Status**: NOT STARTED
**Priority**: P0
**Estimated Effort**: 15 hours
**Dependencies**: WBS-001-03

### Description

Implement email fingerprinting to detect duplicate or near-duplicate emails (same transaction reported multiple times). Use content hashing (SHA256 on key fields: sender, amount, date, merchant) to create fingerprints. Detect duplicates before parsing to avoid redundant processing.

### Acceptance Criteria

1. SHA256 fingerprint from: sender + amount + date + merchant + account
2. Fingerprint stored in Email model
3. Duplicate detection before parsing (query by fingerprint)
4. Mark duplicates with `is_duplicate = True` flag
5. Don't parse duplicates (skip to next email)
6. Fingerprint collision detection (handle rare cases)
7. Email deduplication API endpoint
8. Cleanup old duplicates (configurable retention)

### Files to Create

- `/backend/app/utils/email_fingerprinting.py` - Fingerprinting utilities
- `/backend/tests/test_utils/test_email_fingerprinting.py` - Fingerprinting tests

### Files to Modify

- `/backend/app/models/email.py` - Add fingerprint, is_duplicate fields
- `/backend/app/services/email_sync_service.py` - Check duplicates during sync
- `/backend/alembic/versions/003_email_fingerprint.py` - Add columns/index

### Test Requirements

- Test fingerprint generation (deterministic)
- Test duplicate detection
- Test collision handling
- Test deduplication API
- Test cleanup job
- **Minimum coverage**: 90%

### Technical Notes for AI Agent

1. **Fingerprint Components**:
   ```python
   def generate_fingerprint(email: Email) -> str:
       """Generate SHA256 fingerprint from email."""
       # Parse to get amount, merchant, date
       parsed = parse_email(email.raw_body)
       if not parsed:
           return None

       # Create fingerprint key
       key = f"{email.sender}|{parsed.amount}|{parsed.date}|{parsed.merchant}|{email.user_id}"
       return hashlib.sha256(key.encode()).hexdigest()
   ```

2. **Duplicate Detection**:
   - Check if fingerprint exists in Email table
   - If exists and created_at within 24 hours → duplicate
   - Mark with `is_duplicate = True`
   - Skip parsing

3. **Email Model Update**:
   ```python
   fingerprint: Mapped[str | None]  # SHA256 hash
   is_duplicate: Mapped[bool] = mapped_column(default=False)

   __table_args__ = (
       Index('ix_emails_fingerprint_user', 'fingerprint', 'user_id'),
   )
   ```

4. **API Endpoint**:
   ```
   POST /emails/deduplicate
   - Find duplicate emails
   - Archive or delete duplicates
   - Return count removed
   ```

### Documentation Needed

- Fingerprint algorithm explanation
- Collision handling strategy

---

## WBS-001-05: Implement Parser Similarity Matching

**Status**: NOT STARTED
**Priority**: P1
**Estimated Effort**: 20 hours
**Dependencies**: WBS-001-04

### Description

Implement similarity matching to find and match similar transactions across different email formats. Use fuzzy string matching on merchant names and descriptions to group related transactions. Handle bank name variations (e.g., "Vietcombank", "VCB", "VietCom Bank") and merchant aliases.

### Acceptance Criteria

1. Fuzzy matching on merchant names (using difflib.SequenceMatcher or fuzzywuzzy)
2. Similarity threshold configurable (80% default)
3. Group similar transactions (create transaction groups)
4. Handle bank/merchant aliases (create alias mappings)
5. Match unrecognized emails to similar recognized ones
6. Bulk update alias mappings (admin endpoint)
7. API to find similar transactions
8. Reports on similarity matching accuracy

### Files to Create

- `/backend/app/services/transaction_matcher.py` - Similarity matching service
- `/backend/app/models/matching.py` - TransactionGroup, Alias models
- `/backend/tests/test_services/test_transaction_matcher.py` - Matcher tests

### Files to Modify

- `/backend/app/api/transactions.py` - Add similarity endpoints
- `/backend/alembic/versions/004_transaction_groups.py` - Add tables

### Test Requirements

- Test fuzzy matching accuracy
- Test alias mapping
- Test transaction grouping
- Test performance (large datasets)
- **Minimum coverage**: 85%

### Technical Notes for AI Agent

1. **Fuzzy Matching**:
   ```python
   from difflib import SequenceMatcher

   def similarity(a: str, b: str) -> float:
       """Calculate similarity ratio (0-1)."""
       return SequenceMatcher(None, a.lower(), b.lower()).ratio()

   # Or use fuzzywuzzy: pip install fuzzywuzzy
   from fuzzywuzzy import fuzz
   ratio = fuzz.token_sort_ratio(merchant1, merchant2)  # 0-100
   ```

2. **Alias System**:
   ```python
   class Alias(Base):
       __tablename__ = "aliases"
       user_id: Mapped[str]
       original_name: Mapped[str]  # "VietCom Bank"
       alias_name: Mapped[str]     # "VCB"
       confidence: Mapped[float]   # 0-1
   ```

3. **Transaction Grouping**:
   - Group similar merchant names
   - Group similar amounts + merchant
   - Group by category (for pattern learning)

### Documentation Needed

- Similarity algorithm explanation
- Threshold tuning guide

---

## WBS-001-06: Implement Unrecognized Email Queue + API Endpoints

**Status**: NOT STARTED
**Priority**: P0
**Estimated Effort**: 18 hours
**Dependencies**: WBS-001-05

### Description

Implement queue system for emails that couldn't be parsed by any parser. Store unrecognized emails in `UnrecognizedEmail` table with reason for failure. Provide API endpoints to list, review, manually correct, and generate parser rules from them. UI for parser management will use these endpoints.

### Acceptance Criteria

1. `UnrecognizedEmail` model with: raw_body, parse_error, similar_transactions
2. API to list unrecognized emails (paginated, filterable)
3. API to manually categorize unrecognized email (create rule from it)
4. API to suggest parser rules (based on similar recognized emails)
5. Bulk actions: mark as ignored, delete, re-process
6. Analytics: unrecognized email rate per parser, trend over time
7. Notification system (alert when unrecognized rate > 5%)
8. Export unrecognized emails for analysis

### Files to Create

- `/backend/app/api/unrecognized_emails.py` - API endpoints
- `/backend/app/services/unrecognized_email_service.py` - Business logic
- `/backend/tests/test_api/test_unrecognized_emails.py` - API tests

### Files to Modify

- `/backend/app/models/system.py` - Enhance UnrecognizedEmail model
- `/backend/app/main.py` - Add routes
- `/backend/alembic/versions/005_unrecognized_emails.py` - Schema

### Test Requirements

- Test list/filter endpoints
- Test manual categorization
- Test rule suggestion
- Test analytics calculation
- Test bulk actions
- **Minimum coverage**: 85%

### Technical Notes for AI Agent

1. **UnrecognizedEmail Model**:
   ```python
   class UnrecognizedEmail(Base):
       __tablename__ = "unrecognized_emails"
       user_id: Mapped[str]
       email_id: Mapped[str]  # FK to emails
       raw_body: Mapped[str]
       parse_error: Mapped[str]  # Reason for failure
       parsed_attempt: Mapped[dict]  # What was extracted
       similar_transactions: Mapped[list[str]]  # Similar transaction IDs
       status: Mapped[str]  # 'pending', 'ignored', 'categorized'
       created_at: Mapped[datetime]
   ```

2. **API Endpoints**:
   ```
   GET /unrecognized-emails              - List with filters
   GET /unrecognized-emails/{id}         - Get single
   POST /unrecognized-emails/{id}/categorize - Manual categorize
   POST /unrecognized-emails/{id}/suggest-rules - Get rule suggestions
   POST /unrecognized-emails/bulk-update - Bulk operations
   GET /unrecognized-emails/analytics    - Stats
   POST /unrecognized-emails/export      - Export CSV/JSON
   ```

3. **Rule Suggestion Logic**:
   - Find similar recognized transactions
   - Suggest categorization based on similarity
   - Generate rule pattern from manual correction

### Documentation Needed

- API endpoint documentation
- Rule suggestion algorithm

---

## WBS-001-07: Implement Dynamic Parser (JSON-based) Runtime

**Status**: NOT STARTED
**Priority**: P1
**Estimated Effort**: 25 hours
**Dependencies**: WBS-001-06

### Description

Implement a JSON-based parser specification format that allows defining parsers without writing Python code. Create runtime that loads and executes these specifications. Support regex matching, field extraction, and conditional logic. Enable non-developers to create new bank parsers.

### Acceptance Criteria

1. JSON schema for parser definition
2. Parser runtime that executes JSON specs
3. Regex pattern matching for sender/subject
4. Field extraction from HTML/text using XPath/regex
5. Conditional logic (if/then rules)
6. Type conversion (string → decimal, date formatting)
7. Validation of parsed data
8. Error messages (which rule failed and why)
9. Version control for parser specs
10. Ability to test specs before publishing

### Files to Create

- `/backend/app/parsers/dynamic_parser.py` - Runtime engine
- `/backend/app/schemas/parser_spec.py` - JSON schema definitions
- `/backend/app/models/parser_spec.py` - Store parser specs in DB
- `/backend/tests/test_parsers/test_dynamic_parser.py` - Runtime tests
- `/backend/app/parsers/specs/` - Directory for example JSON specs
- `/backend/docs/parser_spec_schema.json` - JSON schema definition

### Files to Modify

- `/backend/app/parsers/registry.py` - Load dynamic parsers on startup
- `/backend/alembic/versions/006_parser_specs.py` - Add table

### Test Requirements

- Test JSON spec loading
- Test regex extraction
- Test field extraction (XPath)
- Test conditional logic
- Test type conversion
- Test error messages
- Test spec validation
- **Minimum coverage**: 80%

### Technical Notes for AI Agent

1. **Parser Spec Format (JSON)**:
   ```json
   {
     "name": "techcombank",
     "version": "1.0.0",
     "enabled": true,
     "priority": 100,
     "matchers": [
       {
         "field": "sender",
         "pattern": "techcombank|TCB",
         "type": "regex"
       },
       {
         "field": "subject",
         "pattern": "Transfer confirmation",
         "type": "substring"
       }
     ],
     "extractors": [
       {
         "name": "amount",
         "source": "html",
         "pattern": "Amount:\\s*(\\d+[.,\\d]*)",
         "type": "regex",
         "transform": "parse_vnd"
       },
       {
         "name": "merchant",
         "source": "html",
         "xpath": "//div[@class='merchant']/text()",
         "type": "xpath"
       }
     ],
     "rules": [
       {
         "if": "merchant contains 'ATM'",
         "then": {"transaction_type": "withdrawal"}
       }
     ]
   }
   ```

2. **Runtime Engine**:
   ```python
   class DynamicParser(BaseBankParser):
       def __init__(self, spec: dict):
           self.spec = spec
           self.name = spec['name']
           self.priority = spec['priority']

       async def parse(self, email_body: str) -> ParsedTransaction | None:
           # 1. Check matchers
           if not self._check_matchers(email_body):
               return None

           # 2. Extract fields
           fields = self._extract_fields(email_body)

           # 3. Apply rules
           fields = self._apply_rules(fields)

           # 4. Validate
           # 5. Return ParsedTransaction
   ```

3. **Extractor Types**:
   - `regex`: Python regex with capture groups
   - `xpath`: XPath for HTML elements
   - `substring`: Simple substring matching
   - `json_path`: For JSON emails

4. **Transforms**:
   - `parse_vnd`: Vietnamese currency → Decimal
   - `parse_vn_date`: Vietnamese date → datetime
   - `normalize_merchant`: Clean merchant name
   - `uppercase`, `lowercase`, `trim`

### Documentation Needed

- JSON schema definition
- Parser spec examples
- Custom transforms guide

---

## WBS-001-08: Implement Parser Health Monitoring

**Status**: NOT STARTED
**Priority**: P1
**Estimated Effort**: 18 hours
**Dependencies**: WBS-001-07

### Description

Implement monitoring system to track parser health: success rate, error trends, performance metrics. Monitor which parsers are used most, failure reasons, and alert when success rate drops. Store metrics in time-series database or time-based tables.

### Acceptance Criteria

1. `ParserHealthMetric` model (success count, failure count, avg_parse_time)
2. Metrics collected per: parser, date, transaction type
3. Success rate calculation (success / total >= 95%)
4. Alert when success rate < 90% (24-hour rolling window)
5. Error categorization (invalid format, missing field, timeout, etc.)
6. Performance tracking (parse time < 500ms)
7. API endpoints for health dashboard
8. Time-series charts (success rate over time)
9. Alert system (email/notification)
10. Automatic parser disabling if failure rate > 50% (safeguard)

### Files to Create

- `/backend/app/models/health.py` - Health metric models
- `/backend/app/services/health_monitor.py` - Health monitoring service
- `/backend/app/api/parser_health.py` - Health dashboard API
- `/backend/tests/test_services/test_health_monitor.py` - Monitor tests

### Files to Modify

- `/backend/app/parsers/base.py` - Add metrics collection
- `/backend/alembic/versions/007_parser_health.py` - Add tables

### Test Requirements

- Test metric collection
- Test success rate calculation
- Test alert triggering
- Test time-series aggregation
- Test auto-disabling logic
- **Minimum coverage**: 85%

### Technical Notes for AI Agent

1. **Health Metrics Model**:
   ```python
   class ParserHealthMetric(Base):
       __tablename__ = "parser_health_metrics"
       parser_name: Mapped[str]
       date: Mapped[date]
       transaction_type: Mapped[str | None]
       success_count: Mapped[int]
       failure_count: Mapped[int]
       total_time_ms: Mapped[int]  # For avg calculation

       @property
       def success_rate(self) -> float:
           total = self.success_count + self.failure_count
           return self.success_count / total if total > 0 else 0.0

       @property
       def avg_parse_time_ms(self) -> float:
           total = self.success_count + self.failure_count
           return self.total_time_ms / total if total > 0 else 0.0
   ```

2. **Metrics Collection**:
   - Collect after each parse attempt
   - Record success/failure
   - Record parse time
   - Record error reason

3. **Alert Logic**:
   ```python
   def check_parser_health(parser_name: str, user_id: str):
       # Last 24 hours
       metrics = get_metrics(parser_name, user_id, days=1)
       success_rate = sum(m.success_count) / sum(m.total_count)

       if success_rate < 0.9:
           create_alert(f"Parser {parser_name} low success rate: {success_rate}")

       if success_rate < 0.5:
           disable_parser(parser_name, user_id)
   ```

### Documentation Needed

- Health monitoring dashboard guide
- Alert configuration

---

## WBS-001-09: Create Parser Management UI (Settings → Email Parsers Page)

**Status**: NOT STARTED
**Priority**: P1
**Estimated Effort**: 20 hours
**Dependencies**: WBS-001-08

### Description

Create React UI in Settings page for managing email parsers. Display list of available parsers with status, success rate, last sync time. Allow enabling/disabling parsers, testing with sample email, viewing error history, and creating custom parsers from templates.

### Acceptance Criteria

1. Settings → Email Parsers page (new route)
2. Parser list with: name, status (enabled/disabled), success rate, last sync
3. Enable/disable toggle for each parser
4. View parser details (settings, rules, test results)
5. Test parser with sample email (paste HTML/text)
6. Error history (last 10 failures with reasons)
7. Import custom parser (JSON spec or .py file)
8. Parser template selector (guide for creating new)
9. Metrics chart (success rate over 30 days)
10. Vietnamese text throughout

### Files to Create

- `/frontend/src/pages/Settings/EmailParsers.tsx` - Page component
- `/frontend/src/components/features/EmailParsers/` - Sub-components
  - `ParserList.tsx`
  - `ParserCard.tsx`
  - `ParserDetails.tsx`
  - `ParserTester.tsx`
  - `ParserMetricsChart.tsx`
  - `ImportParserModal.tsx`
- `/frontend/src/hooks/useEmailParsers.ts` - Query hooks
- `/frontend/src/services/parserService.ts` - API service
- `/frontend/src/types/parser.ts` - TypeScript types
- `/frontend/tests/pages/Settings/EmailParsers.test.tsx` - Page tests

### Files to Modify

- `/frontend/src/pages/Settings/index.tsx` - Add route
- `/frontend/src/App.tsx` - Update routes if needed

### Test Requirements

- Render parser list
- Toggle enable/disable
- Test parser with sample
- View metrics chart
- Import parser modal
- **Minimum coverage**: 80%

### Technical Notes for AI Agent

1. **Page Layout**:
   ```
   ┌─────────────────────────────────────────┐
   │ Email Parser Management                  │
   │ [+ New Parser] [Settings]               │
   ├─────────────────────────────────────────┤
   │ Parser List:                            │
   │ ┌───────────────────────────────────┐  │
   │ │ Cake/VPBank     [Enabled] ✓       │  │
   │ │ Success: 98% | Last: 5 min ago    │  │
   │ │ [View Details] [Test] [Disable]   │  │
   │ └───────────────────────────────────┘  │
   │ ┌───────────────────────────────────┐  │
   │ │ Techcombank     [Disabled]  ✗      │  │
   │ │ Success: 92% | Last: 2h ago      │  │
   │ │ [View Details] [Test] [Enable]    │  │
   │ └───────────────────────────────────┘  │
   └─────────────────────────────────────────┘
   ```

2. **ParserCard Component**:
   ```typescript
   interface ParserCardProps {
     parser: ParserInfo;
     onEnable: (name: string) => void;
     onDisable: (name: string) => void;
     onTest: (name: string) => void;
     onViewDetails: (name: string) => void;
   }
   ```

3. **useEmailParsers Hook**:
   ```typescript
   export const useEmailParsers = () => {
     return useQuery({
       queryKey: ['email-parsers'],
       queryFn: parserService.getParserList,
     });
   };

   export const useParserMetrics = (parserName: string) => {
     return useQuery({
       queryKey: ['parser-metrics', parserName],
       queryFn: () => parserService.getMetrics(parserName),
     });
   };
   ```

4. **API Service**:
   ```typescript
   export const parserService = {
     async getParserList(): Promise<Parser[]> {},
     async getParserDetails(name: string): Promise<ParserDetails> {},
     async testParser(name: string, emailBody: string) {},
     async toggleParser(name: string, enabled: boolean) {},
     async getMetrics(name: string) {},
     async importParser(spec: unknown) {},
   };
   ```

5. **Metrics Chart**:
   - Use Recharts (LineChart)
   - X-axis: dates (30 days)
   - Y-axis: success rate %
   - Show parser health status

### Documentation Needed

- UI wireframe description
- Parser testing guide

---

## WBS-001-10: Implement Parser Template Generator

**Status**: NOT STARTED
**Priority**: P2
**Estimated Effort**: 20 hours
**Dependencies**: WBS-001-09

### Description

Implement tool to generate parser templates from sample emails. Analyze email structure (HTML, plain text), suggest field extraction patterns, and generate JSON parser specification. Guide users through definition of parser with visual feedback and validation.

### Acceptance Criteria

1. "Generate Parser" wizard with steps:
   - Upload sample email (HTML or plain text)
   - Analyze structure
   - Map fields (amount, merchant, date, etc.)
   - Set matchers (sender, subject patterns)
   - Apply rules (direction, type, category)
   - Preview and test
   - Save as new parser
2. Field extraction suggestions (regex patterns)
3. Visual field highlighting (show where pattern matches)
4. XPath extraction for HTML elements
5. Support regex and simple substring matchers
6. Test generated parser on new samples before saving
7. Generated parser rating (how many test emails it parses)
8. Save to database or export as JSON
9. Version control for generated specs
10. Share parser specs with other users (optional)

### Files to Create

- `/frontend/src/pages/ParserGenerator/` - Wizard pages
  - `index.tsx`
  - `StepUpload.tsx`
  - `StepAnalyze.tsx`
  - `StepMapFields.tsx`
  - `StepMatchers.tsx`
  - `StepRules.tsx`
  - `StepTest.tsx`
  - `StepSave.tsx`
- `/frontend/src/components/ParserGenerator/` - Helper components
  - `FieldHighlighter.tsx`
  - `RegexTester.tsx`
  - `ParserPreview.tsx`
- `/backend/app/services/parser_generator.py` - Spec generation
- `/backend/app/api/parser_generator.py` - Generator endpoints

### Files to Modify

- `/frontend/src/pages/Settings/EmailParsers.tsx` - Add "Generate" button
- `/backend/app/parsers/dynamic_parser.py` - Use generated specs

### Test Requirements

- Test email parsing and analysis
- Test field extraction suggestions
- Test regex pattern generation
- Test generated parser validation
- Test end-to-end wizard
- **Minimum coverage**: 75%

### Technical Notes for AI Agent

1. **Wizard Flow**:
   ```
   1. Upload Email
      ↓
   2. Analyze Structure (suggest fields)
      ↓
   3. Map Fields (confirm extraction patterns)
      ↓
   4. Set Matchers (sender, subject)
      ↓
   5. Apply Rules (direction, category)
      ↓
   6. Test (upload test emails)
      ↓
   7. Save or Export
   ```

2. **Field Detection**:
   - Amount: patterns like `\d+[.,]\d+` or "Amount: XXX"
   - Merchant: patterns like "To: XXX" or "Recipient: XXX"
   - Date: parse with date-fns
   - Reference: "Ref:", "Transaction ID:"

3. **Regex Suggestion**:
   ```python
   def suggest_regex_patterns(email_body: str) -> dict:
       suggestions = {
           'amount': [
               r'\d+[.,]\d+',  # Basic number
               r'VND\s*(\d+[.,]\d+)',  # With currency
               r'Amount.*?(\d+[.,]\d+)',  # With label
           ],
           'merchant': [
               r'To:\s*([\w\s]+)',
               r'Recipient:\s*([\w\s]+)',
           ],
           'date': [
               r'(\d{2}/\d{2}/\d{4})',  # DD/MM/YYYY
               r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
           ]
       }
       return suggestions
   ```

4. **Frontend Steps**:
   - Step 1: Drag-drop or paste email
   - Step 2: Show detected fields, suggest patterns
   - Step 3: User confirms/adjusts patterns
   - Step 4: Add matchers (sender, subject)
   - Step 5: Configure rules (if/then)
   - Step 6: Test on multiple emails
   - Step 7: Save as new parser

### Documentation Needed

- Wizard flow documentation
- Regex pattern guide

---

## Summary

**Total Feature Effort**: 200-250 hours (10 tasks)

**Critical Path**: WBS-001-01 → WBS-001-02 → WBS-001-03 → WBS-001-06

**Can Parallelize**:
- WBS-001-04, 001-05 (can run after 001-03)
- WBS-001-07, 001-08 (can run in parallel)
- WBS-001-09, 001-10 (can run after 001-08)

**Outcome**:
- Complete email parsing system
- Support for multiple banks (extensible)
- Dashboard for parser management
- Foundation for WBS-002 (auto-categorization)
