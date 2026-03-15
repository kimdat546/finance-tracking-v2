# WBS-005: Reports & Insights

**Feature**: Reports and Insights - Analytics and Reporting
**Status**: NOT STARTED
**Priority**: P1 (High)
**Total Effort**: 120-150 hours (8 tasks)
**Dependencies**: WBS-001, WBS-002
**Created**: 2026-03-15

---

## WBS-005-01: Implement Dashboard Summary API

**Effort**: 14 hours | **Dependencies**: WBS-001

API providing dashboard summary metrics: total income/expense/savings, period comparison (month vs month, year vs year).

**Acceptance Criteria**:
- Current month: income, expense, savings (net)
- Previous month comparison (% change)
- Year-to-date totals
- Monthly breakdown (last 12 months)
- Category breakdown (spending by category)
- Top merchants (highest spending)
- Savings rate calculation
- Performance: calculate < 500ms
- Cache with 1-hour TTL
- Test coverage 85%

**Files**:
- `/backend/app/services/dashboard_service.py`
- `/backend/app/api/dashboard.py`
- `/backend/tests/test_api/test_dashboard.py`

**Technical Notes**:
```python
def get_dashboard_summary(user_id: str, date: datetime):
    """Get summary metrics for dashboard."""
    current_month = date.replace(day=1)
    prev_month = (current_month - timedelta(days=1)).replace(day=1)

    current_income = sum_transactions(user_id, current_month, 'income')
    current_expense = sum_transactions(user_id, current_month, 'expense')
    current_savings = current_income - current_expense

    prev_income = sum_transactions(user_id, prev_month, 'income')
    prev_expense = sum_transactions(user_id, prev_month, 'expense')

    return {
        'current_month': {
            'income': current_income,
            'expense': current_expense,
            'savings': current_savings,
        },
        'previous_month': {
            'income': prev_income,
            'expense': prev_expense,
        },
        'change': {
            'income_pct': (current_income - prev_income) / prev_income * 100,
            'expense_pct': (current_expense - prev_expense) / prev_expense * 100,
        }
    }
```

---

## WBS-005-02: Implement Monthly Report API

**Effort**: 12 hours | **Dependencies**: WBS-001

Generate detailed monthly reports with category breakdown, transactions list, trends.

**Acceptance Criteria**:
- Category spending breakdown (table + chart data)
- Transaction list for month (filterable)
- Top 10 merchants
- Expense trends (daily spending line)
- Income sources
- Savings summary
- Budget vs actual (if budgets set)
- Export as PDF
- Email report capability
- Test coverage 80%

**Files**:
- `/backend/app/services/report_service.py`
- `/backend/app/api/reports.py`
- `/backend/tests/test_api/test_reports.py`

---

## WBS-005-03: Implement Spending Trends API

**Effort**: 14 hours | **Dependencies**: WBS-001

Time-series spending data for trend analysis. Daily/weekly/monthly aggregation.

**Acceptance Criteria**:
- Spending by date (daily aggregation)
- Spending by category over time
- Moving averages (7-day, 30-day)
- Trend direction (up/down)
- Seasonality detection (peak months)
- Year-over-year comparison
- Forecast next month spending (linear regression)
- Volatility calculation (spending variance)
- Performance < 1s for 1 year data
- Test coverage 80%

**Files**:
- `/backend/app/services/trends_service.py`
- `/backend/app/api/trends.py`
- `/backend/tests/test_api/test_trends.py`

**Technical Notes**:
```python
def calculate_spending_trend(user_id: str, days: int = 365):
    """Calculate spending trends."""
    transactions = get_transactions(user_id, days)

    # Group by date
    daily_spending = defaultdict(Decimal)
    for t in transactions:
        daily_spending[t.created_at.date()] += abs(t.amount)

    # Calculate 7-day and 30-day moving averages
    dates = sorted(daily_spending.keys())
    ma_7 = []
    ma_30 = []

    for i, date in enumerate(dates):
        # 7-day MA
        if i >= 6:
            ma_7.append(sum(daily_spending[d] for d in dates[i-6:i+1]) / 7)

        # 30-day MA
        if i >= 29:
            ma_30.append(sum(daily_spending[d] for d in dates[i-29:i+1]) / 30)

    return {
        'dates': dates,
        'spending': [daily_spending[d] for d in dates],
        'ma_7': ma_7,
        'ma_30': ma_30,
    }
```

---

## WBS-005-04: Implement Net Worth Tracker API

**Effort**: 12 hours | **Dependencies**: WBS-001

Track net worth over time. Calculate from: accounts balance, debts (negative), goals (savings).

**Acceptance Criteria**:
- Current net worth (assets - liabilities)
- Net worth history (monthly snapshots)
- Asset breakdown (cash, savings, investments)
- Liability breakdown (debts, loans)
- Net worth growth rate
- Projection (if current trend continues)
- Currency conversion (if multiple currencies)
- Milestone tracking (net worth goals)
- Performance < 500ms
- Test coverage 80%

**Files**:
- `/backend/app/services/net_worth_service.py`
- `/backend/app/api/net_worth.py`
- `/backend/tests/test_api/test_net_worth.py`

