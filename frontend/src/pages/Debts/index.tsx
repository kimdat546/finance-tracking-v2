import React, { useState } from 'react'
import { Plus, CreditCard } from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
} from '@/components/ui'
import {
  useDebts,
  useDebtSummary,
  useCreateDebt,
  useRecordDebtPayment,
} from '@/hooks/usePlanning'
import { formatVND, formatDate } from '@/utils/format'
import type { DebtCreateRequest, DebtPaymentRequest } from '@/types/planning'

// ---------------------------------------------------------------------------
// Progress bar helper
// ---------------------------------------------------------------------------

function ProgressBar({ pct }: { pct: number }) {
  const clamped = Math.min(pct, 100)
  return (
    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
      <div
        className="h-2 rounded-full bg-primary-500 transition-all duration-300"
        style={{ width: `${clamped}%` }}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Create Debt Modal
// ---------------------------------------------------------------------------

interface CreateDebtModalProps {
  onClose: () => void
}

function CreateDebtModal({ onClose }: CreateDebtModalProps) {
  const createDebt = useCreateDebt()
  const [form, setForm] = useState<DebtCreateRequest>({
    name: '',
    creditor: '',
    amount: 0,
    start_date: new Date().toISOString().slice(0, 10),
    debt_type: 'owe',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.creditor || form.amount <= 0) return
    await createDebt.mutateAsync(form)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Thêm khoản nợ
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Loại nợ
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors ${
                  form.debt_type === 'owe'
                    ? 'bg-red-500 text-white border-red-500'
                    : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'
                }`}
                onClick={() => setForm({ ...form, debt_type: 'owe' })}
              >
                Bạn nợ
              </button>
              <button
                type="button"
                className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors ${
                  form.debt_type === 'owed'
                    ? 'bg-green-500 text-white border-green-500'
                    : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'
                }`}
                onClick={() => setForm({ ...form, debt_type: 'owed' })}
              >
                Người nợ bạn
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tên khoản nợ
            </label>
            <input
              type="text"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="VD: Vay mua laptop"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {form.debt_type === 'owe' ? 'Chủ nợ (người bạn nợ)' : 'Con nợ (người nợ bạn)'}
            </label>
            <input
              type="text"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Tên người / tổ chức"
              value={form.creditor}
              onChange={(e) => setForm({ ...form, creditor: e.target.value })}
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
              placeholder="5000000"
              value={form.amount || ''}
              onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })}
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
              Ngày đáo hạn (tuỳ chọn)
            </label>
            <input
              type="date"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              value={form.due_date ?? ''}
              onChange={(e) => setForm({ ...form, due_date: e.target.value })}
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
              isLoading={createDebt.isPending}
            >
              Thêm khoản nợ
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Payment Modal
// ---------------------------------------------------------------------------

interface PaymentModalProps {
  debtId: string
  debtName: string
  onClose: () => void
}

