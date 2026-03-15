# WBS-002: Auto Categorization System

**Feature**: Auto Categorization - Intelligent Transaction Categorization
**Status**: NOT STARTED
**Priority**: P0 (Critical)
**Total Effort**: 120-150 hours (8 tasks, 15-20 hours each)
**Dependencies**: WBS-001 (Email Parser Engine)
**Created**: 2026-03-15

---

## WBS-002-01: Implement Rule Engine (Regex Matching, Priority Ordering)

**Status**: NOT STARTED
**Priority**: P0
**Estimated Effort**: 20 hours
**Dependencies**: WBS-001-06

### Description

Implement rule-based categorization engine that applies rules in priority order. Rules contain patterns (merchant name regex, description patterns) and amount ranges. Engine returns matching category and rule confidence. Store rules in database with enable/disable flag and statistics.

### Acceptance Criteria

1. `CategorizationRule` model with: pattern, amount_min/max, priority, enabled flag
2. Rule matching with regex or substring matching
3. Priority-ordered rule evaluation (highest priority wins)
4. Confidence score calculation (0-100%)
5. Multiple rules can match → return highest confidence
6. Case-insensitive matching (handle "APPLE", "apple", "Apple")
7. Performance: categorize 1000 transactions < 1 second
8. Rule statistics: match count, success rate, last matched
9. Ability to bulk enable/disable rules
10. API to create/update/delete rules

### Files to Create

- `/backend/app/services/categorization_engine.py` - Rule matching engine
- `/backend/app/schemas/categorization.py` - Rule schemas
- `/backend/app/api/categorization_rules.py` - Rule management API
- `/backend/tests/test_services/test_categorization_engine.py` - Engine tests

### Files to Modify

- `/backend/app/models/transaction.py` - Update CategorizationRule
- `/backend/alembic/versions/008_categorization_rules.py` - Enhance table

### Test Requirements

- Test regex matching
- Test substring matching
- Test priority ordering
- Test confidence calculation
- Test case-insensitive matching
- Test performance (1000 transactions)
- Test statistics tracking
- **Minimum coverage**: 90%

### Technical Notes for AI Agent

1. **CategorizationRule Model**:
   ```python
   class CategorizationRule(Base):
       __tablename__ = "categorization_rules"

       user_id: Mapped[str]  # Can have user-specific rules
       category_id: Mapped[str]  # FK to Category
       priority: Mapped[int]  # 0-100 (higher = checked first)
       enabled: Mapped[bool] = default(True)

       # Pattern matching
       merchant_pattern: Mapped[str | None]  # regex
       merchant_match_type: Mapped[str] = "regex"  # regex or substring
       description_pattern: Mapped[str | None]
       description_match_type: Mapped[str] = "regex"

       # Amount filtering
       amount_min: Mapped[Decimal | None]
       amount_max: Mapped[Decimal | None]

       # Type filtering
       transaction_type: Mapped[str | None]  # income, expense, transfer

       # Statistics
       match_count: Mapped[int] = default(0)
       last_matched_at: Mapped[datetime | None]

       created_at: Mapped[datetime]
       updated_at: Mapped[datetime]

       category: Mapped["Category"] = relationship(back_populates="rules")
   ```

