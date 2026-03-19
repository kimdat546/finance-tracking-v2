import React from 'react'
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  AlertCircle,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui'
import { formatVND, formatDate } from '@/utils/format'
import {
  useDashboardSummary,
  useQuickStats,
  useMonthlyComparison,
  useAccountBalances,
} from '@/hooks/useReports'

const MONTH_LABELS = ['T1','T2','T3','T4','T5','T6','T7','T8','T9','T10','T11','T12']

export const DashboardPage: React.FC = () => {
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary()
  const { data: quickStats } = useQuickStats()
  const { data: comparison = [] } = useMonthlyComparison(6)
  const { data: accounts = [] } = useAccountBalances()

  const chartData = comparison.map((m) => ({
    month: MONTH_LABELS[(m.month - 1) % 12],
    income: m.total_income,
    expense: m.total_expense,
    savings: m.net_cashflow,
  }))

  const spendChangePct = quickStats?.spend_change_pct ?? 0

  if (summaryLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Income */}
        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Tổng Thu Nhập</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatVND(summary?.total_income ?? 0)}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Tháng này</p>
            </div>
            <div className="p-3 rounded-lg bg-success-50 dark:bg-success-900/30 text-success-700 dark:text-success-300">
              <TrendingUp className="w-6 h-6" />
            </div>
          </div>
        </Card>

        {/* Expense */}
        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Tổng Chi Tiêu</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatVND(summary?.total_expense ?? 0)}
              </p>
              <div className="flex items-center gap-1 mt-1">
                {spendChangePct > 0 ? (
                  <ArrowUpRight className="w-3 h-3 text-danger-500" />
                ) : (
                  <ArrowDownRight className="w-3 h-3 text-success-500" />
                )}
                <p className={`text-xs ${spendChangePct > 0 ? 'text-danger-500' : 'text-success-500'}`}>
                  {Math.abs(spendChangePct).toFixed(1)}% so tháng trước
                </p>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-danger-50 dark:bg-danger-900/30 text-danger-700 dark:text-danger-300">
              <TrendingDown className="w-6 h-6" />
            </div>
          </div>
        </Card>

        {/* Net Cashflow */}
        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Tiết Kiệm Ròng</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatVND(summary?.net_cashflow ?? 0)}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {summary ? `${summary.savings_rate.toFixed(1)}% thu nhập` : '—'}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300">
              <Wallet className="w-6 h-6" />
            </div>
          </div>
        </Card>

        {/* Alerts */}
        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Cảnh Báo Ngân Sách</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {summary?.budget_alerts?.length ?? 0}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Ngân sách vượt 80%</p>
            </div>
            <div className="p-3 rounded-lg bg-warning-50 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300">
              <AlertCircle className="w-6 h-6" />
            </div>
          </div>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Xu Hướng Thu-Chi Hàng Tháng</CardTitle>
            <CardDescription>Thu nhập và chi tiêu trong 6 tháng qua</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis tickFormatter={(v) => `${(v / 1_000_000).toFixed(0)}M`} />
                <Tooltip formatter={(value) => formatVND(value as number)} />
                <Legend />
                <Bar dataKey="income" fill="#10B981" name="Thu nhập" />
                <Bar dataKey="expense" fill="#EF4444" name="Chi tiêu" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Xu Hướng Tiết Kiệm</CardTitle>
            <CardDescription>Tiền tiết kiệm ròng hàng tháng</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis tickFormatter={(v) => `${(v / 1_000_000).toFixed(0)}M`} />
                <Tooltip formatter={(value) => formatVND(value as number)} />
                <Line
                  type="monotone"
                  dataKey="savings"
                  stroke="#3B82F6"
                  strokeWidth={2}
                  dot={{ fill: '#3B82F6' }}
                  name="Tiết kiệm"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Bottom row: top categories + recent transactions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Categories */}
        <Card>
          <CardHeader>
            <CardTitle>Danh Mục Chi Tiêu</CardTitle>
            <CardDescription>Top 5 tháng này</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(summary?.top_categories ?? []).map((cat) => (
                <div key={cat.name}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-700 dark:text-gray-300">{cat.name}</span>
                    <span className="font-medium text-gray-900 dark:text-white">{formatVND(cat.amount)}</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 rounded-full"
                      style={{
                        width: `${summary?.total_expense ? Math.min((cat.amount / summary.total_expense) * 100, 100) : 0}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
              {(summary?.top_categories ?? []).length === 0 && (
                <p className="text-sm text-gray-500 dark:text-gray-400">Chưa có dữ liệu</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Recent Transactions */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Giao Dịch Gần Đây</CardTitle>
              <CardDescription>5 giao dịch mới nhất</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                      <th className="text-left py-2 px-3 font-semibold text-gray-700 dark:text-gray-300">Mô Tả</th>
                      <th className="text-left py-2 px-3 font-semibold text-gray-700 dark:text-gray-300">Danh Mục</th>
                      <th className="text-left py-2 px-3 font-semibold text-gray-700 dark:text-gray-300">Ngày</th>
                      <th className="text-right py-2 px-3 font-semibold text-gray-700 dark:text-gray-300">Số Tiền</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(summary?.recent_transactions ?? []).map((tx) => (
                      <tr
                        key={tx.id}
                        className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                      >
                        <td className="py-2 px-3 text-gray-900 dark:text-white truncate max-w-[160px]">
                          {tx.description}
                        </td>
                        <td className="py-2 px-3 text-gray-600 dark:text-gray-400">{tx.category ?? '—'}</td>
                        <td className="py-2 px-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">
                          {formatDate(tx.transaction_date)}
                        </td>
                        <td
                          className={`py-2 px-3 text-right font-semibold whitespace-nowrap ${
                            tx.type === 'income'
                              ? 'text-success-600 dark:text-success-400'
                              : 'text-danger-600 dark:text-danger-400'
                          }`}
                        >
                          {tx.type === 'income' ? '+' : '-'}
                          {formatVND(tx.amount)}
                        </td>
                      </tr>
                    ))}
                    {(summary?.recent_transactions ?? []).length === 0 && (
                      <tr>
                        <td colSpan={4} className="py-6 text-center text-gray-500 dark:text-gray-400">
                          Chưa có giao dịch
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Account Balances */}
      {accounts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Số Dư Tài Khoản</CardTitle>
            <CardDescription>Tất cả tài khoản đang hoạt động</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {accounts.map((acc) => (
                <div
                  key={acc.id}
                  className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                >
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{acc.name}</p>
                  {acc.institution && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">{acc.institution}</p>
                  )}
                  <p className="text-xl font-bold text-gray-900 dark:text-white mt-2">
                    {formatVND(acc.balance)}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">{acc.account_type}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Budget Alerts */}
      {(summary?.budget_alerts ?? []).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-warning-600 dark:text-warning-400">
              <AlertCircle className="w-5 h-5" />
              Cảnh Báo Ngân Sách
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {summary!.budget_alerts.map((alert) => (
                <div
                  key={alert.budget_id}
                  className="flex items-center justify-between p-3 rounded-lg bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800"
                >
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{alert.name}</p>
                    {alert.category && (
                      <p className="text-xs text-gray-500 dark:text-gray-400">{alert.category}</p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className={`font-bold ${alert.percentage_used >= 100 ? 'text-danger-600' : 'text-warning-600'}`}>
                      {alert.percentage_used.toFixed(0)}%
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatVND(alert.spent_amount)} / {formatVND(alert.limit_amount)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
