# Work Breakdown Structure (WBS) - Personal Finance Tracker

**Version**: 1.0
**Last Updated**: 2026-03-15
**Status**: ACTIVE

---

## Tổng quan

Dự án Personal Finance Tracker được chia thành **7 major features**, mỗi feature có **8-10 sub-tasks**.

**Tổng cộng**: ~80 tasks, ước tính 2000-2500 hours development

---

## Feature Overview

| WBS ID | Feature Name | Status | Priority | Tasks | Est. Hours | Dependencies |
|--------|-------------|--------|----------|-------|-----------|--------------|
| WBS-001 | Email Parser Engine | NOT STARTED | P0 | 10 | 200-250 | None |
| WBS-002 | Auto Categorization | NOT STARTED | P0 | 8 | 120-150 | WBS-001 |
| WBS-003 | Split Bills (Chia tiền) | NOT STARTED | P1 | 8 | 100-130 | WBS-001 |
| WBS-004 | Budget/Goals/Debts | NOT STARTED | P1 | 10 | 150-180 | WBS-001, WBS-002 |
| WBS-005 | Reports & Insights | NOT STARTED | P1 | 8 | 120-150 | WBS-001, WBS-002 |
| WBS-006 | Client-Side Processing | NOT STARTED | P2 | 7 | 100-140 | WBS-001 |
| WBS-007 | Deployment & Security | NOT STARTED | P0 | 7 | 80-100 | All |

---

## Dependency Graph

```
WBS-001 (Email Parser)
  ├─→ WBS-002 (Auto Categorization)
  ├─→ WBS-003 (Split Bills)
  ├─→ WBS-004 (Budget/Goals)
  ├─→ WBS-005 (Reports)
  ├─→ WBS-006 (Client-Side)
  └─→ WBS-007 (Deployment)

WBS-002 (Auto Categorization)
  ├─→ WBS-004
  └─→ WBS-005

WBS-007 (Deployment)
  Depends on all others
```

---

## Implementation Order

**Recommended sequence** (respect dependencies):

### Phase 1: Foundation (Weeks 1-4)
- **WBS-001**: Email Parser Engine
  - Must complete WBS-001-01 through WBS-001-06 first
  - WBS-001-07 onwards can be parallel with WBS-002

### Phase 2: Intelligence (Weeks 4-7)
- **WBS-002**: Auto Categorization (parallel with WBS-001-07+)
- **WBS-003**: Split Bills (can start after WBS-001-06)

### Phase 3: Features (Weeks 7-11)
- **WBS-004**: Budget/Goals/Debts (needs WBS-001, WBS-002)
- **WBS-005**: Reports (needs WBS-001, WBS-002)
- **WBS-006**: Client-Side (parallel, needs WBS-001)

### Phase 4: Production (Weeks 11-13)
- **WBS-007**: Deployment & Security (final, depends on all)

---

## Progress Tracking

### Status Legend

- **NOT STARTED**: No tasks completed
- **IN PROGRESS**: Some tasks in progress
- **BLOCKED**: Waiting for dependencies
- **TESTING**: Implementation done, testing in progress
- **COMPLETED**: All tasks done and tested

### How to Track

1. Each WBS file has per-task status
2. Update status when starting/completing
3. Commit message format:
   ```
   feat(WBS-001-01): implement Gmail OAuth2
   ```

---

## Files Structure

```
docs/wbs/
├── README.md                            # This file
├── WBS-001-email-parser-engine.md       # 10 tasks
├── WBS-002-auto-categorization.md       # 8 tasks
├── WBS-003-split-bills.md               # 8 tasks
├── WBS-004-budget-goals-debts.md        # 10 tasks
├── WBS-005-reports-insights.md          # 8 tasks
├── WBS-006-client-side-processing.md    # 7 tasks
└── WBS-007-deployment-security.md       # 7 tasks
```

---

## Task Format

Mỗi task có format sau:

```
## WBS-XXX-YY: Task Title

**Priority**: P0-P3 (P0 = Critical, P3 = Nice to have)
**Status**: NOT STARTED | IN PROGRESS | COMPLETED | BLOCKED
**Estimated Effort**: X hours
**Dependencies**: [List of prerequisite tasks]

### Description
3-5 sentences chi tiết task là gì, tại sao cần, outcome là gì.

### Acceptance Criteria
1. Specific, testable criteria
2. Measurable requirements
3. Definition of "Done"

### Files to Create
- `/path/to/new/file.py`
- `/path/to/another/file.tsx`

### Files to Modify
- `/path/to/existing/file.py`
- `/path/to/modified/file.tsx`

### Test Requirements
- Unit tests for functions
- Integration tests for endpoints
- Test coverage minimum %

### Technical Notes for AI Agent
- Specific implementation hints
- Gotchas to watch out for
- Code examples if helpful
- External dependencies needed
```

---

## Key Principles

### 1. Dependencies First
- Check dependencies BEFORE starting task
- Don't work on task if prerequisites incomplete

