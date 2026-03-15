import React, { useState } from 'react'
import { Search, ChevronDown, Filter, Download } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, Button, Badge } from '@/components/ui'
import { useTransactions, usePendingTransactions } from '@/hooks/use-transactions'
import { formatVND, formatDate } from '@/utils/format'
import { TransactionQueryParams, Transaction } from '@/types'

export const TransactionsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'all' | 'pending'>('all')
  const [params, setParams] = useState<TransactionQueryParams>({
    page: 1,
    pageSize: 20,
    sortBy: 'date',
    sortOrder: 'desc',
  })

  const { data: allTransactions, isLoading: allLoading } = useTransactions(params)
  const { data: pendingTransactions, isLoading: pendingLoading } = usePendingTransactions()

  const transactions = activeTab === 'all' ? allTransactions : pendingTransactions
  const isLoading = activeTab === 'all' ? allLoading : pendingLoading

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'success' | 'danger' | 'warning' | 'info'> = {
      confirmed: 'success',
      pending: 'warning',
      review: 'danger',
    }
    const labels: Record<string, string> = {
      confirmed: 'Đã xác nhận',
      pending: 'Đang chờ',
      review: 'Cần xem xét',
    }
    return (
      <Badge variant={variants[status] || 'default'} size="sm">
        {labels[status] || status}
      </Badge>
    )
  }

  const getDirectionColor = (direction: string) => {
    return direction === 'inflow'
      ? 'text-success-600 dark:text-success-400'
      : 'text-danger-600 dark:text-danger-400'
  }

  return (
    <div className="space-y-6">
      {/* Filter Bar */}
      <Card>
        <CardContent className="py-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Tìm kiếm giao dịch..."
                className="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500"
              />
            </div>

            {/* Date Range */}
            <select className="px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
              <option>Tất cả thời gian</option>
              <option>Tháng này</option>
              <option>Tuần này</option>
              <option>Hôm nay</option>
            </select>

            {/* Category */}
            <select className="px-4 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
              <option>Tất cả danh mục</option>
              <option>Lương</option>
              <option>Mua sắm</option>
              <option>Ăn uống</option>
              <option>Tiện ích</option>
            </select>

            {/* Buttons */}
            <div className="flex gap-2">
              <Button variant="ghost" size="md" className="flex-1">
                <Filter className="w-4 h-4 mr-2" />
                Lọc
              </Button>
              <Button variant="ghost" size="md">
                <Download className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('all')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            activeTab === 'all'
              ? 'border-primary-600 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
          }`}
        >
          Tất Cả Giao Dịch ({allTransactions?.total || 0})
        </button>
        <button
          onClick={() => setActiveTab('pending')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            activeTab === 'pending'
              ? 'border-primary-600 text-primary-600 dark:text-primary-400'
              : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
          }`}
        >
          Cần Xem Xét ({pendingTransactions?.total || 0})
        </button>
      </div>

      {/* Transactions Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-500 dark:text-gray-400">Đang tải...</div>
            </div>
          ) : transactions?.data && transactions.data.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                    <th className="text-left py-3 px-6 font-semibold text-gray-700 dark:text-gray-300">
                      Mô Tả
                    </th>
                    <th className="text-left py-3 px-6 font-semibold text-gray-700 dark:text-gray-300">
                      Danh Mục
                    </th>
                    <th className="text-left py-3 px-6 font-semibold text-gray-700 dark:text-gray-300">
                      Tài Khoản
                    </th>
                    <th className="text-left py-3 px-6 font-semibold text-gray-700 dark:text-gray-300">
                      Ngày
                    </th>
                    <th className="text-right py-3 px-6 font-semibold text-gray-700 dark:text-gray-300">
                      Số Tiền
                    </th>
                    <th className="text-left py-3 px-6 font-semibold text-gray-700 dark:text-gray-300">
                      Trạng Thái
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.data.map((tx: Transaction) => (
                    <tr
                      key={tx.id}
                      className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer"
                    >
                      <td className="py-3 px-6 text-gray-900 dark:text-white font-medium">
                        {tx.description}
                      </td>
                      <td className="py-3 px-6 text-gray-600 dark:text-gray-400">
                        {tx.category?.name || 'Chưa phân loại'}
                      </td>
                      <td className="py-3 px-6 text-gray-600 dark:text-gray-400">
                        {tx.account?.name || '-'}
                      </td>
                      <td className="py-3 px-6 text-gray-600 dark:text-gray-400">
                        {formatDate(tx.date)}
                      </td>
                      <td className={`py-3 px-6 text-right font-semibold ${getDirectionColor(
                        tx.direction
                      )}`}>
                        {tx.direction === 'inflow' ? '+' : '-'}
                        {formatVND(tx.amount)}
                      </td>
                      <td className="py-3 px-6">
                        {getStatusBadge(tx.status)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <p className="text-gray-500 dark:text-gray-400">
                  Không có giao dịch nào
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {transactions && transactions.totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Trang {transactions.page} trong {transactions.totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              disabled={transactions.page === 1}
              onClick={() =>
                setParams({ ...params, page: Math.max(1, transactions.page - 1) })
              }
            >
              Trước
            </Button>
            <Button
              variant="secondary"
              disabled={transactions.page === transactions.totalPages}
              onClick={() =>
                setParams({
                  ...params,
                  page: Math.min(transactions.totalPages, transactions.page + 1),
                })
              }
            >
              Tiếp Theo
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
