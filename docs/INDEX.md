# Documentation Index - Personal Finance Tracker

**Updated**: 2026-03-15
**Total Documentation**: 5,456 lines across 9 files

---

## Quick Links

### For AI Agents Starting New Tasks

1. **First Time Setup**:
   - Read: `/docs/AI_AGENT_GUIDELINES.md` (complete rules and conventions)
   - Read: `/SYSTEM_DESIGN.md` (system architecture overview)
   - Read: Project-specific WBS task file

2. **During Task Development**:
   - Reference: `AI_AGENT_GUIDELINES.md` for conventions
   - Reference: Task-specific WBS file for acceptance criteria
   - Review: Existing code for style examples
   - Run: Tests frequently (`pytest`, `npm test`)

3. **After Task Completion**:
   - Ensure all acceptance criteria met
   - All tests passing
   - Code follows conventions
   - Commit with proper message format
   - Update WBS task status

---

## Documentation Structure

### 1. AI Agent Guidelines (`/docs/AI_AGENT_GUIDELINES.md`)

**Purpose**: Rules for AI agents working on this project
**Length**: 1,200 lines
**Content**:
- General principles (read SYSTEM_DESIGN first, follow conventions)
- Backend conventions (Python 3.12, async, repository pattern, type hints)
- Frontend conventions (TypeScript strict, functional components, Tailwind only)
- Database conventions (Alembic migrations, snake_case, UUID PKs)
- Testing requirements (pytest, vitest, coverage minimums)
- Code quality checklist
- Troubleshooting guide

**Use When**: Starting any task, need coding conventions, stuck on issue

---

### 2. WBS Overview (`/docs/wbs/README.md`)

**Purpose**: High-level Work Breakdown Structure overview
**Length**: 400 lines
**Content**:
- Feature overview (7 major features, 80 total tasks)
- Effort estimates (2,000-2,500 hours total)
- Dependency graph (critical paths)
- Implementation phases (4 phases, 13 weeks)
- Status tracking (checklist format)
- Progress dashboard

**Use When**: Understanding project scope, planning sprints, checking dependencies

---

### 3. WBS-001: Email Parser Engine (`/docs/wbs/WBS-001-email-parser-engine.md`)

**Purpose**: Email parsing system for bank transaction extraction
**Length**: 900 lines
**Tasks**: 10 subtasks (200-250 hours)
**Subtasks**:
1. Gmail API connection (OAuth2, token management)
2. Email sync service (fetch, filter, incremental sync with historyId)
3. Cake/VPBank parser (outgoing transfers support)
4. Email fingerprinting (duplicate detection)
5. Parser similarity matching (fuzzy merchant matching)
6. Unrecognized email queue (manual correction system)
7. Dynamic JSON parser runtime (non-dev parser creation)
8. Parser health monitoring (success rate, alerts)
9. Parser management UI (Settings page)
10. Parser template generator (auto-generate from samples)

**Critical Path**: 001-01 → 001-02 → 001-03 → 001-06
**Status**: NOT STARTED
**Priority**: P0

---

### 4. WBS-002: Auto Categorization (`/docs/wbs/WBS-002-auto-categorization.md`)

**Purpose**: Intelligent automatic transaction categorization
**Length**: 800 lines
**Tasks**: 8 subtasks (120-150 hours)
**Subtasks**:
1. Rule engine (regex matching, priority ordering)
2. Pattern learning (learn from user categorizations)
3. Pending review queue (uncategorized transactions)
4. Transaction categorization UI (inline edit, bulk)
5. Categorization rules management UI (create, edit, test rules)
6. "Learn from user" flow (suggest creating rules)
7. Seed default categories (20-30 Vietnamese categories)
8. Category analytics (coverage %, rule effectiveness)

**Dependencies**: WBS-001 (must complete email parser first)
**Status**: NOT STARTED
**Priority**: P0

---

### 5. WBS-003: Split Bills / Chia Tiền (`/docs/wbs/WBS-003-split-bills.md`)

**Purpose**: Shared expense tracking and settlement
**Length**: 550 lines
**Tasks**: 8 subtasks (100-130 hours)
**Subtasks**:
1. Contacts CRUD API
2. Split bill creation API (equal/exact/percentage split)
3. Auto-settlement detection (match incoming transfers)
4. Net balance calculation (who owes whom)
5. Contacts management UI
6. Split bill creation UI (multi-step wizard)
7. Split bill dashboard (settlement status, history)
8. Split bill reminders (notifications for overdue debts)

