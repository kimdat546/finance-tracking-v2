import React from 'react'
import { TrendingUp, TrendingDown, Wallet, AlertCircle } from 'lucide-react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui'
import { useTransactionStatistics } from '@/hooks/use-transactions'
import { formatVND, formatDate } from '@/utils/format'

const mockChartData = [
  { month: 'T1', income: 5000000, expense: 3000000 },
  { month: 'T2', income: 6000000, expense: 3500000 },
  { month: 'T3', income: 5500000, expense: 3200000 },
  { month: 'T4', income: 7000000, expense: 4000000 },
  { month: 'T5', income: 8000000, expense: 4500000 },
  { month: 'T6', income: 7500000, expense: 4200000 },
]

const mockRecentTransactions = [
  {
    id: '1',
    description: 'Mua sắm tại siêu thị',
    amount: 500000,
    category: 'Mua sắm',
    date: '2026-03-14',
    direction: 'outflow' as const,
  },
  {
    id: '2',
    description: 'Lương tháng 3',
    amount: 8000000,
    category: 'Lương',
    date: '2026-03-01',
    direction: 'inflow' as const,
  },
  {
    id: '3',
    description: 'Thanh toán điện',
    amount: 250000,
    category: 'Tiện ích',
    date: '2026-03-10',
    direction: 'outflow' as const,
  },
  {
    id: '4',
    description: 'Ăn tối nhà hàng',
    amount: 350000,
    category: 'Ăn uống',
    date: '2026-03-12',
    direction: 'outflow' as const,
  },
]

export const DashboardPage: React.FC = () => {
  const { data: statistics, isLoading } = useTransactionStatistics()

  const totalIncome = statistics?.totalIncome || 7500000
  const totalExpense = statistics?.totalExpense || 4200000
  const netSavings = totalIncome - totalExpense

  const SummaryCard: React.FC<{
    title: string
    value: number
    subtext?: string
    icon: React.ReactNode
    color: 'green' | 'red' | 'blue'
  }> = ({ title, value, subtext, icon, color }) => {
    const colorMap = {
      green: 'bg-success-50 dark:bg-success-900/30 text-success-700 dark:text-success-300',
      red: 'bg-danger-50 dark:bg-danger-900/30 text-danger-700 dark:text-danger-300',
      blue: 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300',
    }

    return (
      <Card>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
              {title}
            </p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatVND(value)}
            </p>
            {subtext && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {subtext}
              </p>
            )}
          </div>
          <div className={`p-3 rounded-lg ${colorMap[color]}`}>{icon}</div>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          title="Tổng Thu Nhập"
          value={totalIncome}
          icon={<TrendingUp className="w-6 h-6" />}
          color="green"
          subtext="Tháng này"
        />
        <SummaryCard
          title="Tổng Chi Tiêu"
          value={totalExpense}
          icon={<TrendingDown className="w-6 h-6" />}
          color="red"
          subtext="Tháng này"
        />
        <SummaryCard
          title="Tiết Kiệm Ròng"
          value={netSavings}
          icon={<Wallet className="w-6 h-6" />}
          color="blue"
          subtext={`${((netSavings / totalIncome) * 100).toFixed(1)}% thu nhập`}
        />
        <SummaryCard
          title="Cần Xem Xét"
          value={2}
          icon={<AlertCircle className="w-6 h-6" />}
          color="red"
          subtext="Giao dịch"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Xu Hướng Thu-Chi Hàng Tháng</CardTitle>
            <CardDescription>Thu nhập và chi tiêu trong 6 tháng qua</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={mockChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip formatter={(value) => formatVND(value as number)} />
                <Legend />
                <Bar dataKey="income" fill="#10B981" name="Thu nhập" />
                <Bar dataKey="expense" fill="#EF4444" name="Chi tiêu" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Savings Trend */}
        <Card>
          <CardHeader>
            <CardTitle>Xu Hướng Tiết Kiệm</CardTitle>
            <CardDescription>Tiền tiết kiệm ròng hàng tháng</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={mockChartData.map((d) => ({
                month: d.month,
                savings: d.income - d.expense,
              }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
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

      {/* Recent Transactions */}
      <Card>
        <CardHeader>
          <CardTitle>Giao Dịch Gần Đây</CardTitle>
          <CardDescription>10 giao dịch mới nhất của bạn</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Mô Tả
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Danh Mục
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Ngày
                  </th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                    Số Tiền
                  </th>
                </tr>
              </thead>
              <tbody>
                {mockRecentTransactions.map((tx) => (
                  <tr
                    key={tx.id}
                    className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                  >
                    <td className="py-3 px-4 text-gray-900 dark:text-white">
                      {tx.description}
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      {tx.category}
                    </td>
                    <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                      {formatDate(tx.date)}
                    </td>
                    <td className={`py-3 px-4 text-right font-semibold ${
                      tx.direction === 'inflow'
                        ? 'text-success-600 dark:text-success-400'
                        : 'text-danger-600 dark:text-danger-400'
                    }`}>
                      {tx.direction === 'inflow' ? '+' : '-'}
                      {formatVND(tx.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