2. **Rule Engine**:
   ```python
   class CategorizationEngine:
       async def categorize(self, transaction: Transaction) -> tuple[str, float]:
           """Categorize transaction, return (category_id, confidence)."""
           rules = await self._get_enabled_rules(transaction.user_id)
           rules.sort(key=lambda r: r.priority, reverse=True)

           for rule in rules:
               if self._matches_rule(transaction, rule):
                   confidence = self._calculate_confidence(rule)
                   return (rule.category_id, confidence)

           return (None, 0.0)

       def _matches_rule(self, transaction: Transaction, rule: CategorizationRule) -> bool:
           """Check if transaction matches rule."""
           # Check type filter
           if rule.transaction_type and transaction.type != rule.transaction_type:
               return False

           # Check amount range
           if rule.amount_min and transaction.amount < rule.amount_min:
               return False
           if rule.amount_max and transaction.amount > rule.amount_max:
               return False

           # Check merchant pattern
           if rule.merchant_pattern:
               if not self._pattern_matches(
                   transaction.merchant,
                   rule.merchant_pattern,
                   rule.merchant_match_type
               ):
                   return False

           # Check description pattern
           if rule.description_pattern:
               if not self._pattern_matches(
                   transaction.description,
                   rule.description_pattern,
                   rule.description_match_type
               ):
                   return False

           return True

       def _pattern_matches(self, text: str, pattern: str, match_type: str) -> bool:
           if match_type == "regex":
               return bool(re.search(pattern, text, re.IGNORECASE))
           else:  # substring
               return pattern.lower() in text.lower()

       def _calculate_confidence(self, rule: CategorizationRule) -> float:
           """Confidence = (matches so far / attempts)."""
           if rule.match_count == 0:
               return 0.5  # Default confidence
           # Can enhance with actual success tracking
           return 0.9
   ```

3. **API Endpoints**:
   ```
   GET    /categorization-rules              - List rules
   POST   /categorization-rules              - Create rule
   PUT    /categorization-rules/{id}         - Update rule
   DELETE /categorization-rules/{id}         - Delete rule
   POST   /categorization-rules/bulk-update  - Enable/disable multiple
   GET    /categorization-rules/suggest      - Suggest rule for category
   ```

### Documentation Needed

- Rule matching algorithm
- Confidence calculation
- API documentation

---

## WBS-002-02: Implement Pattern Learning from User Categorizations

**Status**: NOT STARTED
**Priority**: P0
**Estimated Effort**: 18 hours
**Dependencies**: WBS-002-01

### Description

Implement machine learning component that learns from user's manual categorizations. Extract keywords from merchant/description, find similar transactions, and create rules automatically. System should improve categorization accuracy over time as users manually categorize more transactions.

### Acceptance Criteria

1. Extract keywords from merchant name and description (TF-IDF)
2. Find similar categorized transactions (cosine similarity)
3. Auto-create rules from high-confidence patterns
4. Confidence threshold (80% before auto-creating rule)
5. Track learning effectiveness (accuracy improvement)
6. Allow users to review/approve auto-created rules
7. Category alias learning (learn "Starbucks" = Coffee → Food)
8. Handle seasonal patterns (e.g., December → Holiday shopping)
9. A/B test learning models
10. Opt-out option for automatic rule creation

### Files to Create

- `/backend/app/services/pattern_learner.py` - ML pattern learning
- `/backend/app/models/learning.py` - PatternSignature, Alias models
- `/backend/tests/test_services/test_pattern_learner.py` - Learning tests

### Files to Modify

- `/backend/app/services/categorization_engine.py` - Integrate learner
- `/backend/app/api/transactions.py` - On categorization endpoint

### Test Requirements

- Test keyword extraction
- Test similarity calculation
- Test rule generation
- Test confidence thresholds
- Test learning from multiple transactions
- **Minimum coverage**: 85%

### Technical Notes for AI Agent