### 2. Acceptance Criteria
- Acceptance criteria are the "Definition of Done"
- Task not done until ALL criteria met

### 3. Testing Required
- No task completes without tests
- Tests must pass before merge

### 4. Documentation
- Each feature needs API documentation
- Database schema must be documented
- UI flows should have wireframes

### 5. Code Review
- All code reviewed before merge
- Must meet conventions from AI_AGENT_GUIDELINES.md

---

## Effort Estimation

**Effort Breakdown**:
- **P0 (Critical)**: 2-3 weeks high priority
- **P1 (High)**: 2-4 weeks after P0
- **P2 (Medium)**: 4-8 weeks after P1
- **P3 (Low)**: Nice to have, lower priority

**Total Project**: ~2000-2500 hours = ~12-13 weeks (with team of 3-4 developers)

---

## Status Dashboard

### WBS-001: Email Parser Engine
Progress: 0/10 tasks
- [ ] WBS-001-01: Gmail API connection
- [ ] WBS-001-02: Email sync service
- [ ] WBS-001-03: Cake/VPBank parser
- [ ] WBS-001-04: Email fingerprinting
- [ ] WBS-001-05: Parser similarity matching
- [ ] WBS-001-06: Unrecognized email queue
- [ ] WBS-001-07: Dynamic parser runtime
- [ ] WBS-001-08: Parser health monitoring
- [ ] WBS-001-09: Parser management UI
- [ ] WBS-001-10: Parser template generator

### WBS-002: Auto Categorization
Progress: 0/8 tasks
- [ ] WBS-002-01: Rule engine
- [ ] WBS-002-02: Pattern learning
- [ ] WBS-002-03: Pending review queue
- [ ] WBS-002-04: Transaction categorization UI
- [ ] WBS-002-05: Categorization rules management UI
- [ ] WBS-002-06: Learn from user flow
- [ ] WBS-002-07: Seed default categories
- [ ] WBS-002-08: Category analytics

### WBS-003: Split Bills
Progress: 0/8 tasks
- [ ] WBS-003-01: Contacts CRUD API
- [ ] WBS-003-02: Split bill creation API
- [ ] WBS-003-03: Auto-settlement detection
- [ ] WBS-003-04: Net balance calculation
- [ ] WBS-003-05: Contacts management UI
- [ ] WBS-003-06: Split bill creation UI
- [ ] WBS-003-07: Split bill dashboard
- [ ] WBS-003-08: Split bill reminders

### WBS-004: Budget/Goals/Debts
Progress: 0/10 tasks
- [ ] WBS-004-01: Budget CRUD API
- [ ] WBS-004-02: Budget alerts
- [ ] WBS-004-03: Goals CRUD API
- [ ] WBS-004-04: Debt tracker API
- [ ] WBS-004-05: Subscription detection
- [ ] WBS-004-06: Subscription management API
- [ ] WBS-004-07: Budget management UI
- [ ] WBS-004-08: Goals UI
- [ ] WBS-004-09: Debt tracker UI
- [ ] WBS-004-10: Subscription management UI

### WBS-005: Reports & Insights
Progress: 0/8 tasks
- [ ] WBS-005-01: Dashboard summary API
- [ ] WBS-005-02: Monthly report API
- [ ] WBS-005-03: Spending trends API
- [ ] WBS-005-04: Net worth tracker API
- [ ] WBS-005-05: Dashboard UI
- [ ] WBS-005-06: Monthly report page
- [ ] WBS-005-07: Trends page
- [ ] WBS-005-08: Weekly email digest

### WBS-006: Client-Side Processing
Progress: 0/7 tasks
- [ ] WBS-006-01: TypeScript parser engine
- [ ] WBS-006-02: TypeScript Cake/VPBank parser
- [ ] WBS-006-03: Client-side Gmail integration
- [ ] WBS-006-04: Transaction ingest endpoint
- [ ] WBS-006-05: Sync UI
- [ ] WBS-006-06: Dynamic parser runtime (TypeScript)
- [ ] WBS-006-07: Onboarding flow UI

### WBS-007: Deployment & Security
Progress: 0/7 tasks
- [ ] WBS-007-01: SSL/TLS setup
- [ ] WBS-007-02: Authentication (JWT)
- [ ] WBS-007-03: Automated backups
- [ ] WBS-007-04: Backup management UI
- [ ] WBS-007-05: Monitoring & health checks
- [ ] WBS-007-06: Data export
- [ ] WBS-007-07: Data deletion (GDPR)

---

## Contact & Escalation

**Need help?**
- Read the specific WBS task file
- Check AI_AGENT_GUIDELINES.md for conventions
- Review SYSTEM_DESIGN.md for architecture
- Check existing code for examples

**Blocker?**
- Document the issue
- Report with specific error messages
- Suggest potential solutions
- Don't proceed if blocked

---

**Last Updated**: 2026-03-15
**Maintained By**: Project Team
