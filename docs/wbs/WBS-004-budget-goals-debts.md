# WBS-004: Budget / Goals / Debts / Subscriptions

**Feature**: Financial Planning - Budgets, Goals, Debts, Subscriptions
**Status**: NOT STARTED
**Priority**: P1 (High)
**Total Effort**: 150-180 hours (10 tasks)
**Dependencies**: WBS-001, WBS-002
**Created**: 2026-03-15

---

## WBS-004-01: Implement Budget CRUD API + Spending Calculation

**Effort**: 16 hours | **Dependencies**: WBS-002

Budget model with period (monthly/yearly), category-based limits. Calculate spending per category using transactions. API for CRUD and spending queries.

**Acceptance Criteria**:
- Budget model: period, amount, category, status
- Create/read/update/delete endpoints
- Calculate spending per category (sum transactions)
- Handle budget vs actual comparison
- Support multiple budgets per category
- Archive old budgets
- Performance: calculate spending < 500ms
- Test coverage 85%

**Files**:
- `/backend/app/models/planning.py` - Budget model
- `/backend/app/services/budget_service.py`
- `/backend/app/api/budgets.py`
- `/backend/tests/test_api/test_budgets.py`

**Technical Notes**:
```python
class Budget(Base):
    __tablename__ = "budgets"
    user_id: Mapped[str]
    category_id: Mapped[str]  # Can be None for overall budget
    amount: Mapped[Decimal]
    period: Mapped[str]  # "monthly", "yearly"
    start_date: Mapped[date]
    end_date: Mapped[date | None]
    enabled: Mapped[bool]

# Spending calculation:
# SELECT SUM(amount) FROM transactions
# WHERE user_id = ? AND category_id = ?
# AND transaction_date BETWEEN budget.start_date AND budget.end_date
```

---

## WBS-004-02: Implement Budget Alerts

**Effort**: 12 hours | **Dependencies**: WBS-004-01

Alert system for budget thresholds (80% spent, 100% exceeded). Send notifications, record alerts in database.

**Acceptance Criteria**:
- Alert at 80%, 100%, 120% of budget
- Email notifications
- In-app notifications
- Disable/snooze alerts per budget
- Track alert history
- Don't spam (max 1 alert per day per budget)
- Configurable thresholds
- Test coverage 80%

**Files**:
- `/backend/app/services/budget_alert_service.py`
- `/backend/app/jobs/budget_alert_job.py`
- `/backend/tests/test_jobs/test_budget_alerts.py`

---

## WBS-004-03: Implement Goals CRUD API + Progress Tracking

**Effort**: 14 hours | **Dependencies**: WBS-001

Financial goal model with target amount and date. Track progress toward goal using savings/investments.

**Acceptance Criteria**:
- Goal model: title, target_amount, target_date, category
- Create/read/update/delete endpoints
- Calculate progress (amount saved / target_amount)
- Support multiple goals
- Milestone tracking (25%, 50%, 75%)
- Goal status: active, completed, abandoned
- Recurring goals (annual savings)
- Time-based projections (save X/month to reach goal)
- Test coverage 85%

**Files**:
- `/backend/app/models/planning.py` - Goal model
- `/backend/app/services/goal_service.py`
- `/backend/app/api/goals.py`
- `/backend/tests/test_api/test_goals.py`

**Technical Notes**:
```python
class Goal(Base):
    __tablename__ = "goals"
    user_id: Mapped[str]
    title: Mapped[str]
    target_amount: Mapped[Decimal]
    target_date: Mapped[date]
    category: Mapped[str]  # savings, investment, etc.
    current_amount: Mapped[Decimal] = default(0)
    status: Mapped[str]  # "active", "completed", "abandoned"

# Progress = current_amount / target_amount
# Time remaining = days until target_date
# Required monthly savings = (target_amount - current_amount) / months_remaining
```

---

## WBS-004-04: Implement Debt Tracker API

**Effort**: 15 hours | **Dependencies**: WBS-001

Track loans and debts with interest rates and payment schedules. Calculate remaining balance, interest accrued, and next payment due.

