import React from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui'
import { BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'

const categoryData = [
  { name: 'Mua sắm', value: 30, color: '#3B82F6' },
  { name: 'Ăn uống', value: 25, color: '#10B981' },
  { name: 'Tiện ích', value: 20, color: '#EF4444' },
  { name: 'Giải trí', value: 15, color: '#F59E0B' },
  { name: 'Khác', value: 10, color: '#8B5CF6' },
]

const monthlyData = [
  { month: 'T1', income: 5000000, expense: 3000000 },
  { month: 'T2', income: 6000000, expense: 3500000 },
  { month: 'T3', income: 5500000, expense: 3200000 },
  { month: 'T4', income: 7000000, expense: 4000000 },
  { month: 'T5', income: 8000000, expense: 4500000 },
  { month: 'T6', income: 7500000, expense: 4200000 },
]

export const ReportsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Báo Cáo Tài Chính
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Phân tích chi tiêu và xu hướng tài chính của bạn
        </p>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Trend */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Xu Hướng Thu-Chi Hàng Tháng</CardTitle>
            <CardDescription>So sánh thu nhập và chi tiêu</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="income" fill="#10B981" name="Thu nhập" />
                <Bar dataKey="expense" fill="#EF4444" name="Chi tiêu" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Spending by Category */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Chi Tiêu Theo Danh Mục</CardTitle>
            <CardDescription>Phân tích chi tiêu chi tiết</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {categoryData.map((entry) => (
                    <Cell key={`cell-${entry.name}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tổng Thu Nhập</CardTitle>
            <CardDescription>Năm nay</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-success-600 dark:text-success-400">
              45.000.000 ₫
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tổng Chi Tiêu</CardTitle>
            <CardDescription>Năm nay</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-danger-600 dark:text-danger-400">
              22.400.000 ₫
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tiết Kiệm Ròng</CardTitle>
            <CardDescription>Năm nay</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-primary-600 dark:text-primary-400">
              22.600.000 ₫
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
