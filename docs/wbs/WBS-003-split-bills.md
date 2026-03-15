# WBS-003: Split Bills / Chia Tiền

**Feature**: Split Bills - Shared Expenses Management
**Status**: NOT STARTED
**Priority**: P1 (High)
**Total Effort**: 100-130 hours (8 tasks)
**Dependencies**: WBS-001, WBS-002
**Created**: 2026-03-15

---

## Overview

Chia tiền (split bills) system for tracking shared expenses. Users can create split bills from transactions, track who owes whom, and settle debts. Integrates with contacts and transaction categorization.

---

## WBS-003-01: Implement Contacts CRUD API

**Status**: NOT STARTED
**Effort**: 12 hours

### Description

Create Contact model and API for managing contacts (people involved in split bills). Store contact info: name, phone, email. Track balance with each contact (who owes whom). API for CRUD operations and balance queries.

### Acceptance Criteria

1. Contact model with: name, phone, email, user_id, notes
2. Create/read/update/delete endpoints
3. List contacts with pagination
4. Search contacts by name/phone
5. Get balance summary per contact
6. Bulk import contacts (CSV)
7. Delete contact (cascade to split bills)
8. Contact history (who paid you, you paid them)
9. Mark contacts as favorites
10. Test coverage 85%

### Files to Create

- `/backend/app/models/social.py` - Contact model (enhance existing)
- `/backend/app/services/contact_service.py` - Contact logic
- `/backend/app/api/contacts.py` - API endpoints
- `/backend/tests/test_api/test_contacts.py` - API tests

### Files to Modify

- `/backend/alembic/versions/010_contacts.py` - Add table/indexes

### Technical Notes

- Contact model:
  ```python
  class Contact(Base):
      __tablename__ = "contacts"
      user_id: Mapped[str]
      name: Mapped[str]
      phone: Mapped[str | None]
      email: Mapped[str | None]
      notes: Mapped[str | None]
      is_favorite: Mapped[bool]
      created_at: Mapped[datetime]
  ```
- API: GET/POST /contacts, PUT/DELETE /contacts/{id}
- Balance = sum(user paid) - sum(user received)

---

## WBS-003-02: Implement Split Bill Creation API

**Status**: NOT STARTED
**Effort**: 15 hours

### Description

Create SplitBill model and API for creating split bills. Support equal split, exact amounts, and percentage split. From a transaction, create split with multiple participants. Track who is involved and how much each owes.

### Acceptance Criteria

1. SplitBill model with: transaction_id, category, status
2. SplitParticipant model: contact_id, amount_owed, amount_paid
3. Split types: equal, exact, percentage
4. Create from existing transaction
5. Create standalone split bill
6. Calculate settlements (who pays whom)
7. Mark split as settled/completed
8. Edit split (recalculate if needed)
9. Delete split (return to original transaction)
10. Validation (amounts add up)

### Files to Create

- `/backend/app/models/social.py` - Enhance with split models
- `/backend/app/services/split_service.py` - Split logic
- `/backend/app/schemas/split.py` - Split schemas
- `/backend/app/api/splits.py` - API endpoints
- `/backend/tests/test_api/test_splits.py` - Tests

### Files to Modify

- `/backend/alembic/versions/011_split_bills.py` - Tables

### Technical Notes

- SplitBill schema:
  ```python
  class CreateSplitRequest(BaseModel):
      transaction_id: str | None  # From existing
      description: str
      amount: Decimal
      paid_by: str  # Contact ID
      split_type: str  # "equal", "exact", "percentage"
      participants: list[ParticipantInput]  # {contact_id, amount}
      category: str
  ```
- Calculation example (equal split of 300k among 3 people):
  - Each owes: 100k
  - Participant amounts reflect what they owe

---

## WBS-003-03: Implement Auto-Settlement Detection

**Status**: NOT STARTED
**Effort**: 14 hours

### Description

