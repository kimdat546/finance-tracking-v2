import React, { useState } from 'react'
import { Plus, AlertTriangle, TrendingUp } from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
} from '@/components/ui'
import {
  useBudgets,
  useBudgetAlerts,
  useBudgetSummary,
  useCreateBudget,
} from '@/hooks/usePlanning'
import { formatVND } from '@/utils/format'
import type { BudgetCreateRequest } from '@/types/planning'

// ---------------------------------------------------------------------------
// Progress bar helper
// ---------------------------------------------------------------------------

function ProgressBar({ pct }: { pct: number }) {
  const clamped = Math.min(pct, 100)
  const color =
    clamped > 80 ? 'bg-red-500' : clamped >= 50 ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all duration-300 ${color}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Create Budget Modal
// ---------------------------------------------------------------------------

interface CreateBudgetModalProps {
  onClose: () => void
}

function CreateBudgetModal({ onClose }: CreateBudgetModalProps) {
  const createBudget = useCreateBudget()
  const [form, setForm] = useState<BudgetCreateRequest>({
    category_id: '',
    name: '',
    amount: 0,
    period: 'monthly',
    start_date: new Date().toISOString().slice(0, 10),
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.category_id || !form.name || form.amount <= 0) return
    await createBudget.mutateAsync(form)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Thêm ngân sách
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tên ngân sách
            </label>
            <input
              type="text"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="VD: Ăn uống tháng 3"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              ID danh mục
            </label>
            <input
              type="text"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="category-id"
              value={form.category_id}
              onChange={(e) => setForm({ ...form, category_id: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Hạn mức (VND)
            </label>
            <input
              type="number"
              min={1}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="3000000"
              value={form.amount || ''}
              onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Chu kỳ
            </label>
            <select
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              value={form.period}
              onChange={(e) =>
                setForm({ ...form, period: e.target.value as BudgetCreateRequest['period'] })
              }
            >
              <option value="monthly">Hàng tháng</option>
              <option value="weekly">Hàng tuần</option>
              <option value="yearly">Hàng năm</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Ngày bắt đầu
            </label>
            <input
              type="date"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              required
            />
          </div>
          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={onClose}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              variant="primary"
              className="flex-1"
              isLoading={createBudget.isPending}
            >
              Tạo ngân sách
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export const BudgetPage: React.FC = () => {
  const [showModal, setShowModal] = useState(false)
  const { data: budgetsData, isLoading } = useBudgets()
  const { data: alertsData } = useBudgetAlerts()
  const { data: summary } = useBudgetSummary()

  const budgets = budgetsData?.items ?? []
  const alerts = alertsData ?? []

  const periodLabel: Record<string, string> = {
    monthly: 'Hàng tháng',
    weekly: 'Hàng tuần',
    yearly: 'Hàng năm',
    daily: 'Hàng ngày',
    quarterly: 'Hàng quý',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Ngân Sách</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Đặt và theo dõi ngân sách cho mỗi danh mục
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowModal(true)}>
          <Plus className="w-5 h-5 mr-2" />
          Thêm ngân sách
        </Button>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Tổng ngân sách</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {formatVND(summary.total_budgeted)}
              </p>
              <p className="text-xs text-gray-400 mt-1">{summary.budget_count} ngân sách</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Tổng chi tiêu</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">
                {formatVND(summary.total_spent)}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {summary.over_limit_count} vượt hạn mức
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Còn lại</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">
                {formatVND(summary.total_remaining)}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {summary.on_track_count} đúng kế hoạch
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Alerts */}
      {alerts.length > 0 && (
        <Card className="border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-950">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-orange-700 dark:text-orange-300 text-base">
              <AlertTriangle className="w-5 h-5" />
              Cảnh báo ngân sách ({alerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {alerts.map((alert) => (
                <li
                  key={alert.budget_id}
                  className="text-sm text-orange-700 dark:text-orange-300 flex items-center gap-2"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-orange-500 flex-shrink-0" />
                  {alert.message}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Budget list */}
      {isLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center h-32">
            <div className="text-gray-500 dark:text-gray-400 text-sm">Đang tải...</div>
          </CardContent>
        </Card>
      ) : budgets.length === 0 ? (
        <Card>
          <CardContent className="flex items-center justify-center h-64">
            <div className="text-center">
              <TrendingUp className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Chưa có ngân sách nào
              </h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                Tạo ngân sách để quản lý chi tiêu của bạn
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {budgets.map((budget) => {
            const pct = budget.percentage_used
            const statusColor =
              pct > 100
                ? 'danger'
                : pct > 80
                ? 'warning'
                : 'success'

            return (
              <Card key={budget.id}>
                <CardContent>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h4 className="font-semibold text-gray-900 dark:text-white">
                        {budget.name}
                      </h4>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {budget.category_name ?? budget.category_id} •{' '}
                        {periodLabel[budget.period] ?? budget.period}
                      </p>
                    </div>
                    <Badge variant={statusColor} size="sm">
                      {pct.toFixed(1)}%
                    </Badge>
                  </div>

                  <ProgressBar pct={pct} />

                  <div className="flex justify-between mt-2 text-sm">
                    <span className="text-gray-600 dark:text-gray-400">
                      Đã chi: <span className="font-medium text-gray-900 dark:text-white">{formatVND(budget.spent_amount)}</span>
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">
                      Còn lại:{' '}
                      <span
                        className={`font-medium ${
                          budget.remaining <= 0
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-green-600 dark:text-green-400'
                        }`}
                      >
                        {formatVND(budget.remaining)}
                      </span>
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 text-right">
                    Hạn mức: {formatVND(budget.amount)}
                  </p>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Create modal */}
      {showModal && <CreateBudgetModal onClose={() => setShowModal(false)} />}
    </div>
  )
}
