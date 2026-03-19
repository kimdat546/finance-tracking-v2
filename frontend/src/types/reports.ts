// ---------------------------------------------------------------------------
// Report API response types — aligned with backend service layer
// ---------------------------------------------------------------------------

export interface TopCategory {
  name: string;
  amount: number;
  count: number;
}

export interface RecentTransaction {
  id: string;
  description: string;
  amount: number;
  type: string;
  transaction_date: string;
  merchant: string | null;
  category: string | null;
}

export interface BudgetAlert {
  budget_id: string;
  name: string;
  category: string | null;
  limit_amount: number;
  spent_amount: number;
  percentage_used: number;
}

export interface DashboardSummary {
  total_income: number;
  total_expense: number;
  net_cashflow: number;
  transaction_count: number;
  top_categories: TopCategory[];
  recent_transactions: RecentTransaction[];
  budget_alerts: BudgetAlert[];
  savings_rate: number;
}

export interface QuickStats {
  this_month_spend: number;
  last_month_spend: number;
  spend_change_pct: number;
  savings_current: number;
  savings_target: number;
  savings_progress_pct: number;
  upcoming_renewals_count: number;
  unresolved_split_bills_count: number;
}

export interface AccountBalance {
  id: string;
  name: string;
  account_type: string;
  balance: number;
  currency: string;
  institution: string | null;
}

export interface NetWorth {
  assets: number;
  liabilities: number;
  net_worth: number;
}

export interface NetWorthAccount {
  id: string;
  name: string;
  balance: number;
  currency: string;
}

export interface NetWorthDebt {
  id: string;
  name: string;
  remaining: number;
  currency: string;
}

export interface NetWorthSnapshot {
  assets: number;
  liabilities: number;
  net_worth: number;
  accounts?: NetWorthAccount[];
  debts?: NetWorthDebt[];
}

export interface CategoryBreakdown {
  category_id: string;
  name: string;
  amount: number;
  count: number;
}

export interface DailyExpense {
  date: string;
  amount: number;
}

export interface MerchantSummary {
  name: string;
  amount: number;
  count: number;
}

export interface BudgetPerformance {
  category: string;
  budgeted: number;
  actual: number;
  variance: number;
}

export interface MonthlyReport {
  period: string;
  income: {
    total: number;
    by_category: CategoryBreakdown[];
  };
  expenses: {
    total: number;
    by_category: CategoryBreakdown[];
    by_day: DailyExpense[];
  };
  net: number;
  savings_rate: number;
  vs_previous_month: {
    income_change: number;
    expense_change: number;
  };
  top_merchants: MerchantSummary[];
  budget_performance: BudgetPerformance[];
  transaction_count: number;
}

export interface MonthlyComparison {
  month: string;
  income: number;
  expense: number;
  net: number;
}

export interface CategoryTrend {
  month: string;
  categories: Record<string, number>;
}

export interface SpendingAnomaly {
  transaction_id: string;
  amount: number;
  category: string;
  category_avg: number;
  z_score: number;
  transaction_date: string;
  description: string;
}

export interface RecurringTransaction {
  merchant: string | null;
  description: string | null;
  occurrences: number;
  avg_amount: number;
  is_consistent_amount: boolean;
}
