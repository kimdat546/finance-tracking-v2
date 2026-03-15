# WBS-006: Client-Side Email Processing (Privacy-First)

**Feature**: Client-Side Email Processing - Process emails in user's browser
**Status**: NOT STARTED
**Priority**: P2 (Medium)
**Total Effort**: 100-140 hours (7 tasks)
**Dependencies**: WBS-001
**Created**: 2026-03-15

---

## Overview

Privacy-focused email processing: users grant Gmail access only to browser, emails never reach backend. Frontend parses emails locally, sends only extracted transactions to backend.

---

## WBS-006-01: Create TypeScript Parser Engine

**Effort**: 20 hours | **Dependencies**: WBS-001

Port Python `BaseBankParser` and parser utilities to TypeScript. Create reusable parser framework in browser.

**Acceptance Criteria**:
- Base parser interface (abstract)
- Parser registry for managing parsers
- Vietnamese currency utilities (parse_vnd, format_vnd)
- Date parsing (Vietnamese format)
- Email body parsing (HTML/plain text)
- Error handling and logging
- Type-safe (TypeScript strict mode)
- Unit tests (vitest)
- Performance: parse email < 100ms
- Test coverage 85%

**Files**:
- `/frontend/src/services/parsers/BaseParser.ts` - Abstract base
- `/frontend/src/services/parsers/ParserRegistry.ts` - Registry
- `/frontend/src/utils/vn-currency.ts` - VN utilities
- `/frontend/src/utils/date-utils.ts` - Date parsing
- `/frontend/tests/parsers/BaseParser.test.ts`
- `/frontend/tests/utils/vn-currency.test.ts`

**Technical Notes**:
```typescript
// BaseParser.ts
export interface ParsedTransaction {
  amount: number;
  merchant: string;
  description: string;
  date: Date;
  transactionType: 'income' | 'expense' | 'transfer';
  direction: 'incoming' | 'outgoing';
  referenceNumber?: string;
}

export abstract class BaseParser {
  abstract name: string;
  abstract priority: number;

  abstract parse(emailBody: string): Promise<ParsedTransaction | null>;

  protected parseVND(text: string): number {
    // Parse Vietnamese: "1.234.567,89 đ" → 1234567.89
  }

  protected parseVNDate(text: string): Date {
    // Parse Vietnamese: "14/03/2026, 22:28:37"
  }
}

// ParserRegistry.ts
export class ParserRegistry {
  private parsers: BaseParser[] = [];

  register(parser: BaseParser): void {
    this.parsers.push(parser);
    this.parsers.sort((a, b) => b.priority - a.priority);
  }

  async parse(emailBody: string): Promise<ParsedTransaction | null> {
    for (const parser of this.parsers) {
      const result = await parser.parse(emailBody);
      if (result) return result;
    }
    return null;
  }
}
```

---

## WBS-006-02: Create TypeScript Cake/VPBank Parser

**Effort**: 18 hours | **Dependencies**: WBS-006-01

Port Python Cake/VPBank parser to TypeScript. Support HTML and plain text emails.

**Acceptance Criteria**:
- Parse HTML emails (BeautifulSoup → cheerio)
- Parse plain text fallback
- Extract: amount, merchant, date, direction
- Handle Vietnamese formats
- Direction detection (incoming/outgoing)
- Error handling and validation
- Unit tests with real email fixtures
- 95%+ parsing accuracy
- Test coverage 90%

**Files**:
- `/frontend/src/services/parsers/CakeVPBankParser.ts`
- `/frontend/src/services/parsers/parsers/cake-vpbank.ts` - Parser class
- `/frontend/tests/parsers/CakeVPBankParser.test.ts`
- `/frontend/tests/parsers/fixtures/cake-incoming.html`
- `/frontend/tests/parsers/fixtures/cake-outgoing.txt`