1. **Pattern Learning**:
   ```python
   class PatternLearner:
       async def learn_from_categorization(
           self,
           transaction: Transaction,
           category_id: str
       ) -> CategorizationRule | None:
           """Learn from manual categorization, maybe create rule."""

           # 1. Extract keywords
           keywords = self._extract_keywords(
               transaction.merchant,
               transaction.description
           )

           # 2. Find similar categorized transactions
           similar = await self._find_similar_transactions(
               transaction.user_id,
               keywords,
               category_id
           )

           # 3. Calculate confidence
           confidence = len(similar) / (len(similar) + 5)  # Smoothing

           # 4. Create rule if confident
           if confidence >= 0.8:
               rule = await self._create_rule_from_pattern(
                   transaction.user_id,
                   category_id,
                   keywords,
                   confidence
               )
               return rule

           return None

       def _extract_keywords(self, merchant: str, description: str) -> list[str]:
           """Extract keywords using TF-IDF."""
           text = f"{merchant} {description}".lower()
           # Remove common words
           words = [
               w for w in text.split()
               if w not in STOP_WORDS and len(w) > 2
           ]
           return words[:10]  # Top 10 words

       async def _find_similar_transactions(
           self,
           user_id: str,
           keywords: list[str],
           category_id: str
       ) -> list[Transaction]:
           """Find similar transactions with same category."""
           # Query transactions in same category
           transactions = await self.session.execute(
               select(Transaction).where(
                   (Transaction.user_id == user_id) &
                   (Transaction.category_id == category_id)
               )
           )

           # Score by keyword overlap
           scored = []
           for t in transactions.scalars():
               t_keywords = self._extract_keywords(t.merchant, t.description)
               overlap = len(set(keywords) & set(t_keywords))
               if overlap > 0:
                   scored.append((t, overlap))

           # Return top matches
           return [t for t, _ in sorted(scored, key=lambda x: x[1], reverse=True)]
   ```

2. **STOP_WORDS** (Vietnamese + English):
   ```python
   STOP_WORDS = {
       'the', 'a', 'and', 'or', 'but', 'in', 'on', 'at',
       'cua', 'va', 'la', 'o', 'de', 'tai', 'hang', 'khong'
   }
   ```

3. **Rule Approval Workflow**:
   - System suggests rule
   - User sees suggestion with matching examples
   - User can approve/reject
   - Approved rules added to CategorizationRule table
   - Track approval rate for feedback

### Documentation Needed

- Pattern learning algorithm
- TF-IDF explanation
- Similarity calculation method

---

## WBS-002-03: Implement Pending Review Queue API

**Status**: NOT STARTED
**Priority**: P0
**Estimated Effort**: 15 hours
**Dependencies**: WBS-002-01

### Description

Implement API for viewing and managing uncategorized transactions. Queue shows transactions pending manual categorization, with suggestions from rule engine. Support filtering, sorting, bulk categorization, and marking as reviewed.

### Acceptance Criteria

1. Pending transactions list with filters (date range, amount range, type)
2. Sort options: date, amount, merchant
3. Pagination support (page, page_size)
4. Show categorization suggestions with confidence score
5. Bulk categorize (select multiple, apply category)
6. Quick categorize (single click from list)
7. Defer categorization (hide for 30 days)
8. Mark as reviewed (skip categorization)
9. Statistics: count pending, default category suggestion
10. Analytics: which transactions pending longest

### Files to Create

- `/backend/app/services/pending_review_service.py` - Queue management
- `/backend/app/schemas/pending_review.py` - Response schemas
- `/backend/tests/test_api/test_pending_review.py` - API tests

### Files to Modify

- `/backend/app/api/transactions.py` - Add pending endpoints

### Test Requirements

- Test list pending transactions
- Test filters and sorting
- Test bulk categorization
- Test statistics
- **Minimum coverage**: 85%

### Technical Notes for AI Agent

1. **Pending Transactions Query**:
   ```python
   async def get_pending_transactions(
       self,
       user_id: str,
       skip: int = 0,
       limit: int = 20,
       sort_by: str = "created_at",
       sort_order: str = "desc"
   ) -> list[Transaction]:
       """Get transactions without category."""
       stmt = (
           select(Transaction)
           .where(
               (Transaction.user_id == user_id) &
               (Transaction.category_id == None)
           )
           .offset(skip)
           .limit(limit)
       )
       # Apply sorting
       if sort_by == "amount":
           stmt = stmt.order_by(
               Transaction.amount.desc() if sort_order == "desc"
               else Transaction.amount
           )
       else:
           stmt = stmt.order_by(
               Transaction.created_at.desc() if sort_order == "desc"
               else Transaction.created_at
           )

       result = await self.session.execute(stmt)
       return result.scalars().all()
   ```

