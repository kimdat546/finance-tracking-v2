import React, { useState } from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui'
import { formatVND } from '@/utils/format'
import {
  useMonthlyComparison,
  useMonthlyReport,
  useCategoryTrends,
  useAnomalies,
  useRecurringTransactions,
  useCurrentNetWorth,
  useNetWorthHistory,
} from '@/hooks/useReports'

const MONTH_LABELS = ['T1','T2','T3','T4','T5','T6','T7','T8','T9','T10','T11','T12']
const COLORS = ['#3B82F6','#10B981','#EF4444','#F59E0B','#8B5CF6','#EC4899','#14B8A6']

export const ReportsPage: React.FC = () => {
  const [months, setMonths] = useState(6)
  const { data: comparison = [] } = useMonthlyComparison(months)
  const { data: monthly } = useMonthlyReport()
  const { data: trends = [] } = useCategoryTrends(months)
  const { data: anomalies = [] } = useAnomalies()
  const { data: recurring = [] } = useRecurringTransactions()
  const { data: netWorth } = useCurrentNetWorth()
  const { data: netWorthHistory = [] } = useNetWorthHistory(12)

  const comparisonChart = comparison.map((m) => ({
    month: MONTH_LABELS[(m.month - 1) % 12],
    income: m.total_income,
    expense: m.total_expense,
    savings: m.net_cashflow,
  }))

  const categoryPieData = (monthly?.top_categories ?? []).map((c, i) => ({
    name: c.name,
    value: c.amount,
    color: COLORS[i % COLORS.length],
  }))

  const netWorthChart = netWorthHistory.map((s) => ({
    month: `${s.date.slice(0, 7)}`,
    assets: s.assets,
    liabilities: s.liabilities,
    net_worth: s.net_worth,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Báo Cáo Tài Chính
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Phân tích chi tiêu và xu hướng tài chính của bạn
          </p>
        </div>
        <select
          className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
          value={months}
          onChange={(e) => setMonths(Number(e.target.value))}
        >
          <option value={3}>3 tháng</option>
          <option value={6}>6 tháng</option>
          <option value={12}>12 tháng</option>
        </select>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tổng Thu Nhập Tháng Này</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-success-600 dark:text-success-400">
              {formatVND(monthly?.total_income ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tổng Chi Tiêu Tháng Này</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-danger-600 dark:text-danger-400">
              {formatVND(monthly?.total_expense ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tài Sản Ròng Hiện Tại</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-primary-600 dark:text-primary-400">
              {formatVND(netWorth?.net_worth ?? 0)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Tài sản: {formatVND(netWorth?.assets ?? 0)} — Nợ: {formatVND(netWorth?.liabilities ?? 0)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Xu Hướng Thu-Chi</CardTitle>
            <CardDescription>So sánh thu nhập và chi tiêu {months} tháng qua</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={comparisonChart}>
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
            <CardTitle className="text-base">Chi Tiêu Theo Danh Mục</CardTitle>
            <CardDescription>Phân tích tháng hiện tại</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryPieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={100}
                  dataKey="value"
                >
                  {categoryPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => formatVND(value as number)} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Net Worth History */}
      {netWorthHistory.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Lịch Sử Tài Sản Ròng</CardTitle>
            <CardDescription>12 tháng qua</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={netWorthChart}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis tickFormatter={(v) => `${(v / 1_000_000).toFixed(0)}M`} />
                <Tooltip formatter={(value) => formatVND(value as number)} />
                <Legend />
                <Line type="monotone" dataKey="assets" stroke="#10B981" strokeWidth={2} name="Tài sản" />
                <Line type="monotone" dataKey="liabilities" stroke="#EF4444" strokeWidth={2} name="Nợ" />
                <Line type="monotone" dataKey="net_worth" stroke="#3B82F6" strokeWidth={2} name="Ròng" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Category Trends */}
      {trends.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Xu Hướng Theo Danh Mục</CardTitle>
            <CardDescription>{months} tháng qua</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" type="category" allowDuplicatedCategory={false} />
                <YAxis tickFormatter={(v) => `${(v / 1_000_000).toFixed(0)}M`} />
                <Tooltip formatter={(value) => formatVND(value as number)} />
                <Legend />
                {trends.slice(0, 5).map((trend, i) => (
                  <Line
                    key={trend.category}
                    data={trend.data.map((d) => ({
                      month: MONTH_LABELS[(d.month - 1) % 12],
                      amount: d.amount,
                    }))}
                    type="monotone"
                    dataKey="amount"
                    stroke={COLORS[i % COLORS.length]}
                    strokeWidth={2}
                    name={trend.category}
                    dot={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Anomalies */}
      {anomalies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base text-warning-600 dark:text-warning-400">
              Bất Thường Chi Tiêu
            </CardTitle>
            <CardDescription>Chi tiêu vượt mức trung bình đáng kể</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {anomalies.map((a, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 rounded-lg bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800"
                >
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{a.category}</p>
                    <p className="text-xs text-gray-500">{a.description}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-warning-600">{formatVND(a.current_amount)}</p>
                    <p className="text-xs text-gray-500">
                      TB: {formatVND(a.average_amount)} (+{a.deviation_pct.toFixed(0)}%)
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recurring Transactions */}
      {recurring.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Giao Dịch Định Kỳ</CardTitle>
            <CardDescription>Phát hiện tự động từ lịch sử giao dịch</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-2 px-3 font-semibold text-gray-700 dark:text-gray-300">Mô Tả</th>
                    <th className="text-left py-2 px-3 font-semibold text-gray-700 dark:text-gray-300">Số Tiền TB</th>
                    <th className="text-left py-2 px-3 font-semibold text-gray-700 dark:text-gray-300">Tần Suất</th>
                    <th className="text-left py-2 px-3 font-semibold text-gray-700 dark:text-gray-300">Lần Cuối</th>
                    <th className="text-left py-2 px-3 font-semibold text-gray-700 dark:text-gray-300">Số Lần</th>
                  </tr>
                </thead>
                <tbody>
                  {recurring.map((r, i) => (
                    <tr key={i} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-2 px-3 text-gray-900 dark:text-white">{r.description}</td>
                      <td className="py-2 px-3 font-medium">{formatVND(r.average_amount)}</td>
                      <td className="py-2 px-3 text-gray-600 dark:text-gray-400">
                        ~{r.frequency_days} ngày/lần
                      </td>
                      <td className="py-2 px-3 text-gray-600 dark:text-gray-400">{r.last_date}</td>
                      <td className="py-2 px-3 text-gray-600 dark:text-gray-400">{r.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