**Acceptance Criteria**:
- Debt model: principal, interest_rate, start_date, term_months
- Repayment model: date_paid, amount_paid
- Calculate interest accrued (simple or compound)
- Calculate remaining balance
- Payment schedule generation
- Track overdue payments
- Support different debt types (loan, credit card)
- Debt consolidation support (combine multiple debts)
- Test coverage 85%

**Files**:
- `/backend/app/models/planning.py` - Debt, Repayment models
- `/backend/app/services/debt_service.py`
- `/backend/app/api/debts.py`
- `/backend/tests/test_api/test_debts.py`

**Technical Notes**:
```python
class Debt(Base):
    __tablename__ = "debts"
    user_id: Mapped[str]
    creditor_name: Mapped[str]
    principal: Mapped[Decimal]
    interest_rate: Mapped[float]  # Annual %
    start_date: Mapped[date]
    term_months: Mapped[int]
    payment_amount: Mapped[Decimal]  # Monthly payment

# Interest calculation:
# Simple: interest = principal * rate * (term_months/12)
# Compound: interest = principal * (1 + rate)^(term_months/12) - principal
```

---

## WBS-004-05: Implement Subscription Detection

**Effort**: 14 hours | **Dependencies**: WBS-002

Auto-detect recurring transactions (subscriptions). Analyze transaction history for patterns. Identify monthly, yearly, and irregular recurring charges.