**Technical Notes**:
```typescript
import cheerio from 'cheerio';

export class CakeVPBankParser extends BaseParser {
  name = 'cake-vpbank';
  priority = 100;

  async parse(emailBody: string): Promise<ParsedTransaction | null> {
    // Try HTML parsing first
    let transaction = this.parseHTML(emailBody);

    // Fallback to plain text
    if (!transaction) {
      transaction = this.parsePlainText(emailBody);
    }

    if (!transaction) return null;

    // Validate
    if (!transaction.amount || !transaction.date) return null;

    return transaction;
  }

  private parseHTML(emailBody: string): ParsedTransaction | null {
    const $ = cheerio.load(emailBody);

    // Extract fields using CSS selectors
    const amount = this.parseVND(
      $('div:contains("Amount")').text()
    );

    const merchant = $('span.merchant').text();
    const dateStr = $('div:contains("Time")').text();

    return {
      amount,
      merchant,
      date: this.parseVNDate(dateStr),
      // ... more fields
    };
  }

  private parsePlainText(emailBody: string): ParsedTransaction | null {
    // Regex-based extraction for plain text
    const amountMatch = emailBody.match(/Amount:\\s*([\d.]+[,\\d]*)/);
    if (!amountMatch) return null;

    return {
      amount: this.parseVND(amountMatch[1]),
      // ... more fields
    };
  }
}
```

---

## WBS-006-03: Implement Client-Side Gmail API Integration

**Effort**: 18 hours | **Dependencies**: WBS-006-02

Implement Gmail OAuth in browser. Fetch emails directly from frontend, no backend involved.

**Acceptance Criteria**:
- OAuth2 authorization in browser
- Token management (store in localStorage/IndexedDB)
- Fetch emails using Gmail API (messages.list)
- Filter by labels
- Batch fetch (1000+ emails)
- Handle rate limiting (429 responses)
- Incremental sync with historyId
- Error handling (401, 403, 503)
- Security: tokens never sent to backend
- Test coverage 75%

**Files**:
- `/frontend/src/services/gmail/GmailClient.ts`
- `/frontend/src/services/gmail/OAuthManager.ts`
- `/frontend/src/hooks/useGmailAuth.ts`
- `/frontend/tests/services/gmail/GmailClient.test.ts`

**Technical Notes**:
```typescript
export class OAuthManager {
  private clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  private redirectUri = `${window.location.origin}/oauth/callback`;

  async authorize(): Promise<string> {
    // Build authorization URL
    const authUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
    authUrl.searchParams.set('client_id', this.clientId);
    authUrl.searchParams.set('redirect_uri', this.redirectUri);
    authUrl.searchParams.set('response_type', 'code');
    authUrl.searchParams.set('scope', 'https://www.googleapis.com/auth/gmail.readonly');
    authUrl.searchParams.set('access_type', 'offline');

    // Redirect to Google
    window.location.href = authUrl.toString();
  }

  async getAccessToken(): Promise<string> {
    const stored = localStorage.getItem('gmail_access_token');
    if (stored) return stored;

    // Token not found, need to authorize
    throw new Error('Not authenticated');
  }
}

export class GmailClient {
  private oauth: OAuthManager;
  private baseUrl = 'https://www.googleapis.com/gmail/v1/users/me';

  async fetchMessages(query: string): Promise<any[]> {
    const token = await this.oauth.getAccessToken();

    const response = await fetch(
      `${this.baseUrl}/messages?q=${encodeURIComponent(query)}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      if (response.status === 429) {
        // Rate limit, retry later
        throw new Error('Rate limited');
      }
      throw new Error(`Gmail API error: ${response.status}`);
    }

    return response.json();
  }

  async getMessageFull(messageId: string): Promise<any> {
    const token = await this.oauth.getAccessToken();

    const response = await fetch(
      `${this.baseUrl}/messages/${messageId}?format=full`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    return response.json();
  }
}
```

---

## WBS-006-04: Implement Transaction Ingest API Endpoint

**Effort**: 14 hours | **Dependencies**: WBS-006-03

Backend endpoint to receive parsed transactions from frontend. Validate and store without raw email.

**Acceptance Criteria**:
- POST /transactions/ingest endpoint
- Accept batch of transactions
- Validate: amount, merchant, date, category
- Prevent duplicates (fingerprinting)
- Store without raw email body
- Return stored transactions with IDs
- Error handling (validation, duplicates)
- Rate limiting (1000 tx per minute max)
- Log ingestion source (client-side)
- Test coverage 85%

**Files**:
- `/backend/app/api/ingest.py`
- `/backend/app/schemas/ingest.py`
- `/backend/app/services/ingest_service.py`
- `/backend/tests/test_api/test_ingest.py`

**Technical Notes**:
```python
class TransactionIngestRequest(BaseModel):
    """Batch of transactions to ingest."""
    transactions: list[TransactionIngestItem]
    source: str = "client-side"  # or "email-sync"

