import apiClient, { getCurrentUserId } from './client';
import type {
  AccountBalance,
  BudgetAlert,
  CategoryTrend,
  DashboardSummary,
  MonthlyComparison,
  MonthlyReport,
  NetWorth,
  NetWorthSnapshot,
  QuickStats,
  RecurringTransaction,
  SpendingAnomaly,
} from '@/types/reports';

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await apiClient.get('/reports/dashboard/summary', {
    params: { user_id: getCurrentUserId() },
  });
  return data;
}

export async function getQuickStats(): Promise<QuickStats> {
  const { data } = await apiClient.get('/reports/dashboard/quick-stats', {
    params: { user_id: getCurrentUserId() },
  });
  return data;
}

export async function getAccountBalances(): Promise<AccountBalance[]> {
  const { data } = await apiClient.get('/reports/dashboard/account-balances', {
    params: { user_id: getCurrentUserId() },
  });
  return data;
}

export async function getNetWorthDashboard(): Promise<NetWorth> {
  const { data } = await apiClient.get('/reports/dashboard/net-worth', {
    params: { user_id: getCurrentUserId() },
  });
  return data;
}

export async function getMonthlyReport(year?: number, month?: number): Promise<MonthlyReport> {
  const { data } = await apiClient.get('/reports/monthly', {
    params: { user_id: getCurrentUserId(), year: year ?? 0, month: month ?? 0 },
  });
  return data;
}

export async function getMonthlyComparison(months = 6): Promise<MonthlyComparison[]> {
  const { data } = await apiClient.get('/reports/monthly/comparison', {
    params: { user_id: getCurrentUserId(), months },
  });
  return data;
}

export async function getCategoryTrends(months = 6): Promise<CategoryTrend[]> {
  const { data } = await apiClient.get('/reports/trends/categories', {
    params: { user_id: getCurrentUserId(), months },
  });
  return data;
}

export async function getAnomalies(): Promise<SpendingAnomaly[]> {
  const { data } = await apiClient.get('/reports/trends/anomalies', {
    params: { user_id: getCurrentUserId() },
  });
  return data;
}

export async function getRecurringTransactions(): Promise<RecurringTransaction[]> {
  const { data } = await apiClient.get('/reports/trends/recurring', {
    params: { user_id: getCurrentUserId() },
  });
  return data;
}

export async function getCurrentNetWorth(): Promise<NetWorth> {
  const { data } = await apiClient.get('/reports/net-worth', {
    params: { user_id: getCurrentUserId() },
  });
  return data;
}

export async function getNetWorthHistory(months = 12): Promise<NetWorthSnapshot[]> {
  const { data } = await apiClient.get('/reports/net-worth/history', {
    params: { user_id: getCurrentUserId(), months },
  });
  return data;
}

export type { BudgetAlert, CategoryTrend, DashboardSummary, MonthlyComparison, MonthlyReport, NetWorth, NetWorthSnapshot, QuickStats, RecurringTransaction, SpendingAnomaly };