2. **With Suggestions**:
   ```python
   async def get_pending_with_suggestions(
       self,
       user_id: str,
       skip: int = 0,
       limit: int = 20
   ) -> list[PendingTransactionSchema]:
       """Get pending transactions with category suggestions."""
       transactions = await self.get_pending_transactions(user_id, skip, limit)

       results = []
       for t in transactions:
           # Get top 3 suggestions
           suggestions = await self.categorization_engine.get_suggestions(t)
           results.append(
               PendingTransactionSchema(
                   **t.__dict__,
                   suggestions=suggestions
               )
           )

       return results
   ```

3. **API Endpoints**:
   ```
   GET /transactions/pending                    - List pending
   POST /transactions/pending/bulk-categorize   - Bulk assign
   POST /transactions/{id}/defer                - Defer 30 days
   ```

### Documentation Needed

- Pending queue API documentation

---

## WBS-002-04: Create Transaction Categorization UI (Inline Edit, Bulk Categorize)

**Status**: NOT STARTED
**Priority**: P0
**Estimated Effort**: 18 hours
**Dependencies**: WBS-002-03

### Description

Create React UI for categorizing transactions. Feature inline category selection, quick categorize buttons, bulk operations, and confirmation dialogs. Show category hierarchy, color-coded categories, and categorization suggestions. Integrate with categorization API.

### Acceptance Criteria

1. Transaction list with category column (clickable to edit)
2. Inline category selector (dropdown with search)
3. Category hierarchy support (main category → subcategory)
4. Color-coded categories (visual feedback)
5. Quick suggest button (show top suggestion)
6. Bulk select checkboxes (select multiple transactions)
7. Bulk categorize modal (apply to all selected)
8. Confirmation before categorization (with undo 30 sec)
9. Show categorization confidence/suggestion count
10. Vietnamese category names

### Files to Create

- `/frontend/src/pages/Transactions/TransactionList.tsx` - Main list
- `/frontend/src/components/features/Transactions/` - Sub-components
  - `CategorySelector.tsx`
  - `CategoryBadge.tsx`
  - `BulkCategorizeModal.tsx`
  - `SuggestionPanel.tsx`
- `/frontend/src/hooks/useCategories.ts` - Category queries
- `/frontend/src/services/categoryService.ts` - API calls
- `/frontend/src/types/category.ts` - Types

### Test Requirements

- Render transaction list
- Edit category inline
- Bulk select and categorize
- Show suggestions
- **Minimum coverage**: 80%

### Technical Notes for AI Agent

1. **CategorySelector Component**:
   ```typescript
   interface CategorySelectorProps {
     value: string | null;
     onChange: (categoryId: string) => void;
     categories: Category[];
     suggestions?: CategorySuggestion[];
     isLoading?: boolean;
   }

   export const CategorySelector: React.FC<CategorySelectorProps> = ({
     value,
     onChange,
     categories,
     suggestions,
     isLoading,
   }) => {
     const [open, setOpen] = React.useState(false);
     const [search, setSearch] = React.useState('');

     return (
       <div className="relative">
         <button
           onClick={() => setOpen(!open)}
           className="px-3 py-2 border rounded-md text-sm"
         >
           {getCategoryName(value, categories) || 'Chọn danh mục'}
         </button>

         {open && (
           <div className="absolute top-full left-0 w-64 bg-white border rounded shadow-lg">
             <input
               type="text"
               placeholder="Tìm danh mục..."
               value={search}
               onChange={(e) => setSearch(e.target.value)}
               className="w-full px-3 py-2 border-b"
             />

             {suggestions && suggestions.length > 0 && (
               <div className="bg-blue-50 p-2 border-b">
                 <p className="text-xs font-semibold text-gray-600">Gợi ý</p>
                 {suggestions.map((s) => (
                   <button
                     key={s.categoryId}
                     onClick={() => {
                       onChange(s.categoryId);
                       setOpen(false);
                     }}
                     className="w-full text-left px-3 py-2 hover:bg-blue-100 text-sm"
                   >
                     {s.categoryName} ({Math.round(s.confidence * 100)}%)
                   </button>
                 ))}
               </div>
             )}

             <div className="max-h-48 overflow-y-auto">
               {categories
                 .filter((c) => c.name.toLowerCase().includes(search.toLowerCase()))
                 .map((c) => (
                   <button
                     key={c.id}
                     onClick={() => {
                       onChange(c.id);
                       setOpen(false);
                     }}
                     className={clsx(
                       'w-full text-left px-3 py-2 hover:bg-gray-100',
                       value === c.id && 'bg-blue-100'
                     )}
                   >
                     <span
                       className="inline-block w-3 h-3 rounded-full mr-2"
                       style={{ backgroundColor: c.color }}
                     />
                     {c.name}
                   </button>
                 ))}
             </div>
           </div>
         )}
       </div>
     );
   };
   ```

