// Planning types: Budget, Goal, Debt, Subscription

export interface Budget {
  id: string
  category_id: string
  category_name?: string
  name: string
  amount: number
  period: 'monthly' | 'weekly' | 'yearly' | 'daily' | 'quarterly'
  currency: string
  spent_amount: number
  remaining: number
  percentage_used: number
  start_date: string
  end_date?: string
  is_active: boolean
  alert_threshold: number
}

export interface BudgetListResponse {
  items: Budget[]
  total: number
}

export interface BudgetCreateRequest {
  category_id: string
  name: string
  amount: number
  period: Budget['period']
  start_date: string
  end_date?: string
  currency?: string
  alert_threshold?: number
}

export interface BudgetAlert {
  budget_id: string
  name: string
  percentage_used: number
  spent_amount: number
  limit_amount: number
  alert_threshold: number
  message: string
}

export interface BudgetSummary {
  total_budgeted: number
  total_spent: number
  total_remaining: number
  budget_count: number
  on_track_count: number
  warning_count: number
  over_limit_count: number
}

export interface Goal {
  id: string
  name: string
  description?: string
  target_amount: number
  current_amount: number
  percentage_complete: number
  start_date: string
  target_date: string
  currency: string
  status: 'active' | 'completed' | 'paused' | 'abandoned'
  priority: number
  icon?: string
  color?: string
  is_active: boolean
}

export interface GoalListResponse {
  items: Goal[]
  total: number
}

export interface GoalCreateRequest {
  name: string
  description?: string
  target_amount: number
  start_date: string
  target_date: string
  currency?: string
  priority?: number
  icon?: string
  color?: string
}

export interface GoalSummary {
  total_goals: number
  active_goals: number
  completed_goals: number
  total_target: number
  total_saved: number
  completion_percentage: number
}

export interface Debt {
  id: string
  name: string
  creditor?: string
  description?: string
  amount: number
  paid_amount: number
  remaining_amount: number
  currency: string
  interest_rate?: number
  monthly_payment?: number
  start_date: string
  due_date?: string
  paid_off_date?: string
  debt_type: 'owe' | 'owed'
  status: string
  is_active: boolean
}

export interface DebtListResponse {
  items: Debt[]
  total: number
}

export interface DebtCreateRequest {
  name: string
  creditor: string
  description?: string
  amount: number
  currency?: string
  interest_rate?: number
  monthly_payment?: number
  start_date: string
  due_date?: string
  debt_type: 'owe' | 'owed'
}

export interface DebtPaymentRequest {
  amount: number
  payment_date: string
  notes?: string
}

export interface DebtSummary {
  total_owe: number
  total_owed: number
  net_position: number
  active_debt_count: number
  upcoming_due: Array<{
    debt_id: string
    creditor: string
    due_date: string
    remaining: number
    debt_type: string
  }>
}

export interface Subscription {
  id: string
  name: string
  description?: string
  amount: number
  currency: string
  billing_cycle: 'monthly' | 'yearly' | 'weekly' | 'daily' | 'quarterly'
  start_date: string
  next_billing_date: string
  end_date?: string
  annual_cost: number
  is_active: boolean
  is_auto_renew: boolean
  category_id?: string
}

export interface SubscriptionListResponse {
  items: Subscription[]
  total: number
}

export interface SubscriptionCreateRequest {
  name: string
  description?: string
  amount: number
  currency?: string
  billing_cycle: Subscription['billing_cycle']
  start_date: string
  next_billing_date: string
  end_date?: string
  category_id?: string
  is_auto_renew?: boolean
}

export interface SubscriptionDetectionResult {
  name: string
  amount: number
  suggested_category?: string
  confidence: number
  transaction_ids: string[]
  billing_cycle: string
}

export interface SubscriptionSummary {
  active_count: number
  monthly_cost: number
  yearly_cost: number
  upcoming_renewals_count: number
}