Detect when incoming transactions settle outstanding split bills. Match incoming transfers from contacts to their outstanding debts automatically. Calculate net balances and settlement progress.

### Acceptance Criteria

1. Match incoming transfer amount to outstanding debt
2. Handle partial settlements (debt > payment)
3. Handle overpayment (payment > debt)
4. Mark split as settled when fully paid
5. Detect settlement by: amount, sender, date proximity
6. Manual settlement override (mark settled manually)
7. Settlement history tracking
8. Suggest settlement for low-confidence matches
9. Batch settlement matching
10. API to confirm auto-detected settlements

### Files to Create

- `/backend/app/services/settlement_service.py` - Settlement logic
- `/backend/app/api/settlements.py` - Settlement endpoints

### Files to Modify

- `/backend/app/services/email_sync_service.py` - Auto-detect on sync
- `/backend/app/models/social.py` - Add settlement status

### Technical Notes

- Match algorithm:
  1. Get outstanding splits from contact
  2. Check recent incoming transactions from that contact
  3. If amount matches/close, mark as settlement
  4. Confidence score based on amount match accuracy
- Settlement statuses: pending, partial, settled, disputed

---

## WBS-003-04: Implement Net Balance Calculation

**Status**: NOT STARTED
**Effort**: 12 hours

### Description

Calculate net balance between user and each contact. From list of split bills and settlements, compute who owes whom and how much in aggregate. Provide different views: money you owe, money owed to you.

### Acceptance Criteria

1. Net balance per contact (positive = they owe, negative = you owe)
2. Aggregate balance (across all contacts)
3. Breakdown by split bill (detailed view)
4. Exclude settled bills from balance
5. High-precision Decimal arithmetic
6. Timezone handling (all in UTC)
7. API endpoint for net balances
8. Report: net balance over time (chart data)
9. Currency support (VND, USD)
10. Caching (recalculate max once per day)

### Files to Create

- `/backend/app/services/balance_calculator.py` - Balance logic

### Files to Modify

- `/backend/app/api/splits.py` - Add balance endpoints

### Technical Notes

- Query all splits/settlements for user + contact
- Sum amounts, exclude settled
- Result: net balance (positive = they owe, negative = you owe)
- Cache in Redis with 24h TTL

---

## WBS-003-05: Create Contacts Management UI

**Status**: NOT STARTED
**Effort**: 14 hours

### Description

React UI for managing contacts. List contacts with filters, create/edit/delete modals, search. Show contact balance, transaction history, and options to create split bills with them.

### Acceptance Criteria

1. Contacts list page
2. Search/filter (name, phone)
3. Create contact modal (form)
4. Edit contact modal
5. Delete with confirmation
6. Quick contact creation (from split bill form)
7. Show balance per contact (money you owe/they owe)
8. Show recent transactions with contact
9. Contact details page (full history)
10. Bulk actions (export, delete multiple)

### Files to Create

- `/frontend/src/pages/Contacts/` - Contacts pages
  - `ContactsList.tsx`
  - `ContactDetail.tsx`
- `/frontend/src/components/features/Contacts/` - Components
  - `ContactCard.tsx`
  - `ContactForm.tsx`
  - `ContactBalanceBadge.tsx`
- `/frontend/src/hooks/useContacts.ts` - Queries
- `/frontend/src/services/contactService.ts` - API

### Test Requirements

- Render contacts list
- Create/edit/delete contact
- Search functionality
- Display balance
- 80% coverage

---

## WBS-003-06: Create Split Bill Creation UI

**Status**: NOT STARTED
**Effort**: 16 hours

### Description

React component for creating split bills. Multi-step form: select transaction, choose split type, add participants, configure amounts, preview, confirm. Support from transaction or standalone creation.

### Acceptance Criteria