2. **Bulk Categorize Modal**:
   - Show selected transaction count
   - Category selector
   - Preview affected transactions
   - Confirm/Cancel buttons

3. **Undo Feature**:
   - Store previous categorizations
   - Show "Undo" button for 30 seconds
   - Use React Query mutation optimistic updates

### Documentation Needed

- UI mockup description
- Category hierarchy explanation

---

## WBS-002-05: Create Categorization Rules Management UI

**Status**: NOT STARTED
**Priority**: P1
**Estimated Effort**: 16 hours
**Dependencies**: WBS-002-04

### Description

Create React UI for managing categorization rules. Display active rules with statistics, allow creating new rules via form or from transaction example, enable/disable rules, and view rule effectiveness. Support rule templates and bulk operations.

### Acceptance Criteria

1. Rules list with: pattern, category, priority, success rate, match count
2. Create rule form (merchant pattern, amount range, priority)
3. Create rule from transaction example (auto-generate pattern)
4. Edit rule modal
5. Enable/disable toggle
6. Delete with confirmation
7. Rule priority reordering (drag-drop)
8. Rule effectiveness chart (success rate over time)
9. Bulk actions (enable/disable multiple)
10. Rule templates (common patterns for quick setup)

### Files to Create

- `/frontend/src/pages/Settings/CategorizationRules.tsx` - Page
- `/frontend/src/components/features/Rules/` - Sub-components
  - `RulesList.tsx`
  - `RuleCard.tsx`
  - `RuleForm.tsx`
  - `RuleFromTransactionModal.tsx`
  - `RuleEffectivenessChart.tsx`
- `/frontend/src/hooks/useCategorizationRules.ts` - Queries
- `/frontend/src/services/rulesService.ts` - API

### Test Requirements

- Render rules list
- Create/edit/delete rules
- Reorder rules
- View statistics
- **Minimum coverage**: 80%

### Technical Notes for AI Agent

1. **RuleForm Component**:
   - Input: merchant pattern, description pattern
   - Select: category, priority, match type (regex/substring)
   - Input: amount range (optional)
   - Input: transaction type filter (optional)
   - Toggle: enabled
   - Button: Test pattern (show matching transactions)

2. **Rule Reordering**:
   - Use react-beautiful-dnd or @dnd-kit/core
   - Drag rules to reorder
   - Save new priority to backend

3. **Rule Templates**:
   ```typescript
   const RULE_TEMPLATES = [
     {
       name: 'Food & Dining',
       patterns: ['restaurant|cafe|food|eatery|pho|pizza'],
       category: 'Food & Dining',
     },
     {
       name: 'Transportation',
       patterns: ['uber|grab|taxi|fuel|gas|parking'],
       category: 'Transportation',
     },
     // More templates...
   ];
   ```

### Documentation Needed

- Rules management guide
- Pattern syntax documentation

---

## WBS-002-06: Implement "Learn from User" Flow (Suggest Creating Rule)

**Status**: NOT STARTED
**Priority**: P1
**Estimated Effort**: 12 hours
**Dependencies**: WBS-002-02, WBS-002-04

### Description

Implement intelligent suggestion system that notifies users when they manually categorize similar transactions multiple times. Suggest auto-creating a rule for that pattern. Show suggestion in UI with example transactions and confidence score.

