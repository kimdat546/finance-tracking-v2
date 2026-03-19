import client from './client'
import type {
  Budget,
  BudgetAlert,
  BudgetCreateRequest,
  BudgetListResponse,
  BudgetSummary,
  Debt,
  DebtCreateRequest,
  DebtListResponse,
  DebtPaymentRequest,
  DebtSummary,
  Goal,
  GoalCreateRequest,
  GoalListResponse,
  GoalSummary,
  Subscription,
  SubscriptionCreateRequest,
  SubscriptionDetectionResult,
  SubscriptionListResponse,
  SubscriptionSummary,
} from '@/types/planning'

// ---------------------------------------------------------------------------
// Budget API
// ---------------------------------------------------------------------------

export const budgetApi = {
  listBudgets: async (activeOnly = true): Promise<BudgetListResponse> => {
    const response = await client.get<BudgetListResponse>('/planning/budgets', {
      params: { active_only: activeOnly },
    })
    return response.data
  },

  getBudget: async (budgetId: string): Promise<Budget> => {
    const response = await client.get<Budget>(`/planning/budgets/${budgetId}`)
    return response.data
  },

  createBudget: async (data: BudgetCreateRequest): Promise<Budget> => {
    const response = await client.post<Budget>('/planning/budgets', data)
    return response.data
  },

  updateBudget: async (budgetId: string, data: Partial<BudgetCreateRequest>): Promise<Budget> => {
    const response = await client.put<Budget>(`/planning/budgets/${budgetId}`, data)
    return response.data
  },

  deleteBudget: async (budgetId: string): Promise<void> => {
    await client.delete(`/planning/budgets/${budgetId}`)
  },

  getAlerts: async (): Promise<BudgetAlert[]> => {
    const response = await client.get<BudgetAlert[]>('/planning/budgets/alerts')
    return response.data
  },

  getSummary: async (): Promise<BudgetSummary> => {
    const response = await client.get<BudgetSummary>('/planning/budgets/summary')
    return response.data
  },
}

// ---------------------------------------------------------------------------
// Goal API
// ---------------------------------------------------------------------------

export const goalApi = {
  listGoals: async (activeOnly = true): Promise<GoalListResponse> => {
    const response = await client.get<GoalListResponse>('/planning/goals', {
      params: { active_only: activeOnly },
    })
    return response.data
  },

  getGoal: async (goalId: string): Promise<Goal> => {
    const response = await client.get<Goal>(`/planning/goals/${goalId}`)
    return response.data
  },

  createGoal: async (data: GoalCreateRequest): Promise<Goal> => {
    const response = await client.post<Goal>('/planning/goals', data)
    return response.data
  },

  updateGoal: async (goalId: string, data: Partial<GoalCreateRequest>): Promise<Goal> => {
    const response = await client.put<Goal>(`/planning/goals/${goalId}`, data)
    return response.data
  },

  deleteGoal: async (goalId: string): Promise<void> => {
    await client.delete(`/planning/goals/${goalId}`)
  },

  addContribution: async (goalId: string, amount: number): Promise<Goal> => {
    const response = await client.post<Goal>(
      `/planning/goals/${goalId}/contribute`,
      null,
      { params: { amount } }
    )
    return response.data
  },

  getSummary: async (): Promise<GoalSummary> => {
    const response = await client.get<GoalSummary>('/planning/goals/summary')
    return response.data
  },
}

// ---------------------------------------------------------------------------
// Debt API
// ---------------------------------------------------------------------------

export const debtApi = {
  listDebts: async (debtType?: 'owe' | 'owed'): Promise<DebtListResponse> => {
    const response = await client.get<DebtListResponse>('/planning/debts', {
      params: debtType ? { debt_type: debtType } : undefined,
    })
    return response.data
  },

  createDebt: async (data: DebtCreateRequest): Promise<Debt> => {
    const response = await client.post<Debt>('/planning/debts', data)
    return response.data
  },

  updateDebt: async (debtId: string, data: Partial<DebtCreateRequest>): Promise<Debt> => {
    const response = await client.put<Debt>(`/planning/debts/${debtId}`, data)
    return response.data
  },

  deleteDebt: async (debtId: string): Promise<void> => {
    await client.delete(`/planning/debts/${debtId}`)
  },

  recordPayment: async (debtId: string, data: DebtPaymentRequest): Promise<Debt> => {
    const response = await client.post<Debt>(`/planning/debts/${debtId}/payment`, data)
    return response.data
  },

  getSummary: async (): Promise<DebtSummary> => {
    const response = await client.get<DebtSummary>('/planning/debts/summary')
    return response.data
  },
}

// ---------------------------------------------------------------------------
// Subscription API
// ---------------------------------------------------------------------------

export const subscriptionApi = {
  listSubscriptions: async (activeOnly = true): Promise<SubscriptionListResponse> => {
    const response = await client.get<SubscriptionListResponse>('/planning/subscriptions', {
      params: { active_only: activeOnly },
    })
    return response.data
  },

  createSubscription: async (data: SubscriptionCreateRequest): Promise<Subscription> => {
    const response = await client.post<Subscription>('/planning/subscriptions', data)
    return response.data
  },

  updateSubscription: async (
    subId: string,
    data: Partial<SubscriptionCreateRequest>
  ): Promise<Subscription> => {
    const response = await client.put<Subscription>(`/planning/subscriptions/${subId}`, data)
    return response.data
  },

  cancelSubscription: async (subId: string): Promise<void> => {
    await client.delete(`/planning/subscriptions/${subId}`)
  },

  detectSubscriptions: async (): Promise<SubscriptionDetectionResult[]> => {
    const response = await client.get<SubscriptionDetectionResult[]>(
      '/planning/subscriptions/detect'
    )
    return response.data
  },

  getUpcomingRenewals: async (days = 7): Promise<SubscriptionListResponse> => {
    const response = await client.get<SubscriptionListResponse>(
      '/planning/subscriptions/upcoming',
      { params: { days } }
    )
    return response.data
  },

  getSummary: async (): Promise<SubscriptionSummary> => {
    const response = await client.get<SubscriptionSummary>('/planning/subscriptions/summary')
    return response.data
  },
}
