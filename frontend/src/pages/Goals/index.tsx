import React, { useState } from 'react'
import { Plus, Target } from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
} from '@/components/ui'
import {
  useGoals,
  useGoalSummary,
  useCreateGoal,
  useAddGoalContribution,
} from '@/hooks/usePlanning'
import { formatVND, formatDate } from '@/utils/format'
import type { GoalCreateRequest } from '@/types/planning'

// ---------------------------------------------------------------------------
// Progress bar helper
// ---------------------------------------------------------------------------

function ProgressBar({ pct }: { pct: number }) {
  const clamped = Math.min(pct, 100)
  const color =
    clamped >= 100 ? 'bg-green-500' : clamped >= 50 ? 'bg-blue-500' : 'bg-primary-500'
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
// Days remaining helper
// ---------------------------------------------------------------------------

function daysRemaining(targetDate: string): number {
  const target = new Date(targetDate)
  const today = new Date()
  const diff = Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
  return diff
}

// ---------------------------------------------------------------------------
// Create Goal Modal
// ---------------------------------------------------------------------------

interface CreateGoalModalProps {
  onClose: () => void
}

function CreateGoalModal({ onClose }: CreateGoalModalProps) {
  const createGoal = useCreateGoal()
  const [form, setForm] = useState<GoalCreateRequest>({
    name: '',
    target_amount: 0,
    start_date: new Date().toISOString().slice(0, 10),
    target_date: '',
    description: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name || form.target_amount <= 0 || !form.target_date) return
    await createGoal.mutateAsync(form)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Thêm mục tiêu
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tên mục tiêu
            </label>
            <input
              type="text"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="VD: Mua xe máy, Du lịch..."
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Mô tả (tuỳ chọn)
            </label>
            <input
              type="text"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Mô tả ngắn về mục tiêu"
              value={form.description ?? ''}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Số tiền mục tiêu (VND)
            </label>
            <input
              type="number"
              min={1}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="30000000"
              value={form.target_amount || ''}
              onChange={(e) => setForm({ ...form, target_amount: Number(e.target.value) })}
              required
            />
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
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Ngày mục tiêu
            </label>
            <input
              type="date"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              value={form.target_date}
              onChange={(e) => setForm({ ...form, target_date: e.target.value })}
              required
            />
          </div>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="secondary" className="flex-1" onClick={onClose}>
              Hủy
            </Button>
            <Button
              type="submit"
              variant="primary"
              className="flex-1"
              isLoading={createGoal.isPending}
            >
              Tạo mục tiêu
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Contribute Modal
// ---------------------------------------------------------------------------

interface ContributeModalProps {
  goalId: string
  goalName: string
  onClose: () => void
}

function ContributeModal({ goalId, goalName, onClose }: ContributeModalProps) {
  const addContribution = useAddGoalContribution()
  const [amount, setAmount] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const num = Number(amount)
    if (num <= 0) return
    await addContribution.mutateAsync({ goalId, amount: num })
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-sm mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
          Góp tiền
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{goalName}</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Số tiền góp (VND)
            </label>
            <input
              type="number"
              min={1}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="500000"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="flex gap-3">
            <Button type="button" variant="secondary" className="flex-1" onClick={onClose}>
              Hủy
            </Button>
            <Button
              type="submit"
              variant="primary"
              className="flex-1"
              isLoading={addContribution.isPending}
            >
              Xác nhận
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

export const GoalsPage: React.FC = () => {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [contributeGoalId, setContributeGoalId] = useState<string | null>(null)
  const [contributeGoalName, setContributeGoalName] = useState('')

  const { data: goalsData, isLoading } = useGoals()
  const { data: summary } = useGoalSummary()

  const goals = goalsData?.items ?? []

  const statusLabel: Record<string, string> = {
    active: 'Đang thực hiện',
    completed: 'Hoàn thành',
    paused: 'Tạm dừng',
    abandoned: 'Đã huỷ',
  }

  const statusVariant = (status: string): 'success' | 'info' | 'warning' | 'default' => {
    if (status === 'completed') return 'success'
    if (status === 'active') return 'info'
    if (status === 'paused') return 'warning'
    return 'default'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Mục Tiêu Tài Chính
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Lập mục tiêu tiết kiệm và theo dõi tiến độ
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <Plus className="w-5 h-5 mr-2" />
          Thêm mục tiêu
        </Button>
      </div>

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Tổng mục tiêu</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {summary.total_goals}
              </p>
              <p className="text-xs text-gray-400 mt-1">{summary.active_goals} đang thực hiện</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Đã tiết kiệm</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">
                {formatVND(summary.total_saved)}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {summary.completion_percentage.toFixed(1)}% tổng mục tiêu
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Tổng cần đạt</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {formatVND(summary.total_target)}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {summary.completed_goals} đã hoàn thành
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Goals list */}
      {isLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center h-32">
            <p className="text-gray-500 dark:text-gray-400 text-sm">Đang tải...</p>
          </CardContent>
        </Card>
      ) : goals.length === 0 ? (
        <Card>
          <CardContent className="flex items-center justify-center h-64">
            <div className="text-center">
              <Target className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Chưa có mục tiêu nào
              </h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                Tạo mục tiêu tài chính để theo dõi tiến độ tiết kiệm
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {goals.map((goal) => {
            const days = daysRemaining(goal.target_date)
            const pct = goal.percentage_complete

            return (
              <Card key={goal.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base">{goal.name}</CardTitle>
                      {goal.description && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          {goal.description}
                        </p>
                      )}
                    </div>
                    <Badge variant={statusVariant(goal.status)} size="sm">
                      {statusLabel[goal.status] ?? goal.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {/* Progress */}
                  <ProgressBar pct={pct} />
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {formatVND(goal.current_amount)}
                      </span>{' '}
                      / {formatVND(goal.target_amount)}
                    </span>
                    <span className="font-semibold text-primary-600 dark:text-primary-400">
                      {pct.toFixed(1)}%
                    </span>
                  </div>

                  {/* Metadata */}
                  <div className="flex justify-between text-xs text-gray-400 dark:text-gray-500">
                    <span>Đến: {formatDate(goal.target_date)}</span>
                    <span>
                      {days > 0
                        ? `Còn ${days} ngày`
                        : days === 0
                        ? 'Hôm nay'
                        : 'Đã qua hạn'}
                    </span>
                  </div>

                  {/* Contribute button */}
                  {goal.status === 'active' && (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full mt-2"
                      onClick={() => {
                        setContributeGoalId(goal.id)
                        setContributeGoalName(goal.name)
                      }}
                    >
                      + Góp tiền
                    </Button>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {showCreateModal && <CreateGoalModal onClose={() => setShowCreateModal(false)} />}
      {contributeGoalId && (
        <ContributeModal
          goalId={contributeGoalId}
          goalName={contributeGoalName}
          onClose={() => setContributeGoalId(null)}
        />
      )}
    </div>
  )
}