### Acceptance Criteria

1. Detect repeated manual categorizations (same category for similar transactions)
2. Calculate pattern confidence (how sure we are about the rule)
3. Show suggestion toast/notification
4. "Create Rule" button with auto-generated pattern
5. Show matching example transactions
6. Allow customizing rule before creating
7. Track suggestion acceptance rate
8. Don't suggest if rule already exists
9. Defer suggestion option (hide for 7 days)
10. Learn from both accepted and rejected suggestions

### Files to Create

- `/frontend/src/components/features/Suggestions/` - Suggestion components
  - `RuleSuggestionToast.tsx`
  - `RuleSuggestionModal.tsx`
- `/frontend/src/hooks/useRuleSuggestions.ts` - Query suggestions
- `/backend/app/services/suggestion_engine.py` - Generate suggestions

### Files to Modify

- `/backend/app/services/pattern_learner.py` - Integrate suggestion detection
- `/frontend/src/pages/Transactions/TransactionList.tsx` - Show suggestions

### Test Requirements

- Test suggestion generation
- Test confidence calculation
- Test suggestion display
- **Minimum coverage**: 80%

### Technical Notes for AI Agent

1. **Suggestion Detection**:
   - On each manual categorization, check if similar
   - Look for 3+ transactions with same category in last 30 days
   - Calculate keyword overlap
   - If confidence > 70%, suggest rule

2. **Toast Notification**:
   ```typescript
   interface RuleSuggestion {
     title: string;        // "Tạo quy tắc cho Nhà hàng?"
     category: string;
     exampleTransactions: Transaction[];
     confidence: number;   // 0-1
     suggestedPattern: string;
   }
   ```

3. **User Feedback Loop**:
   - Track accepted suggestions
   - Track rejected suggestions
   - Track deferred suggestions
   - Improve accuracy over time

### Documentation Needed

- Suggestion algorithm explanation

---

## WBS-002-07: Seed Default Categories for Vietnamese Users

**Status**: NOT STARTED
**Priority**: P1
**Estimated Effort**: 10 hours
**Dependencies**: WBS-002-01

### Description

Create comprehensive category hierarchy for Vietnamese users. Include common categories: Food, Transportation, Utilities, Entertainment, etc. Each category has color code and icon. Seed default rules for common transactions (e.g., "Starbucks" → Food, ATM → Withdrawal).

### Acceptance Criteria

1. 20-30 main categories with Vietnamese names
2. Subcategories (2-3 levels deep)
3. Each category has: color code, icon, description
4. Default rules for common merchants (30-50 rules)
5. Rules for transaction types (ATM, online purchases, etc.)
6. Support multiple currencies (default VND)
7. Rules data in database seed/migration
8. Categories exported as JSON for reference
9. Easy to customize/extend per user
10. Localization-ready (i18n support)

### Files to Create

- `/backend/alembic/versions/009_seed_categories.py` - Migration
- `/backend/app/data/default_categories.json` - Category definitions
- `/backend/app/data/default_rules.json` - Default rules
- `/backend/scripts/seed_categories.py` - Seed script

### Test Requirements

- Test seed migration
- Test category hierarchy
- Test default rules work
- **Minimum coverage**: 70%

### Technical Notes for AI Agent

1. **Default Categories** (Vietnamese):
   ```json
   {
     "categories": [
       {
         "name": "Ăn & Uống",
         "color": "#FF6B6B",
         "icon": "utensils",
         "subcategories": [
           {"name": "Nhà hàng", "color": "#FF8787"},
           {"name": "Cà phê", "color": "#FFA5A5"},
           {"name": "Giao đồ ăn", "color": "#FFC3C3"}
         ]
       },
       {
         "name": "Giao thông",
         "color": "#4ECDC4",
         "subcategories": [
           {"name": "Xăng dầu", "color": "#6EE7DE"},
           {"name": "Xe Grab/Uber", "color": "#87F5F0"}
         ]
       },
       // More categories...
     ]
   }
   ```