**Dependencies**: WBS-001, WBS-002
**Status**: NOT STARTED
**Priority**: P1

---

### 6. WBS-004: Budget / Goals / Debts / Subscriptions (`/docs/wbs/WBS-004-budget-goals-debts.md`)

**Purpose**: Financial planning and tracking
**Length**: 700 lines
**Tasks**: 10 subtasks (150-180 hours)
**Subtasks**:
1. Budget CRUD API (with spending calculation)
2. Budget alerts (80%, 100%, 120% thresholds)
3. Goals CRUD API (with progress tracking)
4. Debt tracker API (with interest calculation)
5. Subscription detection (recurring pattern analysis)
6. Subscription management API
7. Budget management UI
8. Goals UI
9. Debt tracker UI
10. Subscription management UI

**Dependencies**: WBS-001, WBS-002
**Status**: NOT STARTED
**Priority**: P1

---

### 7. WBS-005: Reports & Insights (`/docs/wbs/WBS-005-reports-insights.md`)

**Purpose**: Analytics and reporting
**Length**: 700 lines
**Tasks**: 8 subtasks (120-150 hours)
**Subtasks**:
1. Dashboard summary API (income/expense/savings, period comparison)
2. Monthly report API (category breakdown, trends)
3. Spending trends API (time series, moving averages)
4. Net worth tracker API (asset tracking over time)
5. Dashboard UI (summary cards, charts)
6. Monthly report page (detailed breakdown)
7. Trends page (line charts, forecasting)
8. Weekly email digest (scheduled task)

**Dependencies**: WBS-001, WBS-002
**Status**: NOT STARTED
**Priority**: P1

---

### 8. WBS-006: Client-Side Email Processing (`/docs/wbs/WBS-006-client-side-processing.md`)

**Purpose**: Privacy-first: process emails in user's browser
**Length**: 650 lines
**Tasks**: 7 subtasks (100-140 hours)
**Subtasks**:
1. TypeScript parser engine (port from Python)
2. TypeScript Cake/VPBank parser
3. Client-side Gmail API integration (OAuth in browser)
4. Transaction ingest API endpoint (receive parsed data)
5. Sync UI (progress, results, errors)
6. Dynamic parser runtime in TypeScript
7. Onboarding flow UI (choose sync method)

**Dependencies**: WBS-001 (for parser architecture knowledge)
**Status**: NOT STARTED
**Priority**: P2
**Note**: Optional feature for privacy-conscious users

---

### 9. WBS-007: Deployment & Security (`/docs/wbs/WBS-007-deployment-security.md`)

