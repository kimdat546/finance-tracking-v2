import { useQuery } from '@tanstack/react-query';
import {
  getAccountBalances,
  getAnomalies,
  getCategoryTrends,
  getCurrentNetWorth,
  getDashboardSummary,
  getMonthlyComparison,
  getMonthlyReport,
  getNetWorthDashboard,
  getNetWorthHistory,
  getQuickStats,
  getRecurringTransactions,
} from '@/api/reports';

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: getDashboardSummary,
  });
}

export function useQuickStats() {
  return useQuery({
    queryKey: ['dashboard', 'quick-stats'],
    queryFn: getQuickStats,
  });
}

export function useAccountBalances() {
  return useQuery({
    queryKey: ['dashboard', 'account-balances'],
    queryFn: getAccountBalances,
  });
}

export function useNetWorthDashboard() {
  return useQuery({
    queryKey: ['dashboard', 'net-worth'],
    queryFn: getNetWorthDashboard,
  });
}

export function useMonthlyReport(year?: number, month?: number) {
  return useQuery({
    queryKey: ['reports', 'monthly', year, month],
    queryFn: () => getMonthlyReport(year, month),
  });
}

export function useMonthlyComparison(months = 6) {
  return useQuery({
    queryKey: ['reports', 'monthly-comparison', months],
    queryFn: () => getMonthlyComparison(months),
  });
}

export function useCategoryTrends(months = 6) {
  return useQuery({
    queryKey: ['reports', 'category-trends', months],
    queryFn: () => getCategoryTrends(months),
  });
}

export function useAnomalies() {
  return useQuery({
    queryKey: ['reports', 'anomalies'],
    queryFn: getAnomalies,
  });
}

export function useRecurringTransactions() {
  return useQuery({
    queryKey: ['reports', 'recurring'],
    queryFn: getRecurringTransactions,
  });
}

export function useCurrentNetWorth() {
  return useQuery({
    queryKey: ['reports', 'net-worth'],
    queryFn: getCurrentNetWorth,
  });
}

export function useNetWorthHistory(months = 12) {
  return useQuery({
    queryKey: ['reports', 'net-worth-history', months],
    queryFn: () => getNetWorthHistory(months),
  });
}
