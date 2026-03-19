import React, { useState } from 'react'
import { Plus, Users, Receipt, Scale } from 'lucide-react'
import { Button } from '@/components/ui'
import { formatCurrency } from '@/utils/format'
import { cn } from '@/utils/cn'
import {
  useNetBalances,
  useSettlementSummary,
  useSplitBills,
  useSplitGroups,
  useSettleSplitBill,
} from '@/hooks/useSplitBills'
import { SplitBillCard } from './SplitBillCard'
import { BalanceItem } from './BalanceItem'
import { CreateBillModal } from './CreateBillModal'

type Tab = 'bills' | 'balances' | 'groups'

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'bills', label: 'Hóa đơn', icon: <Receipt className="w-4 h-4" /> },
  { id: 'balances', label: 'Số dư', icon: <Scale className="w-4 h-4" /> },
  { id: 'groups', label: 'Nhóm', icon: <Users className="w-4 h-4" /> },
]

export const SplitBillsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('bills')
  const [showCreateModal, setShowCreateModal] = useState(false)

  const { data: summaryData } = useSettlementSummary()
  const { data: billsData, isLoading: billsLoading } = useSplitBills()
  const { data: balancesData, isLoading: balancesLoading } = useNetBalances()
  const { data: groupsData, isLoading: groupsLoading } = useSplitGroups()
  const settleMutation = useSettleSplitBill()

  const bills = billsData?.items ?? []
  const balances = balancesData ?? []
  const groups = groupsData?.items ?? []

  const handleSettle = (billId: string, contactId: string, amount: number) => {
    settleMutation.mutate({ billId, payload: { contact_id: contactId, amount } })
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Chia Hóa Đơn</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Quản lý các hóa đơn chia sẻ với bạn bè
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <Plus className="w-5 h-5 mr-2" />
          Tạo hóa đơn
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Họ nợ bạn</p>
          <p className="mt-2 text-2xl font-bold text-green-600 dark:text-green-400">
            {summaryData ? formatCurrency(summaryData.total_owed_to_me) : '—'}
          </p>
          {summaryData && (
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
              {summaryData.unsettled_bills_count} hóa đơn chưa xong
            </p>
          )}
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Bạn nợ họ</p>
          <p className="mt-2 text-2xl font-bold text-red-600 dark:text-red-400">
            {summaryData ? formatCurrency(summaryData.total_i_owe) : '—'}
          </p>
          {summaryData && (
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
              Vị thế ròng:{' '}
              <span
                className={cn(
                  'font-medium',
                  summaryData.net_position >= 0
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-red-600 dark:text-red-400'
                )}
              >
                {summaryData.net_position >= 0 ? '+' : ''}
                {formatCurrency(summaryData.net_position)}
              </span>
            </p>
          )}
        </div>
      </div>

      {/* Tab navigation */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 gap-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab.id
                ? 'border-primary-600 text-primary-600 dark:text-primary-400 dark:border-primary-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {/* Bills tab */}
        {activeTab === 'bills' && (
          <div className="space-y-3">
            {billsLoading && (
              <div className="flex justify-center py-12">
                <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}

            {!billsLoading && bills.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Receipt className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-3" />
                <p className="text-gray-500 dark:text-gray-400 font-medium">
                  Chưa có hóa đơn nào
                </p>
                <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                  Bấm "Tạo hóa đơn" để bắt đầu
                </p>
              </div>
            )}

            {bills.map((bill) => (
              <SplitBillCard key={bill.id} bill={bill} onSettle={handleSettle} />
            ))}
          </div>
        )}

        {/* Balances tab */}
        {activeTab === 'balances' && (
          <div className="space-y-3">
            {balancesLoading && (
              <div className="flex justify-center py-12">
                <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}

            {!balancesLoading && balances.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Scale className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-3" />
                <p className="text-gray-500 dark:text-gray-400 font-medium">
                  Không có số dư nào
                </p>
                <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                  Tạo hóa đơn để bắt đầu theo dõi
                </p>
              </div>
            )}

            {balances.map((balance) => (
              <BalanceItem key={balance.contact_id} balance={balance} />
            ))}
          </div>
        )}

        {/* Groups tab */}
        {activeTab === 'groups' && (
          <div className="space-y-3">
            {groupsLoading && (
              <div className="flex justify-center py-12">
                <div className="w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}

            {!groupsLoading && groups.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Users className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-3" />
                <p className="text-gray-500 dark:text-gray-400 font-medium">
                  Chưa có nhóm nào
                </p>
                <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                  Nhóm sẽ được tạo tự động khi bạn tạo hóa đơn
                </p>
              </div>
            )}

            {groups.map((group) => (
              <div
                key={group.id}
                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200
                  dark:border-gray-700 shadow-sm px-4 py-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center flex-shrink-0">
                    <Users className="w-4 h-4 text-primary-700 dark:text-primary-300" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {group.name}
                    </p>
                    {group.description && (
                      <p className="text-xs text-gray-400 dark:text-gray-500 truncate">
                        {group.description}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex-shrink-0 text-right ml-4">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {formatCurrency(group.total_amount)}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    {group.member_count} thành viên
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create bill modal */}
      {showCreateModal && (
        <CreateBillModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  )
}