1. "Split this transaction" button on transaction detail
2. Split creation wizard (multi-step)
3. Step 1: Choose split type (equal/exact/percentage)
4. Step 2: Add participants (select from contacts)
5. Step 3: Configure amounts (auto-calculate)
6. Step 4: Preview settlement breakdown
7. Step 5: Confirm and create
8. Quick split (click equal split from transaction)
9. Standalone split creation
10. Show calculation/verification

### Files to Create

- `/frontend/src/pages/Splits/` - Split pages
  - `CreateSplit.tsx`
  - `SplitWizard.tsx`
- `/frontend/src/components/features/Splits/` - Components
  - `SplitTypeSelector.tsx`
  - `ParticipantInput.tsx`
  - `AmountCalculator.tsx`
  - `SplitPreview.tsx`
- `/frontend/src/hooks/useSplits.ts`
- `/frontend/src/services/splitService.ts`

### Technical Notes

- Wizard state management (Zustand store)
- Calculate equal split: total / participant_count
- Calculate percentage: (amount * percentage) / 100
- Validation: amounts must sum to total
- UI: step indicator, progress bar

---

## WBS-003-07: Create Split Bill Dashboard

**Status**: NOT STARTED
**Effort**: 16 hours

### Description

Dashboard showing user's split bill status. View outstanding debts, who owes money, settlement progress, and history. Charts showing owed amounts by contact and settlement trends.

### Acceptance Criteria

1. Dashboard page showing:
   - Money you owe (total + by contact)
   - Money owed to you (total + by contact)
   - Pending splits (% settled)
2. Settlement progress (how much settled)
3. List of unsettled splits (with action buttons)
4. "Settle now" button (auto-generated payment instructions)
5. Settlement history (who paid whom, when)
6. Charts: breakdown by contact (bar/pie)
7. Trends: settlement rate over time
8. Actions: settle, defer, ignore split
9. Notifications (overdue splits)
10. Export report

### Files to Create

- `/frontend/src/pages/Dashboard/SplitBills.tsx` - Dashboard page
- `/frontend/src/components/features/Dashboard/` - Dashboard components
  - `SplitSummaryCards.tsx`
  - `OutstandingDebtsTable.tsx`
  - `SettlementTrendsChart.tsx`
  - `ContactBalanceChart.tsx`

### Test Requirements

- Render dashboard
- Display balances
- Show charts
- List unsettled splits
- 80% coverage

---

## WBS-003-08: Implement Split Bill Reminders

**Status**: NOT STARTED
**Effort**: 13 hours

### Description

Reminder system for overdue split bills. Send notifications when debt > 3 days old, escalate after 7 days, 14 days. Support email/push/in-app notifications. Configurable per contact.

### Acceptance Criteria

1. Notification model (track sent reminders)
2. Send reminder when debt > 3 days
3. Escalate: 7 days (more urgent), 14 days (critical)
4. Don't send > 1 reminder per 7 days (avoid spam)
5. Configurable per contact (disable for certain people)
6. Email notifications with settlement link
7. In-app notification/toast
8. Batch job to send due reminders
9. Mark reminder as sent/not sent
10. Unsubscribe option

### Files to Create

- `/backend/app/services/reminder_service.py` - Reminder logic
- `/backend/app/jobs/reminder_job.py` - Scheduled job (APScheduler)
- `/backend/tests/test_jobs/test_reminder_job.py` - Job tests

### Files to Modify

- `/backend/app/main.py` - Register scheduled job
- `/backend/app/models/social.py` - Add notification tracking

### Technical Notes

- Job runs daily (APScheduler)
- Query splits: status='pending' AND created_at < (now - 3 days)
- Check: last_reminder_sent < (now - 7 days)
- Send notification + record in DB
- Email template includes: amount, contact, payment method

---

## Summary

**Total Effort**: 100-130 hours

**Critical Path**: WBS-003-01 → WBS-003-02 → WBS-003-04

**Outcome**: Complete split bills system with UI and automation

---

*Detailed implementation notes and code examples provided for each task above.*