**Purpose**: Production hardening and compliance
**Length**: 650 lines
**Tasks**: 7 subtasks (80-100 hours)
**Subtasks**:
1. SSL/TLS setup (Let's Encrypt, Nginx, auto-renewal)
2. Authentication (JWT, login, password reset)
3. Automated backups (daily local, weekly offsite)
4. Backup management UI (restore, download)
5. Monitoring (health checks, Sentry, APM)
6. Data export (CSV, JSON, PDF - GDPR compliance)
7. Data deletion (GDPR right to be forgotten)

**Dependencies**: All other WBS (final phase)
**Status**: NOT STARTED
**Priority**: P0

---

## Implementation Statistics

### By Priority

| Priority | Features | Tasks | Hours |
|----------|----------|-------|-------|
| **P0** | WBS-001, WBS-007 | 17 | 280-350 |
| **P1** | WBS-002, WBS-003, WBS-004, WBS-005 | 34 | 470-610 |
| **P2** | WBS-006 | 7 | 100-140 |
| **Total** | 7 features | 58 | 850-1,100 |

*Note: WBS tasks total ~80, this table shows major groupings*

### By Technology Stack

**Backend (Python/FastAPI)**:
- 35+ tasks
- Database models, API endpoints, services, parsers, scheduler jobs
- Estimated: 500-700 hours

**Frontend (React/TypeScript)**:
- 25+ tasks
- Pages, components, hooks, services, state management
- Estimated: 350-450 hours

**Infrastructure**:
- 15+ tasks
- Docker, Nginx, SSL, backups, monitoring, CI/CD
- Estimated: 100-150 hours

---

## Quick Reference Tables

### Task Dependencies Map

```
No Dependencies:
  └─ WBS-001-01, 001-02, 001-03

WBS-001 → WBS-002 → WBS-004, WBS-005
        ↓
        WBS-003

All → WBS-007 (final phase)

WBS-006 (optional, parallel to WBS-001)
```

### Effort Estimation by Feature

| WBS | Feature | Effort | Days (1 dev) | Priority |
|-----|---------|--------|-------------|----------|
| 001 | Email Parser | 200-250h | 6-7 weeks | P0 |
| 002 | Auto Categorization | 120-150h | 4-5 weeks | P0 |
| 003 | Split Bills | 100-130h | 3-4 weeks | P1 |
| 004 | Budget/Goals/Debts | 150-180h | 5-6 weeks | P1 |
| 005 | Reports/Insights | 120-150h | 4-5 weeks | P1 |
| 006 | Client-Side (optional) | 100-140h | 3-4 weeks | P2 |
| 007 | Deployment/Security | 80-100h | 2-3 weeks | P0 |

---

## Development Workflow

### Phase 1: Foundation (Weeks 1-4)
- **Focus**: WBS-001 (Email Parser Engine)
- **Output**: Working email → transaction parser
- **Testing**: Parser accuracy > 95%
- **Deliverables**: Parser API, test coverage

### Phase 2: Intelligence (Weeks 4-7)
- **Focus**: WBS-002 (Auto Categorization)
- **Parallel**: WBS-006 optional development
- **Output**: Automatic transaction categorization
- **Testing**: Categorization accuracy > 90%
- **Deliverables**: Rules engine, UI, learning system

### Phase 3: Features (Weeks 7-11)
- **Focus**: WBS-003, WBS-004, WBS-005
- **Parallel**: Can work on all simultaneously (independent)
- **Output**: Split bills, budgets, reports
- **Testing**: Feature complete, UI polished
- **Deliverables**: Complete feature set

### Phase 4: Production (Weeks 11-13)
- **Focus**: WBS-007 (Deployment & Security)
- **Output**: Production-ready system
- **Testing**: Security audit passed, performance benchmarks met
- **Deliverables**: Deployed application, monitoring active

---

## For New Team Members

1. **Start Here**: Read `AI_AGENT_GUIDELINES.md` (rules)
2. **Understand System**: Read `/SYSTEM_DESIGN.md` (architecture)
3. **Pick a Task**: Check `/docs/wbs/README.md` (WBS overview)
4. **Read Specific WBS**: Get detailed requirements
5. **Start Coding**: Follow conventions from guidelines
6. **Test Frequently**: Unit tests, integration tests
7. **Commit Often**: Proper message format

---

## File Locations

All documentation located in:
```
/sessions/hopeful-vigilant-thompson/mnt/personal-finance-tracking/
├── /docs/
│   ├── AI_AGENT_GUIDELINES.md         (This one, start here)
│   ├── INDEX.md                        (This file)
│   └── /wbs/
│       ├── README.md                   (WBS overview)
│       ├── WBS-001-email-parser-engine.md
│       ├── WBS-002-auto-categorization.md
│       ├── WBS-003-split-bills.md
│       ├── WBS-004-budget-goals-debts.md
│       ├── WBS-005-reports-insights.md
│       ├── WBS-006-client-side-processing.md
│       └── WBS-007-deployment-security.md
├── SYSTEM_DESIGN.md                    (Architecture)
├── backend/
├── frontend/
├── docker-compose.yml
├── Makefile
└── scripts/
```

---

## How to Update Documentation

- **WBS Files**: Update `status` field when tasks change
- **AI Guidelines**: Keep synchronized with actual code conventions
- **This Index**: Update counts and estimates periodically

---

## Support & Questions

**If blocked**:
1. Check relevant WBS task file
2. Read `AI_AGENT_GUIDELINES.md` troubleshooting section
3. Review existing code for examples
4. Check `SYSTEM_DESIGN.md` for architectural guidance

**If documentation is unclear**:
- Ask for clarification
- Update documentation to be clearer
- Share improvements with team

---

**Happy coding! 🚀**

*This comprehensive WBS and guidelines system provides everything needed to implement a professional-grade personal finance application.*
