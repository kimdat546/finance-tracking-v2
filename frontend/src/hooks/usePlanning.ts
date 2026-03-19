import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { budgetApi, debtApi, goalApi, subscriptionApi } from '@/api/planning'
import type {
  BudgetCreateRequest,
  DebtCreateRequest,
  DebtPaymentRequest,
  GoalCreateRequest,
  SubscriptionCreateRequest,
} from '@/types/planning'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const planningKeys = {
  // Budgets
  budgets: ['budgets'] as const,
  budgetList: (activeOnly: boolean) => ['budgets', 'list', activeOnly] as const,
  budgetDetail: (id: string) => ['budgets', 'detail', id] as const,
  budgetAlerts: ['budgets', 'alerts'] as const,
  budgetSummary: ['budgets', 'summary'] as const,

  // Goals
  goals: ['goals'] as const,
  goalList: (activeOnly: boolean) => ['goals', 'list', activeOnly] as const,
  goalDetail: (id: string) => ['goals', 'detail', id] as const,
  goalSummary: ['goals', 'summary'] as const,

  // Debts
  debts: ['debts'] as const,
  debtList: (type?: 'owe' | 'owed') => ['debts', 'list', type] as const,
  debtSummary: ['debts', 'summary'] as const,

  // Subscriptions
  subscriptions: ['subscriptions'] as const,
  subscriptionList: (activeOnly: boolean) => ['subscriptions', 'list', activeOnly] as const,
  subscriptionUpcoming: (days: number) => ['subscriptions', 'upcoming', days] as const,
  subscriptionSummary: ['subscriptions', 'summary'] as const,
  subscriptionDetect: ['subscriptions', 'detect'] as const,
}

// ===========================================================================
// Budget hooks
// ===========================================================================

export const useBudgets = (activeOnly = true) =>
  useQuery({
    queryKey: planningKeys.budgetList(activeOnly),
    queryFn: () => budgetApi.listBudgets(activeOnly),
    staleTime: 5 * 60 * 1000,
  })

export const useBudget = (budgetId?: string) =>
  useQuery({
    queryKey: budgetId ? planningKeys.budgetDetail(budgetId) : ['budget', null],
    queryFn: () => (budgetId ? budgetApi.getBudget(budgetId) : null),
    enabled: !!budgetId,
  })

export const useBudgetAlerts = () =>
  useQuery({
    queryKey: planningKeys.budgetAlerts,
    queryFn: () => budgetApi.getAlerts(),
    staleTime: 2 * 60 * 1000,
  })

export const useBudgetSummary = () =>
  useQuery({
    queryKey: planningKeys.budgetSummary,
    queryFn: () => budgetApi.getSummary(),
    staleTime: 5 * 60 * 1000,
  })

export const useCreateBudget = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: BudgetCreateRequest) => budgetApi.createBudget(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.budgets })
    },
  })
}

export const useUpdateBudget = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      budgetId,
      data,
    }: {
      budgetId: string
      data: Partial<BudgetCreateRequest>
    }) => budgetApi.updateBudget(budgetId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.budgets })
    },
  })
}

export const useDeleteBudget = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (budgetId: string) => budgetApi.deleteBudget(budgetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.budgets })
    },
  })
}

// ===========================================================================
// Goal hooks
// ===========================================================================

export const useGoals = (activeOnly = true) =>
  useQuery({
    queryKey: planningKeys.goalList(activeOnly),
    queryFn: () => goalApi.listGoals(activeOnly),
    staleTime: 5 * 60 * 1000,
  })

export const useGoal = (goalId?: string) =>
  useQuery({
    queryKey: goalId ? planningKeys.goalDetail(goalId) : ['goal', null],
    queryFn: () => (goalId ? goalApi.getGoal(goalId) : null),
    enabled: !!goalId,
  })

export const useGoalSummary = () =>
  useQuery({
    queryKey: planningKeys.goalSummary,
    queryFn: () => goalApi.getSummary(),
    staleTime: 5 * 60 * 1000,
  })

export const useCreateGoal = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: GoalCreateRequest) => goalApi.createGoal(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.goals })
    },
  })
}

export const useUpdateGoal = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      goalId,
      data,
    }: {
      goalId: string
      data: Partial<GoalCreateRequest>
    }) => goalApi.updateGoal(goalId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.goals })
    },
  })
}

export const useDeleteGoal = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (goalId: string) => goalApi.deleteGoal(goalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.goals })
    },
  })
}

export const useAddGoalContribution = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ goalId, amount }: { goalId: string; amount: number }) =>
      goalApi.addContribution(goalId, amount),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.goals })
    },
  })
}

// ===========================================================================
// Debt hooks
// ===========================================================================

export const useDebts = (debtType?: 'owe' | 'owed') =>
  useQuery({
    queryKey: planningKeys.debtList(debtType),
    queryFn: () => debtApi.listDebts(debtType),
    staleTime: 5 * 60 * 1000,
  })

export const useDebtSummary = () =>
  useQuery({
    queryKey: planningKeys.debtSummary,
    queryFn: () => debtApi.getSummary(),
    staleTime: 5 * 60 * 1000,
  })

export const useCreateDebt = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: DebtCreateRequest) => debtApi.createDebt(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.debts })
    },
  })
}

export const useUpdateDebt = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      debtId,
      data,
    }: {
      debtId: string
      data: Partial<DebtCreateRequest>
    }) => debtApi.updateDebt(debtId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.debts })
    },
  })
}

export const useDeleteDebt = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (debtId: string) => debtApi.deleteDebt(debtId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.debts })
    },
  })
}

export const useRecordDebtPayment = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      debtId,
      data,
    }: {
      debtId: string
      data: DebtPaymentRequest
    }) => debtApi.recordPayment(debtId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.debts })
    },
  })
}

// ===========================================================================
// Subscription hooks
// ===========================================================================

export const useSubscriptions = (activeOnly = true) =>
  useQuery({
    queryKey: planningKeys.subscriptionList(activeOnly),
    queryFn: () => subscriptionApi.listSubscriptions(activeOnly),
    staleTime: 5 * 60 * 1000,
  })

export const useUpcomingRenewals = (days = 7) =>
  useQuery({
    queryKey: planningKeys.subscriptionUpcoming(days),
    queryFn: () => subscriptionApi.getUpcomingRenewals(days),
    staleTime: 5 * 60 * 1000,
  })

export const useSubscriptionSummary = () =>
  useQuery({
    queryKey: planningKeys.subscriptionSummary,
    queryFn: () => subscriptionApi.getSummary(),
    staleTime: 5 * 60 * 1000,
  })

export const useDetectSubscriptions = () =>
  useQuery({
    queryKey: planningKeys.subscriptionDetect,
    queryFn: () => subscriptionApi.detectSubscriptions(),
    enabled: false, // only runs on explicit refetch
    staleTime: 0,
  })

export const useCreateSubscription = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: SubscriptionCreateRequest) => subscriptionApi.createSubscription(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.subscriptions })
    },
  })
}

export const useUpdateSubscription = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      subId,
      data,
    }: {
      subId: string
      data: Partial<SubscriptionCreateRequest>
    }) => subscriptionApi.updateSubscription(subId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.subscriptions })
    },
  })
}

export const useCancelSubscription = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (subId: string) => subscriptionApi.cancelSubscription(subId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planningKeys.subscriptions })
    },
  })
}
