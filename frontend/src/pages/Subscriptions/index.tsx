import React, { useState } from 'react'
import { Plus, RefreshCw, Zap } from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
} from '@/components/ui'
import {
  useSubscriptions,
  useSubscriptionSummary,
  useUpcomingRenewals,
  useCreateSubscription,
  useCancelSubscription,
  useDetectSubscriptions,
} from '@/hooks/usePlanning'
import { formatVND, formatDate } from '@/utils/format'
import type { SubscriptionCreateRequest } from '@/types/planning'

// ---------------------------------------------------------------------------
// Create Subscription Modal
// ---------------------------------------------------------------------------

interface CreateSubscriptionModalProps {
  onClose: () => void
}

function CreateSubscriptionModal({ onClose }: CreateSubscriptionModalProps) {
  const createSub = useCreateSubscription()
  const [form, setForm] = useState<SubscriptionCreateRequest>({
    name: '',
    amount: 0,
    billing_cycle: 'monthly',
    start_date: new Date().toISOString().slice(0, 10),
    next_billing_date: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name || form.amount <= 0 || !form.next_billing_date) return
    await createSub.mutateAsync(form)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Thêm đăng ký
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tên dịch vụ
            </label>
            <input
              type="text"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Netflix, Spotify, ..."
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Số tiền (VND)
            </label>
            <input
              type="number"
              min={1}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="180000"
              value={form.amount || ''}
              onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Chu kỳ thanh toán
            </label>
            <select
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              value={form.billing_cycle}
              onChange={(e) =>
                setForm({
                  ...form,
                  billing_cycle: e.target.value as SubscriptionCreateRequest['billing_cycle'],
                })
              }
            >
              <option value="monthly">Hàng tháng</option>
              <option value="yearly">Hàng năm</option>
              <option value="weekly">Hàng tuần</option>
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
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Ngày gia hạn tiếp theo
            </label>
            <input
              type="date"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              value={form.next_billing_date}
              onChange={(e) => setForm({ ...form, next_billing_date: e.target.value })}
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
              isLoading={createSub.isPending}
            >
              Thêm đăng ký
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Detection Results Modal
// ---------------------------------------------------------------------------

interface DetectionModalProps {
  onClose: () => void
}

function DetectionModal({ onClose }: DetectionModalProps) {
  const { data, isFetching, refetch } = useDetectSubscriptions()

  React.useEffect(() => {
    refetch()
  }, [refetch])

  const results = data ?? []

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg mx-4 p-6 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Phát hiện đăng ký
          </h3>
          <button
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-xl"
            onClick={onClose}
          >
            x
          </button>
        </div>
        {isFetching ? (
          <div className="flex-1 flex items-center justify-center py-8">
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              Đang phân tích giao dịch...
            </p>
          </div>
        ) : results.length === 0 ? (
          <div className="flex-1 flex items-center justify-center py-8">
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              Không phát hiện đăng ký định kỳ nào
            </p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto space-y-3">
            {results.map((r, idx) => (
              <div
                key={idx}
                className="border border-gray-200 dark:border-gray-700 rounded-lg p-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white text-sm">{r.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {r.billing_cycle} • {r.transaction_ids.length} giao dịch
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-gray-900 dark:text-white text-sm">
                      {formatVND(r.amount)}
                    </p>
                    <Badge
                      variant={
                        r.confidence >= 0.8
                          ? 'success'
                          : r.confidence >= 0.5
                          ? 'warning'
                          : 'default'
                      }
                      size="sm"
                    >
                      {(r.confidence * 100).toFixed(0)}% chắc chắn
                    </Badge>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="mt-4">
          <Button variant="secondary" className="w-full" onClick={onClose}>
            Đóng
          </Button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export const SubscriptionsPage: React.FC = () => {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showDetectModal, setShowDetectModal] = useState(false)

  const { data: subsData, isLoading } = useSubscriptions()
  const { data: summary } = useSubscriptionSummary()
  const { data: upcomingData } = useUpcomingRenewals(7)
  const cancelSub = useCancelSubscription()

  const subscriptions = subsData?.items ?? []
  const upcomingRenewals = upcomingData?.items ?? []

  const cycleLabel: Record<string, string> = {
    monthly: 'Hàng tháng',
    yearly: 'Hàng năm',
    weekly: 'Hàng tuần',
    daily: 'Hàng ngày',
    quarterly: 'Hàng quý',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Đăng Ký</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Quản lý các khoản đăng ký định kỳ
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowDetectModal(true)}>
            <Zap className="w-4 h-4 mr-2" />
            Phát hiện subscription
          </Button>
          <Button variant="primary" onClick={() => setShowCreateModal(true)}>
            <Plus className="w-5 h-5 mr-2" />
            Thêm đăng ký
          </Button>
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Chi phí hàng tháng</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {formatVND(summary.monthly_cost)}
              </p>
              <p className="text-xs text-gray-400 mt-1">{summary.active_count} đăng ký</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Chi phí hàng năm</p>
              <p className="text-2xl font-bold text-orange-600 dark:text-orange-400 mt-1">
                {formatVND(summary.yearly_cost)}
              </p>
              <p className="text-xs text-gray-400 mt-1">Ước tính cả năm</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Sắp gia hạn</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">
                {summary.upcoming_renewals_count}
              </p>
              <p className="text-xs text-gray-400 mt-1">Trong 7 ngày tới</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Upcoming renewals */}
      {upcomingRenewals.length > 0 && (
        <Card className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-blue-700 dark:text-blue-300 text-base">
              <RefreshCw className="w-4 h-4" />
              Sắp gia hạn ({upcomingRenewals.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {upcomingRenewals.map((sub) => (
                <li
                  key={sub.id}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-blue-700 dark:text-blue-300 font-medium">
                    {sub.name}
                  </span>
                  <div className="flex items-center gap-3">
                    <span className="text-blue-600 dark:text-blue-400">
                      {formatVND(sub.amount)}
                    </span>
                    <span className="text-xs text-blue-500 dark:text-blue-400">
                      {formatDate(sub.next_billing_date)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* All subscriptions */}
      {isLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center h-32">
            <p className="text-gray-500 dark:text-gray-400 text-sm">Đang tải...</p>
          </CardContent>
        </Card>
      ) : subscriptions.length === 0 ? (
        <Card>
          <CardContent className="flex items-center justify-center h-64">
            <div className="text-center">
              <RefreshCw className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Chưa có đăng ký nào
              </h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                Thêm đăng ký để theo dõi các khoản phí định kỳ
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {subscriptions.map((sub) => {
            const isUpcoming = upcomingRenewals.some((u) => u.id === sub.id)

            return (
              <Card key={sub.id}>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-gray-900 dark:text-white text-sm">
                          {sub.name}
                        </h4>
                        {isUpcoming && (
                          <Badge variant="warning" size="sm">
                            Sắp gia hạn
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {cycleLabel[sub.billing_cycle] ?? sub.billing_cycle} •{' '}
                        Gia hạn: {formatDate(sub.next_billing_date)}
                      </p>
                    </div>
                    <div className="text-right ml-4">
                      <p className="font-semibold text-gray-900 dark:text-white text-sm">
                        {formatVND(sub.amount)}
                      </p>
                      <p className="text-xs text-gray-400 dark:text-gray-500">
                        {formatVND(sub.annual_cost)}/năm
                      </p>
                    </div>
                  </div>
                  <div className="flex justify-end mt-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950"
                      onClick={() => cancelSub.mutate(sub.id)}
                    >
                      Huỷ đăng ký
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {showCreateModal && <CreateSubscriptionModal onClose={() => setShowCreateModal(false)} />}
      {showDetectModal && <DetectionModal onClose={() => setShowDetectModal(false)} />}
    </div>
  )
}