function PaymentModal({ debtId, debtName, onClose }: PaymentModalProps) {
  const recordPayment = useRecordDebtPayment()
  const [form, setForm] = useState<DebtPaymentRequest>({
    amount: 0,
    payment_date: new Date().toISOString().slice(0, 10),
    notes: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.amount <= 0) return
    await recordPayment.mutateAsync({ debtId, data: form })
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-sm mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
          Ghi nhận thanh toán
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{debtName}</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Số tiền (VND)
            </label>
            <input
              type="number"
              min={1}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="500000"
              value={form.amount || ''}
              onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })}
              required
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Ngày thanh toán
            </label>
            <input
              type="date"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              value={form.payment_date}
              onChange={(e) => setForm({ ...form, payment_date: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Ghi chú (tuỳ chọn)
            </label>
            <input
              type="text"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Ghi chú về khoản thanh toán"
              value={form.notes ?? ''}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
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
              isLoading={recordPayment.isPending}
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
// Debt card component
// ---------------------------------------------------------------------------

interface DebtCardProps {
  debt: {
    id: string
    name: string
    creditor?: string
    amount: number
    paid_amount: number
    remaining_amount: number
    due_date?: string
    debt_type: 'owe' | 'owed'
    is_active: boolean
  }
  onPayment: (id: string, name: string) => void
}

function DebtCard({ debt, onPayment }: DebtCardProps) {
  const paidPct =
    debt.amount > 0 ? Math.min((debt.paid_amount / debt.amount) * 100, 100) : 0

  return (
    <Card>
      <CardContent className="space-y-3">
        <div className="flex items-start justify-between">
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-white text-sm">
              {debt.name || debt.creditor}
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {debt.debt_type === 'owe' ? 'Nợ' : 'Cho vay'}: {debt.creditor}
            </p>
          </div>
          {debt.due_date && (
            <span className="text-xs text-gray-400 dark:text-gray-500">
              Hạn: {formatDate(debt.due_date)}
            </span>
          )}
        </div>

        <ProgressBar pct={paidPct} />

        <div className="flex justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">
            Đã trả:{' '}
            <span className="font-medium text-gray-900 dark:text-white">
              {formatVND(debt.paid_amount)}
            </span>
          </span>
          <span className="text-gray-600 dark:text-gray-400">
            Còn:{' '}
            <span className="font-medium text-red-600 dark:text-red-400">
              {formatVND(debt.remaining_amount)}
            </span>
          </span>
        </div>
        <p className="text-xs text-gray-400 dark:text-gray-500 text-right">
          Gốc: {formatVND(debt.amount)}
        </p>

        {debt.is_active && (
          <Button
            variant="secondary"
            size="sm"
            className="w-full"
            onClick={() => onPayment(debt.id, debt.name || debt.creditor || '')}
          >
            Ghi nhận thanh toán
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export const DebtsPage: React.FC = () => {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [paymentDebt, setPaymentDebt] = useState<{ id: string; name: string } | null>(null)

  const { data: allDebtsData, isLoading } = useDebts()
  const { data: summary } = useDebtSummary()

  const allDebts = allDebtsData?.items ?? []
  const owedByMe = allDebts.filter((d) => d.debt_type === 'owe')
  const owedToMe = allDebts.filter((d) => d.debt_type === 'owed')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Quản Lý Nợ</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Theo dõi các khoản nợ và lập kế hoạch thanh toán
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <Plus className="w-5 h-5 mr-2" />
          Thêm Nợ
        </Button>
      </div>

      {/* Net position card */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="border-red-200 dark:border-red-800">
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Bạn đang nợ</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">
                {formatVND(summary.total_owe)}
              </p>
              <p className="text-xs text-gray-400 mt-1">{owedByMe.length} khoản</p>
            </CardContent>
          </Card>
          <Card className="border-green-200 dark:border-green-800">
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Người ta nợ bạn</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">
                {formatVND(summary.total_owed)}
              </p>
              <p className="text-xs text-gray-400 mt-1">{owedToMe.length} khoản</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p className="text-sm text-gray-500 dark:text-gray-400">Vị thế ròng</p>
              <p
                className={`text-2xl font-bold mt-1 ${
                  summary.net_position >= 0
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-red-600 dark:text-red-400'
                }`}
              >
                {summary.net_position >= 0 ? '+' : ''}
                {formatVND(summary.net_position)}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {summary.active_debt_count} khoản đang hoạt động
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {isLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center h-32">
            <p className="text-gray-500 dark:text-gray-400 text-sm">Đang tải...</p>
          </CardContent>
        </Card>
      ) : allDebts.length === 0 ? (
        <Card>
          <CardContent className="flex items-center justify-center h-64">
            <div className="text-center">
              <CreditCard className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Chưa có khoản nợ nào
              </h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                Thêm khoản nợ để quản lý nợ của bạn
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Bạn nợ section */}
          {owedByMe.length > 0 && (
            <div>
              <h3 className="text-base font-semibold text-red-600 dark:text-red-400 mb-3 flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500 inline-block" />
                Bạn nợ ({owedByMe.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {owedByMe.map((debt) => (
                  <DebtCard
                    key={debt.id}
                    debt={debt}
                    onPayment={(id, name) => setPaymentDebt({ id, name })}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Người nợ bạn section */}
          {owedToMe.length > 0 && (
            <div>
              <h3 className="text-base font-semibold text-green-600 dark:text-green-400 mb-3 flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-green-500 inline-block" />
                Người nợ bạn ({owedToMe.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {owedToMe.map((debt) => (
                  <DebtCard
                    key={debt.id}
                    debt={debt}
                    onPayment={(id, name) => setPaymentDebt({ id, name })}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {showCreateModal && <CreateDebtModal onClose={() => setShowCreateModal(false)} />}
      {paymentDebt && (
        <PaymentModal
          debtId={paymentDebt.id}
          debtName={paymentDebt.name}
          onClose={() => setPaymentDebt(null)}
        />
      )}
    </div>
  )
}