**Acceptance Criteria**:
- Analyze last 90 days of transactions
- Detect recurring patterns (same merchant, similar amounts)
- Calculate recurrence: monthly, yearly, custom
- Confidence score (how sure it's recurring)
- Filter out false positives (grocery stores, etc.)
- User confirmation (approve detected subscriptions)
- Mark as subscription in transaction
- Notification for new detected subscriptions
- Test coverage 80%

**Files**:
- `/backend/app/services/subscription_detector.py`
- `/backend/app/api/subscription_detector.py`
- `/backend/tests/test_services/test_subscription_detector.py`

**Technical Notes**:
```python
def detect_subscriptions(user_id: str, days: int = 90):
    """Find recurring transactions."""
    transactions = get_transactions(user_id, days)

    # Group by merchant
    grouped = defaultdict(list)
    for t in transactions:
        grouped[t.merchant].append(t)

    subscriptions = []
    for merchant, txns in grouped.items():
        if len(txns) >= 2:  # At least 2 occurrences
            # Analyze recurrence
            dates = sorted([t.created_at for t in txns])
            intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]

            # Check if regular (30±2 days, 365±5 days, etc.)
            if is_regular_interval(intervals):
                subscriptions.append({
                    'merchant': merchant,
                    'amount': statistics.mean([t.amount for t in txns]),
                    'interval': calculate_interval(intervals),
                    'confidence': confidence_score(txns),
                })

    return subscriptions
```

---

## WBS-004-06: Implement Subscription Management API

**Effort**: 12 hours | **Dependencies**: WBS-004-05

CRUD API for managing subscriptions. Create, update, cancel subscriptions. Track renewal dates and upcoming charges.

**Acceptance Criteria**:
- Subscription model: merchant, amount, frequency, next_renewal
- Create/read/update/delete endpoints
- Mark as active/paused/cancelled
- Calculate total annual cost
- Renewal date calculation
- Upcoming renewals list
- Cost tracking (spend on subscriptions)
- Bulk actions (pause all, cancel all)
- Test coverage 85%

**Files**:
- `/backend/app/models/planning.py` - Subscription model
- `/backend/app/services/subscription_service.py`
- `/backend/app/api/subscriptions.py`
- `/backend/tests/test_api/test_subscriptions.py`

---

## WBS-004-07: Create Budget Management UI

**Effort**: 16 hours | **Dependencies**: WBS-004-02

Budget page showing active budgets, spending vs limit, alerts. Create/edit/delete budgets. Visual progress bars and alerts.

**Acceptance Criteria**:
- Budgets list with progress bars
- Create budget modal (category, amount, period)
- Edit budget dialog
- Delete with confirmation
- Spending breakdown (show transactions in budget)
- Alert notifications (toast for 80%, 100%)
- Visual indicators (red for over budget)
- Compare to previous period
- Recommendations (budgets you're over/under)
- Vietnamese labels

**Files**:
- `/frontend/src/pages/Budgets/BudgetList.tsx`
- `/frontend/src/components/features/Budgets/`
  - `BudgetCard.tsx`
  - `BudgetForm.tsx`
  - `SpendingBreakdown.tsx`
  - `AlertNotifications.tsx`
- `/frontend/src/hooks/useBudgets.ts`

---

## WBS-004-08: Create Goals UI

**Effort**: 14 hours | **Dependencies**: WBS-004-03

Goals page showing progress toward financial goals. Track milestones, time remaining, required monthly savings.

**Acceptance Criteria**:
- Goals list with progress bars/circles
- Create goal modal (title, amount, deadline)
- Goal detail page (progress, milestones, history)
- Edit goal dialog
- Delete goal with confirmation
- Progress visualization (25%, 50%, 75%, 100%)
- Time remaining countdown
- Monthly savings required calculation
- Celebration when goal reached
- Goal recommendations

**Files**:
- `/frontend/src/pages/Goals/GoalsList.tsx`
- `/frontend/src/pages/Goals/GoalDetail.tsx`
- `/frontend/src/components/features/Goals/`
  - `GoalCard.tsx`
  - `GoalForm.tsx`
  - `ProgressCircle.tsx`
  - `MilestoneTracker.tsx`
- `/frontend/src/hooks/useGoals.ts`

---

## WBS-004-09: Create Debt Tracker UI

**Effort**: 14 hours | **Dependencies**: WBS-004-04

Debt management page showing all debts, repayment schedules, remaining balance. Track payment progress and interest.

**Acceptance Criteria**:
- Debts list with balance, interest rate, term
- Create debt modal
- Edit debt dialog
- Payment history table
- Payment schedule calendar
- Remaining balance projection
- Interest calculation display
- Next payment date highlight
- Debt consolidation suggestion
- Export payment schedule

**Files**:
- `/frontend/src/pages/Debts/DebtList.tsx`
- `/frontend/src/pages/Debts/DebtDetail.tsx`
- `/frontend/src/components/features/Debts/`
  - `DebtCard.tsx`
  - `DebtForm.tsx`
  - `PaymentSchedule.tsx`
  - `PaymentHistory.tsx`
- `/frontend/src/hooks/useDebts.ts`

---

## WBS-004-10: Create Subscription Management UI

**Effort**: 13 hours | **Dependencies**: WBS-004-06

Subscription management page showing active subscriptions, renewal dates, annual costs. One-click cancel subscription.

**Acceptance Criteria**:
- Subscriptions list with renewal date, amount
- Total annual cost display
- Create subscription modal
- Edit subscription dialog
- Delete/cancel subscription with confirmation
- Upcoming renewals section
- Cost summary (annual, monthly average)
- Pause/resume subscription
- Renewal date countdown
- Reminder before renewal
- Bulk actions (cancel multiple)

**Files**:
- `/frontend/src/pages/Subscriptions/SubscriptionList.tsx`
- `/frontend/src/components/features/Subscriptions/`
  - `SubscriptionCard.tsx`
  - `SubscriptionForm.tsx`
  - `CostSummary.tsx`
  - `UpcomingRenewals.tsx`
- `/frontend/src/hooks/useSubscriptions.ts`

---

## Summary

**Total Effort**: 150-180 hours

**Implementation Sequence**:
1. WBS-004-01: Budgets API
2. WBS-004-02: Budget alerts
3. WBS-004-03: Goals API
4. WBS-004-04: Debt tracker API
5. WBS-004-05: Subscription detection
6. WBS-004-06: Subscription management API
7. Then UI tasks (004-07 through 004-10) in parallel

**Outcome**: Complete financial planning system with budgets, goals, debts, and subscription management

---

*Each task includes detailed acceptance criteria, file references, and technical implementation notes.*