**Technical Notes**:
```python
def calculate_net_worth(user_id: str):
    """Calculate current net worth."""
    # Assets
    account_balance = sum_account_balances(user_id)
    savings = sum_goal_savings(user_id)

    # Liabilities
    debt_balance = sum_outstanding_debts(user_id)
    credit_card_debt = sum_credit_card_balances(user_id)

    net_worth = account_balance + savings - debt_balance - credit_card_debt
    return {
        'assets': account_balance + savings,
        'liabilities': debt_balance + credit_card_debt,
        'net_worth': net_worth,
    }

def get_net_worth_history(user_id: str, months: int = 12):
    """Get net worth over last N months."""
    history = []
    for i in range(months, 0, -1):
        date = now() - timedelta(days=30*i)
        nw = calculate_net_worth_at_date(user_id, date)
        history.append({'date': date, 'net_worth': nw})
    return history
```

---

## WBS-005-05: Create Dashboard UI

**Effort**: 16 hours | **Dependencies**: WBS-005-01

Main dashboard page with summary cards, charts, and recent activity.

**Acceptance Criteria**:
- Summary cards: income, expense, savings, balance
- Period selector (month, year, custom)
- Comparison to previous period
- Spending by category (pie/bar chart)
- Trend chart (spending over last 6 months)
- Recent transactions (last 10)
- Quick actions (add transaction, create budget)
- Alerts (budget exceeded, bill reminder)
- Net worth display
- Vietnamese language

**Files**:
- `/frontend/src/pages/Dashboard/index.tsx`
- `/frontend/src/components/features/Dashboard/`
  - `SummaryCards.tsx`
  - `SpendingChart.tsx`
  - `TrendChart.tsx`
  - `RecentTransactions.tsx`
  - `AlertsBanner.tsx`
- `/frontend/src/hooks/useDashboard.ts`

---

## WBS-005-06: Create Monthly Report Page

**Effort**: 14 hours | **Dependencies**: WBS-005-02

Monthly report page showing detailed breakdown, charts, comparison, export options.

**Acceptance Criteria**:
- Month selector (calendar or dropdown)
- Category spending table (amount, % of total)
- Category spending chart (pie, bar, sunburst)
- Top merchants table
- Daily spending sparkline
- Summary section
- Budget vs actual (if set)
- Comparison to previous month
- Export as PDF button
- Email report button
- Print support

**Files**:
- `/frontend/src/pages/Reports/MonthlyReport.tsx`
- `/frontend/src/components/features/Reports/`
  - `CategoryBreakdown.tsx`
  - `MerchantRanking.tsx`
  - `ComparisonChart.tsx`
  - `ExportOptions.tsx`
- `/frontend/src/hooks/useMonthlyReport.ts`

---

## WBS-005-07: Create Trends Page

**Effort**: 14 hours | **Dependencies**: WBS-005-03

Trends page showing spending over time with filters and analysis.

**Acceptance Criteria**:
- Time period selector (6 months, 1 year, custom)
- Spending line chart (with moving averages)
- Category breakdown over time
- Trend direction indicators (up/down arrows)
- Volatility display
- Year-over-year comparison (if enough data)
- Forecast section (next month prediction)
- Peak/low spending indicators
- Category trends (which categories growing)
- Export chart/data

**Files**:
- `/frontend/src/pages/Trends/TrendsPage.tsx`
- `/frontend/src/components/features/Trends/`
  - `TrendChart.tsx`
  - `CategoryTrends.tsx`
  - `Forecast.tsx`
  - `VolatilityIndicator.tsx`
- `/frontend/src/hooks/useTrends.ts`

---

## WBS-005-08: Implement Weekly Email Digest

**Effort**: 14 hours | **Dependencies**: WBS-005-02

Scheduled email digest sent weekly (or configurable) with spending summary, alerts, and insights.

**Acceptance Criteria**:
- Scheduled job (every Friday)
- Email template with:
  - Spending summary (week vs previous)
  - Top 5 merchants
  - Budget status (if over)
  - Upcoming bills (subscriptions, debts)
  - Saving progress (goals)
  - Tip of the week
- Configurable day/time
- Opt-out option
- Template variables (personalization)
- Track sent emails
- Resend capability
- Plain text + HTML versions

**Files**:
- `/backend/app/jobs/email_digest_job.py`
- `/backend/app/templates/email/weekly_digest.html`
- `/backend/app/templates/email/weekly_digest.txt`
- `/backend/app/services/email_service.py`
- `/backend/tests/test_jobs/test_email_digest.py`

**Technical Notes**:
```python
@app.on_event("startup")
async def schedule_email_digest():
    """Schedule weekly digest every Friday at 8 AM."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_weekly_digest,
        trigger="cron",
        day_of_week="fri",
        hour=8,
        minute=0,
    )
    scheduler.start()

async def send_weekly_digest():
    """Send weekly email digest to all users."""
    users = get_users_with_email_digest_enabled()
    for user in users:
        summary = get_weekly_summary(user.id)
        html = render_template('weekly_digest.html', user=user, summary=summary)
        send_email(user.email, "Your Weekly Spending Digest", html)
```

---

## Summary

**Total Effort**: 120-150 hours

**Implementation Sequence**:
1. WBS-005-01: Dashboard summary API
2. WBS-005-02: Monthly report API
3. WBS-005-03: Spending trends API
4. WBS-005-04: Net worth tracker API
5. Then UI tasks (005-05 through 005-07) in parallel
6. WBS-005-08: Email digest (last, depends on all above)

**Outcome**: Complete reporting and analytics system with dashboards, insights, and email digests

---

*Each task fully documented with acceptance criteria, file structure, and technical implementation notes.*