class TransactionIngestItem(BaseModel):
    merchant: str
    amount: Decimal
    description: str
    transaction_date: datetime
    transaction_type: str  # income, expense, transfer
    direction: str  # incoming, outgoing
    reference_number: str | None = None
    account_id: str | None = None

@router.post("/transactions/ingest")
async def ingest_transactions(
    request: TransactionIngestRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ingest batch of client-parsed transactions."""
    service = IngestService(session)

    # Validate and store
    stored = []
    for item in request.transactions:
        # Check for duplicate (fingerprint)
        existing = await service.check_duplicate(current_user.id, item)
        if existing:
            stored.append(existing)
            continue

        # Create transaction
        tx = Transaction(
            user_id=current_user.id,
            merchant=item.merchant,
            amount=item.amount,
            description=item.description,
            transaction_date=item.transaction_date,
            transaction_type=item.transaction_type,
            direction=item.direction,
            reference_number=item.reference_number,
            account_id=item.account_id,
            source='client-side',
        )
        session.add(tx)
        stored.append(tx)

    await session.commit()
    return {'stored': len(stored), 'transactions': stored}
```

---

## WBS-006-05: Create Sync UI

**Effort**: 16 hours | **Dependencies**: WBS-006-04

React components for sync UI: login, progress indicator, results summary.

**Acceptance Criteria**:
- Gmail login button (OAuth flow)
- Email fetching progress (count, %)
- Email parsing progress (showing parser)
- Results summary: total fetched, parsed, errors
- List of errors (with details)
- Option to retry failed emails
- Time elapsed
- Speed: X emails/min
- Cancel button (stop sync)
- Toast notifications (success/error)

**Files**:
- `/frontend/src/pages/Sync/EmailSync.tsx`
- `/frontend/src/components/features/Sync/`
  - `GmailLoginButton.tsx`
  - `SyncProgress.tsx`
  - `ParsingProgress.tsx`
  - `SyncResults.tsx`
  - `ErrorList.tsx`
- `/frontend/src/hooks/useEmailSync.ts`
- `/frontend/src/hooks/useGmailAuth.ts`

**Technical Notes**:
```typescript
export const EmailSync: React.FC = () => {
  const [syncState, setSyncState] = React.useState<'idle' | 'fetching' | 'parsing' | 'done'>('idle');
  const [progress, setProgress] = React.useState({
    emailsFetched: 0,
    totalEmails: 0,
    emailsParsed: 0,
    errors: [] as SyncError[],
  });

  const handleSync = async () => {
    setSyncState('fetching');

    // 1. Fetch emails from Gmail
    const emails = await gmailClient.fetchEmails();
    setProgress(p => ({ ...p, totalEmails: emails.length }));

    // 2. Parse emails
    setSyncState('parsing');
    const transactions = [];
    for (const email of emails) {
      try {
        const tx = await parserRegistry.parse(email.body);
        if (tx) {
          transactions.push(tx);
          setProgress(p => ({
            ...p,
            emailsParsed: p.emailsParsed + 1,
          }));
        }
      } catch (e) {
        setProgress(p => ({
          ...p,
          errors: [...p.errors, { email: email.id, error: e.message }],
        }));
      }

      // Update count
      setProgress(p => ({
        ...p,
        emailsFetched: p.emailsFetched + 1,
      }));
    }

    // 3. Send to backend
    await ingestService.ingestTransactions(transactions);
    setSyncState('done');
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Gmail Sync</h1>

      {syncState === 'idle' && (
        <button onClick={handleSync} className="btn btn-primary">
          Start Sync from Gmail
        </button>
      )}

      {syncState === 'fetching' && (
        <SyncProgress
          emailsFetched={progress.emailsFetched}
          totalEmails={progress.totalEmails}
        />
      )}

      {syncState === 'parsing' && (
        <ParsingProgress
          emailsParsed={progress.emailsParsed}
          totalEmails={progress.totalEmails}
        />
      )}

      {syncState === 'done' && (
        <SyncResults
          totalFetched={progress.totalEmails}
          totalParsed={progress.emailsParsed}
          errors={progress.errors}
          onRetry={handleSync}
        />
      )}
    </div>
  );
};
```

---

## WBS-006-06: Implement Dynamic Parser Runtime in TypeScript

**Effort**: 18 hours | **Dependencies**: WBS-006-01

Create TypeScript runtime that executes JSON parser specifications (like WBS-001-07 in backend).

**Acceptance Criteria**:
- Load JSON parser specifications
- Execute regex/XPath matchers
- Extract fields from HTML/text
- Apply conditional rules
- Type conversion (string → number, date)
- Error messages (which rule failed)
- Test specification before using
- Performance: parse < 200ms
- Support both HTML and plain text
- Test coverage 80%

**Files**:
- `/frontend/src/services/parsers/DynamicParser.ts`
- `/frontend/src/services/parsers/ParserExecutor.ts`
- `/frontend/src/types/parser-spec.ts`
- `/frontend/tests/parsers/DynamicParser.test.ts`

---

## WBS-006-07: Create Onboarding Flow UI

**Effort**: 16 hours | **Dependencies**: WBS-006-05

Onboarding wizard: choose sync method (client-side vs server-side), connect Gmail, set up preferences.

**Acceptance Criteria**:
- Welcome screen
- Choose sync method (client-side, server-side, manual)
- Gmail connection (for chosen method)
- Bank selection (which banks to support)
- Category setup (or use defaults)
- First sync
- Success screen
- Skip option (setup later)
- Multi-step form with progress
- Save preferences

**Files**:
- `/frontend/src/pages/Onboarding/` - Onboarding pages
  - `index.tsx`
  - `StepWelcome.tsx`
  - `StepSyncMethod.tsx`
  - `StepGmailConnect.tsx`
  - `StepBanks.tsx`
  - `StepCategories.tsx`
  - `StepFirstSync.tsx`
  - `StepComplete.tsx`
- `/frontend/src/hooks/useOnboarding.ts`

---

## Summary

**Total Effort**: 100-140 hours

**Key Benefits**:
- User privacy: emails never leave browser
- Better performance: parsing in parallel
- Offline capability: parse without internet
- No backend storage of raw emails

**Trade-offs**:
- More code in frontend
- User must authorize Gmail from browser
- No server-side email re-processing

**Implementation Sequence**:
1. WBS-006-01: TypeScript parser engine
2. WBS-006-02: Cake/VPBank parser
3. WBS-006-03: Gmail API client
4. WBS-006-04: Ingest endpoint
5. WBS-006-05: Sync UI
6. WBS-006-06: Dynamic parser runtime
7. WBS-006-07: Onboarding flow

---

*Privacy-first architecture allowing users full control over their email data.*
