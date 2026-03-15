import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Wallet,
  Users,
  PieChart,
  Target,
  CreditCard,
  Receipt,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
} from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { Badge } from '@/components/ui'
import { cn } from '@/utils/cn'

interface NavItem {
  label: string
  href: string
  icon: React.ReactNode
  badge?: number
  section: 'main' | 'social' | 'planning' | 'analytics' | 'system'
}

const navItems: NavItem[] = [
  // Main
  {
    label: 'Bảng điều khiển',
    href: '/',
    icon: <LayoutDashboard className="w-5 h-5" />,
    section: 'main',
  },
  {
    label: 'Giao dịch',
    href: '/transactions',
    icon: <Wallet className="w-5 h-5" />,
    section: 'main',
    badge: 0,
  },

  // Social
  {
    label: 'Chia hóa đơn',
    href: '/split-bills',
    icon: <Users className="w-5 h-5" />,
    section: 'social',
  },

  // Planning
  {
    label: 'Ngân sách',
    href: '/budget',
    icon: <PieChart className="w-5 h-5" />,
    section: 'planning',
  },
  {
    label: 'Mục tiêu',
    href: '/goals',
    icon: <Target className="w-5 h-5" />,
    section: 'planning',
  },
  {
    label: 'Nợ',
    href: '/debts',
    icon: <CreditCard className="w-5 h-5" />,
    section: 'planning',
  },
  {
    label: 'Đăng ký',
    href: '/subscriptions',
    icon: <Receipt className="w-5 h-5" />,
    section: 'planning',
  },

  // Analytics
  {
    label: 'Báo cáo',
    href: '/reports',
    icon: <BarChart3 className="w-5 h-5" />,
    section: 'analytics',
  },

  // System
  {
    label: 'Cài đặt',
    href: '/settings',
    icon: <Settings className="w-5 h-5" />,
    section: 'system',
  },
]

export const Sidebar: React.FC = () => {
  const location = useLocation()
  const { sidebarOpen, toggleSidebar, pendingReviewCount } = useAppStore()

  const sections = {
    main: navItems.filter((item) => item.section === 'main'),
    social: navItems.filter((item) => item.section === 'social'),
    planning: navItems.filter((item) => item.section === 'planning'),
    analytics: navItems.filter((item) => item.section === 'analytics'),
    system: navItems.filter((item) => item.section === 'system'),
  }

  const NavSection: React.FC<{ title: string; items: NavItem[] }> = ({
    title,
    items,
  }) => (
    <div className="mb-6">
      {sidebarOpen && (
        <h3 className="px-4 mb-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          {title}
        </h3>
      )}
      <nav className="space-y-1">
        {items.map((item) => {
          const isActive = location.pathname === item.href
          const badge =
            item.label === 'Giao dịch' ? pendingReviewCount : item.badge

          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                'flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors duration-200',
                isActive
                  ? 'bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-200'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              )}
              title={!sidebarOpen ? item.label : undefined}
            >
              <span className="flex-shrink-0">{item.icon}</span>
              {sidebarOpen && (
                <>
                  <span className="flex-1 text-sm font-medium">
                    {item.label}
                  </span>
                  {badge !== undefined && badge > 0 && (
                    <Badge variant="danger" size="sm" className="ml-auto">
                      {badge}
                    </Badge>
                  )}
                </>
              )}
            </Link>
          )
        })}
      </nav>
    </div>
  )

  return (
    <aside
      className={cn(
        'h-screen bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-20'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-800">
        {sidebarOpen && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <Wallet className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-lg font-bold text-gray-900 dark:text-white">
              Finances
            </h1>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          aria-label={sidebarOpen ? 'Đóng sidebar' : 'Mở sidebar'}
        >
          {sidebarOpen ? (
            <ChevronLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          )}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto py-6">
        {/* Pending Review Alert */}
        {pendingReviewCount > 0 && sidebarOpen && (
          <div className="mx-4 mb-6 p-3 bg-warning-50 dark:bg-warning-900/30 border border-warning-200 dark:border-warning-800 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-warning-600 dark:text-warning-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-warning-800 dark:text-warning-200">
                  {pendingReviewCount} giao dịch cần xem xét
                </p>
                <Link
                  to="/transactions"
                  className="text-xs text-warning-700 dark:text-warning-300 hover:underline mt-1 inline-block"
                >
                  Xem chi tiết
                </Link>
              </div>
            </div>
          </div>
        )}

        <NavSection title="Chính" items={sections.main} />
        <NavSection title="Xã hội" items={sections.social} />
        <NavSection title="Lập kế hoạch" items={sections.planning} />
        <NavSection title="Phân tích" items={sections.analytics} />
        <NavSection title="Hệ thống" items={sections.system} />
      </div>

      {/* Footer */}
      {sidebarOpen && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
          <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
            v0.1.0
          </div>
        </div>
      )}
    </aside>
  )
}