2. **Default Rules**:
   ```json
   {
     "rules": [
       {
         "merchant_pattern": "starbucks|coffee|cafe",
         "category_name": "Cà phê",
         "priority": 100,
         "match_type": "regex"
       },
       {
         "merchant_pattern": "atm|rut tien",
         "category_name": "Rút tiền",
         "priority": 90
       }
     ]
   }
   ```

3. **Seed Migration**:
   ```python
   async def upgrade():
       """Seed default categories and rules."""
       # Load JSON files
       with open('app/data/default_categories.json') as f:
           categories_data = json.load(f)

       # Insert categories
       for cat_def in categories_data['categories']:
           await insert_category(cat_def)

       # Insert rules
       with open('app/data/default_rules.json') as f:
           rules_data = json.load(f)

       for rule_def in rules_data['rules']:
           await insert_rule(rule_def)
   ```

### Documentation Needed

- Category hierarchy documentation
- Default rules list

---

## WBS-002-08: Implement Category Analytics (Which Rules Fire Most, Coverage %)

**Status**: NOT STARTED
**Priority**: P2
**Estimated Effort**: 14 hours
**Dependencies**: WBS-002-01

### Description

Implement analytics dashboard showing categorization effectiveness. Track which rules match most frequently, overall categorization coverage (% of transactions with category), success rates, and trends over time. Identify uncategorizable transaction types.

### Acceptance Criteria

1. Dashboard page with category analytics
2. Rule effectiveness ranking (top 10 most-matched rules)
3. Overall categorization coverage % (categorized / total)
4. Coverage by transaction type breakdown
5. Category distribution (pie chart)
6. Trend chart (coverage over 30 days)
7. Identify gap categories (transactions with no matching rule)
8. Rule overlap detection (rules with similar patterns)
9. Suggestions for new rules (based on gaps)
10. Export analytics as PDF/CSV

### Files to Create

- `/backend/app/services/analytics_service.py` - Analytics calculations
- `/backend/app/api/analytics.py` - Analytics endpoints
- `/frontend/src/pages/Analytics/CategorizationAnalytics.tsx` - Dashboard
- `/frontend/src/components/features/Analytics/` - Charts
  - `RuleEffectivenessChart.tsx`
  - `CoverageTrendChart.tsx`
  - `CategoryDistributionChart.tsx`

### Files to Modify

- `/frontend/src/pages/Dashboard.tsx` - Add analytics link

### Test Requirements

- Test analytics calculation
- Test chart rendering
- Test trend calculation
- **Minimum coverage**: 75%

### Technical Notes for AI Agent

1. **Metrics**:
   ```python
   def calculate_coverage_stats(user_id: str) -> dict:
       """Calculate categorization coverage."""
       total = count_transactions(user_id)
       categorized = count_transactions(
           user_id,
           category_id__isnull=False
       )
       coverage = categorized / total if total > 0 else 0
       return {
           'total': total,
           'categorized': categorized,
           'coverage': coverage,
           'by_type': {
               'income': calculate_type_coverage('income'),
               'expense': calculate_type_coverage('expense'),
               'transfer': calculate_type_coverage('transfer'),
           }
       }
   ```

2. **Rule Effectiveness**:
   - Sort rules by match_count
   - Calculate success_rate = successful_categorizations / total_matches
   - Filter rules with < 10 matches (too new to judge)

3. **Charts**:
   - Rule effectiveness: Bar chart (rule name vs match count)
   - Coverage trend: Line chart (date vs coverage %)
   - Category distribution: Pie chart (category vs count)

### Documentation Needed

- Analytics dashboard guide
- Metric calculations explanation

---

## Summary

**Total Feature Effort**: 120-150 hours (8 tasks)

**Critical Path**: WBS-002-01 → WBS-002-03 → WBS-002-04

**Dependencies**: All tasks depend on WBS-001 completion

**Outcome**:
- Intelligent categorization system
- Rules management UI
- Analytics dashboard
- Foundation for WBS-003 (Split Bills)
- Enhanced with WBS-005 (Reports)
