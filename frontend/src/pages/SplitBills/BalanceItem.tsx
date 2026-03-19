import React from 'react'
import { cn } from '@/utils/cn'
import { formatCurrency } from '@/utils/format'
import type { NetBalance } from '@/types/social'

interface BalanceItemProps {
  balance: NetBalance
}

export const BalanceItem: React.FC<BalanceItemProps> = ({ balance }) => {
  const isPositive = balance.net > 0
  const isNeutral = balance.net === 0

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
      {/* Avatar + name */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-9 h-9 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center flex-shrink-0">
          <span className="text-sm font-semibold text-primary-700 dark:text-primary-300">
            {balance.contact_name.charAt(0).toUpperCase()}
          </span>
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
            {balance.contact_name}
          </p>
          {!isNeutral && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {isPositive
                ? `Họ nợ bạn ${formatCurrency(balance.they_owe_me)}`
                : `Bạn nợ họ ${formatCurrency(balance.i_owe_them)}`}
            </p>
          )}
          {isNeutral && (
            <p className="text-xs text-gray-400 dark:text-gray-500">Đã cân bằng</p>
          )}
        </div>
      </div>

      {/* Net amount */}
      <div className="flex-shrink-0 text-right">
        <span
          className={cn(
            'text-sm font-semibold',
            isNeutral && 'text-gray-500 dark:text-gray-400',
            isPositive && 'text-green-600 dark:text-green-400',
            !isPositive && !isNeutral && 'text-red-600 dark:text-red-400'
          )}
        >
          {isPositive && '+'}
          {formatCurrency(Math.abs(balance.net))}
        </span>
        <p className="text-xs text-gray-400 dark:text-gray-500">
          {isPositive ? 'Được nhận' : isNeutral ? 'Cân bằng' : 'Phải trả'}
        </p>
      </div>
    </div>
  )
}
