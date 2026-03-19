import React, { useState } from 'react'
import { ChevronDown, ChevronUp, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { cn } from '@/utils/cn'
import { Badge } from '@/components/ui'
import { formatCurrency, formatDate } from '@/utils/format'
import type { SplitBill } from '@/types/social'

interface SplitBillCardProps {
  bill: SplitBill
  onSettle?: (billId: string, contactId: string, amount: number) => void
}

const STATUS_LABELS: Record<SplitBill['status'], string> = {
  pending: 'Đang chờ',
  partial: 'Một phần',
  settled: 'Đã xong',
}

const STATUS_VARIANTS: Record<SplitBill['status'], 'warning' | 'info' | 'success'> = {
  pending: 'warning',
  partial: 'info',
  settled: 'success',
}

const StatusIcon: React.FC<{ status: SplitBill['status'] }> = ({ status }) => {
  if (status === 'settled') return <CheckCircle className="w-4 h-4 text-green-500" />
  if (status === 'partial') return <AlertCircle className="w-4 h-4 text-blue-500" />
  return <Clock className="w-4 h-4 text-yellow-500" />
}

export const SplitBillCard: React.FC<SplitBillCardProps> = ({ bill, onSettle }) => {
  const [expanded, setExpanded] = useState(false)

  const settledCount = bill.participants.filter((p) => p.is_settled).length
  const totalCount = bill.participants.length

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
      {/* Card header */}
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full text-left px-4 py-4 flex items-start gap-3 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
      >
        <StatusIcon status={bill.status} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium text-gray-900 dark:text-white truncate">
              {bill.title}
            </span>
            <Badge variant={STATUS_VARIANTS[bill.status]} size="sm">
              {STATUS_LABELS[bill.status]}
            </Badge>
          </div>

          <div className="flex items-center gap-3 mt-1 text-sm text-gray-500 dark:text-gray-400">
            <span>{formatCurrency(bill.total_amount)}</span>
            <span>•</span>
            <span>
              {settledCount}/{totalCount} đã thanh toán
            </span>
            <span>•</span>
            <span>{formatDate(bill.created_at)}</span>
          </div>

          {bill.notes && (
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500 truncate">{bill.notes}</p>
          )}
        </div>

        <span className="ml-2 text-gray-400 dark:text-gray-500 flex-shrink-0">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </span>
      </button>

      {/* Participants panel */}
      {expanded && (
        <div className="border-t border-gray-100 dark:border-gray-700 px-4 py-3 space-y-2">
          {bill.participants.length === 0 ? (
            <p className="text-sm text-gray-400">Không có người tham gia</p>
          ) : (
            bill.participants.map((participant) => (
              <div
                key={participant.contact_id}
                className="flex items-center justify-between gap-2 py-1"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div
                    className={cn(
                      'w-2 h-2 rounded-full flex-shrink-0',
                      participant.is_settled
                        ? 'bg-green-500'
                        : 'bg-yellow-400'
                    )}
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300 truncate">
                    {participant.contact_name}
                  </span>
                </div>

                <div className="flex items-center gap-3 flex-shrink-0">
                  <span
                    className={cn(
                      'text-sm font-medium',
                      participant.is_settled
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-gray-800 dark:text-gray-200'
                    )}
                  >
                    {formatCurrency(participant.share_amount)}
                  </span>

                  {!participant.is_settled && onSettle && (
                    <button
                      type="button"
                      onClick={() =>
                        onSettle(bill.id, participant.contact_id, participant.share_amount)
                      }
                      className="text-xs px-2 py-1 rounded-md bg-primary-100 text-primary-700
                        hover:bg-primary-200 dark:bg-primary-900 dark:text-primary-300
                        dark:hover:bg-primary-800 transition-colors"
                    >
                      Thanh toán
                    </button>
                  )}

                  {participant.is_settled && (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
