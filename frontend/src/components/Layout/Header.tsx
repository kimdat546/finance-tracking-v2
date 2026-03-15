import React, { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import {
  Bell,
  RefreshCw,
  ChevronDown,
  LogOut,
} from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { formatRelativeTime } from '@/utils/format'
import { cn } from '@/utils/cn'

const pageNames: Record<string, string> = {
  '/': 'Bảng điều khiển',
  '/transactions': 'Giao dịch',
  '/split-bills': 'Chia hóa đơn',
  '/budget': 'Ngân sách',
  '/goals': 'Mục tiêu',
  '/debts': 'Nợ',
  '/subscriptions': 'Đăng ký',
  '/reports': 'Báo cáo',
  '/settings': 'Cài đặt',
}

export const Header: React.FC = () => {
  const location = useLocation()
  const { syncStatus, setSyncStatus, lastSyncTime, notificationCount, setNotificationCount } = useAppStore()
  const [userMenuOpen, setUserMenuOpen] = React.useState(false)

  const pageTitle = pageNames[location.pathname] || 'Ứng dụng'

  // Simulate sync status
  useEffect(() => {
    const handleSync = () => {
      setSyncStatus('syncing')
      const timer = setTimeout(() => {
        setSyncStatus('success')
        useAppStore.setState({ lastSyncTime: new Date() })
        setTimeout(() => {
          setSyncStatus('idle')
        }, 2000)
      }, 1500)
      return () => clearTimeout(timer)
    }

    // Auto-sync every 5 minutes
    const interval = setInterval(handleSync, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [setSyncStatus])

  const syncStatusColor = {
    idle: 'text-gray-400',
    syncing: 'text-primary-500 animate-spin',
    success: 'text-success-500',
    error: 'text-danger-500',
  }

  const syncStatusLabel = {
    idle: 'Đã đồng bộ',
    syncing: 'Đang đồng bộ...',
    success: 'Đồng bộ thành công',
    error: 'Lỗi đồng bộ',
  }

  return (
    <header className="h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Left section - Title */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {pageTitle}
        </h1>
      </div>

      {/* Right section - Controls */}
      <div className="flex items-center gap-4">
        {/* Sync Status */}
        <div className="flex items-center gap-2 text-sm">
          <RefreshCw
            className={cn('w-4 h-4', syncStatusColor[syncStatus])}
          />
          <span className="text-gray-600 dark:text-gray-400">
            {syncStatusLabel[syncStatus]}
          </span>
          {lastSyncTime && syncStatus === 'idle' && (
            <span className="text-xs text-gray-500 dark:text-gray-500 ml-1">
              ({formatRelativeTime(lastSyncTime)})
            </span>
          )}
        </div>

        {/* Notification Bell */}
        <button className="relative p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
          <Bell className="w-5 h-5" />
          {notificationCount > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 bg-danger-500 rounded-full" />
          )}
        </button>

        {/* User Menu */}
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="flex items-center gap-2 px-3 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
              U
            </div>
            <span className="text-sm font-medium">Người dùng</span>
            <ChevronDown className={cn(
              'w-4 h-4 transition-transform',
              userMenuOpen && 'rotate-180'
            )} />
          </button>

          {/* Dropdown Menu */}
          {userMenuOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50">
              <button className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700">
                <LogOut className="w-4 h-4" />
                Đăng xuất
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
