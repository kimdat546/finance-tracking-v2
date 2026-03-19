import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Plus,
  RefreshCw,
  X,
  CheckCircle,
  AlertTriangle,
  XCircle,
} from 'lucide-react'
import { Button, Badge, Card, CardContent } from '@/components/ui'
import { cn } from '@/utils/cn'
import { formatRelativeTime } from '@/utils/format'
import {
  useParsers,
  useDynamicParsers,
  useToggleDynamicParser,
  useParserAlerts,
  useAcknowledgeAlert,
  useParserMetrics,
} from '@/hooks/useParsers'
import { ParserCard } from './components/ParserCard'
import { ParserMetricsChart } from './components/ParserMetricsChart'
import { ParserTester } from './components/ParserTester'
import type { ParserInfo, DynamicParserSpec, ParserAlert } from '@/types/parser'

type Tab = 'builtin' | 'custom' | 'alerts'

// Detail slide-over panel
interface DetailPanelProps {
  parserName: string
  onClose: () => void
}

const DetailPanel: React.FC<DetailPanelProps> = ({ parserName, onClose }) => {
  const { data: metrics, isLoading } = useParserMetrics(parserName)
  const [activeSection, setActiveSection] = useState<'chart' | 'test'>('chart')

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div
        className="flex-1 bg-black/40"
        onClick={onClose}
      />
      {/* Panel */}
      <div className="w-full max-w-lg bg-white dark:bg-gray-900 shadow-xl flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">{parserName}</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Chi tiết parser</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex gap-0 border-b border-gray-200 dark:border-gray-700 px-5">
          <button
            onClick={() => setActiveSection('chart')}
            className={cn(
              'py-2.5 px-1 mr-4 text-sm font-medium border-b-2 transition-colors',
              activeSection === 'chart'
                ? 'border-primary-600 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            )}
          >
            Biểu đồ (30 ngày)
          </button>
          <button
            onClick={() => setActiveSection('test')}
            className={cn(
              'py-2.5 px-1 text-sm font-medium border-b-2 transition-colors',
              activeSection === 'test'
                ? 'border-primary-600 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            )}
          >
            Kiểm tra
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {activeSection === 'chart' && (
            <ParserMetricsChart metrics={metrics ?? []} isLoading={isLoading} />
          )}
          {activeSection === 'test' && (
            <ParserTester spec={{ name: parserName }} />
          )}
        </div>
      </div>
    </div>
  )
}

// Alert card
interface AlertCardProps {
  alert: ParserAlert
  onAcknowledge: (id: string) => void
  isAcknowledging: boolean
}

const AlertCard: React.FC<AlertCardProps> = ({ alert, onAcknowledge, isAcknowledging }) => {
  const statusIcon = {
    healthy: <CheckCircle className="w-4 h-4 text-green-500" />,
    degraded: <AlertTriangle className="w-4 h-4 text-yellow-500" />,
    failed: <XCircle className="w-4 h-4 text-red-500" />,
  }[alert.status]

  return (
    <div
      className={cn(
        'p-4 rounded-lg border',
        alert.is_acknowledged
          ? 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700 opacity-60'
          : alert.status === 'failed'
          ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
          : 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">{statusIcon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="font-medium text-sm text-gray-900 dark:text-white">
              {alert.parser_name}
            </span>
            {alert.is_acknowledged && (
              <Badge variant="default" size="sm">Đã xác nhận</Badge>
            )}
          </div>
          <p className="text-sm text-gray-700 dark:text-gray-300">{alert.message}</p>
          <div className="flex gap-3 mt-1 text-xs text-gray-500 dark:text-gray-400">
            <span>Lỗi: {alert.error_count_24h}</span>
            <span>Thành công: {alert.success_count_24h}</span>
            <span>{formatRelativeTime(alert.created_at)}</span>
          </div>
        </div>
        {!alert.is_acknowledged && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onAcknowledge(alert.id)}
            isLoading={isAcknowledging}
          >
            Xác nhận
          </Button>
        )}
      </div>
    </div>
  )
}

export const EmailParsersPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('builtin')
  const [detailParser, setDetailParser] = useState<string | null>(null)
  const [testParser, setTestParser] = useState<string | null>(null)

  const { data: dashboard, isLoading: dashLoading, refetch: refetchDashboard } = useParsers()
  const { data: dynamicParsers, isLoading: dynLoading, refetch: refetchDynamic } = useDynamicParsers()
  const { data: alerts, isLoading: alertsLoading } = useParserAlerts()

  const toggleMutation = useToggleDynamicParser()
  const acknowledgeMutation = useAcknowledgeAlert()

  const builtinParsers: ParserInfo[] = dashboard?.parsers ?? []
  const customParsers: ParserInfo[] = (dynamicParsers ?? []).map((dp: DynamicParserSpec) => ({
    name: dp.name,
    description: dp.description,
    version: dp.version,
    enabled: dp.enabled,
    priority: dp.priority,
    is_builtin: false,
    status: dp.enabled ? 'unknown' : 'disabled',
  } as ParserInfo))

  const unacknowledgedCount = (alerts ?? []).filter((a: ParserAlert) => !a.is_acknowledged).length

  const handleToggleCustom = (name: string, enabled: boolean) => {
    const dp = (dynamicParsers ?? []).find((d: DynamicParserSpec) => d.name === name)
    if (dp) {
      toggleMutation.mutate({ id: dp.id, enabled })
    }
  }

  const isLoading = activeTab === 'builtin' ? dashLoading : activeTab === 'custom' ? dynLoading : alertsLoading

  const TabButton: React.FC<{
    id: Tab
    label: string
    badge?: number
  }> = ({ id, label, badge }) => (
    <button
      onClick={() => setActiveTab(id)}
      className={cn(
        'flex items-center gap-1.5 px-4 py-2.5 font-medium text-sm border-b-2 transition-colors whitespace-nowrap',
        activeTab === id
          ? 'border-primary-600 text-primary-600 dark:text-primary-400'
          : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
      )}
    >
      {label}
      {badge !== undefined && badge > 0 && (
        <Badge variant="danger" size="sm">{badge}</Badge>
      )}
    </button>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Quản lý Email Parser
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
            Tự động phân tích email ngân hàng và trích xuất giao dịch
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              refetchDashboard()
              refetchDynamic()
            }}
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Link to="/settings/parser-generator">
            <Button variant="primary" size="sm">
              <Plus className="w-4 h-4 mr-1.5" />
              Tạo Parser
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats summary */}
      {dashboard && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Tổng parser', value: dashboard.total, color: 'text-gray-900 dark:text-white' },
            { label: 'Hoạt động', value: dashboard.healthy, color: 'text-green-600 dark:text-green-400' },
            { label: 'Cảnh báo', value: dashboard.degraded, color: 'text-yellow-600 dark:text-yellow-400' },
            { label: 'Lỗi', value: dashboard.failed, color: 'text-red-600 dark:text-red-400' },
          ].map((stat) => (
            <Card key={stat.label} className="p-3">
              <CardContent className="p-0">
                <p className="text-xs text-gray-500 dark:text-gray-400">{stat.label}</p>
                <p className={cn('text-2xl font-bold mt-0.5', stat.color)}>{stat.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-0 border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
        <TabButton id="builtin" label="Parsers có sẵn" />
        <TabButton id="custom" label="Custom Parsers" />
        <TabButton id="alerts" label="Cảnh báo" badge={unacknowledgedCount} />
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <span className="inline-block w-8 h-8 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Built-in parsers tab */}
          {activeTab === 'builtin' && (
            <div className="space-y-3">
              {builtinParsers.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-12 gap-2">
                    <p className="text-gray-500 dark:text-gray-400">
                      Không có parser tích hợp nào
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                      Kiểm tra kết nối đến API server
                    </p>
                  </CardContent>
                </Card>
              ) : (
                builtinParsers.map((parser) => (
                  <ParserCard
                    key={parser.name}
                    parser={parser}
                    onViewDetails={() => setDetailParser(parser.name)}
                    onTest={() => setTestParser(parser.name)}
                    isCustom={false}
                  />
                ))
              )}
            </div>
          )}

          {/* Custom parsers tab */}
          {activeTab === 'custom' && (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {customParsers.length} custom parser{customParsers.length !== 1 ? 's' : ''}
                </p>
                <Link to="/settings/parser-generator">
                  <Button variant="primary" size="sm">
                    <Plus className="w-4 h-4 mr-1" />
                    Tạo mới
                  </Button>
                </Link>
              </div>
              {customParsers.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
                    <p className="text-gray-500 dark:text-gray-400">
                      Chưa có custom parser nào
                    </p>
                    <Link to="/settings/parser-generator">
                      <Button variant="primary" size="sm">
                        <Plus className="w-4 h-4 mr-1.5" />
                        Tạo Parser đầu tiên
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              ) : (
                customParsers.map((parser) => (
                  <ParserCard
                    key={parser.name}
                    parser={parser}
                    onToggle={handleToggleCustom}
                    onViewDetails={() => setDetailParser(parser.name)}
                    onTest={() => setTestParser(parser.name)}
                    isCustom
                  />
                ))
              )}
            </div>
          )}

          {/* Alerts tab */}
          {activeTab === 'alerts' && (
            <div className="space-y-3">
              {(alerts ?? []).length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-12 gap-2">
                    <CheckCircle className="w-8 h-8 text-green-500" />
                    <p className="text-gray-500 dark:text-gray-400">
                      Không có cảnh báo nào
                    </p>
                  </CardContent>
                </Card>
              ) : (
                (alerts as ParserAlert[]).map((alert) => (
                  <AlertCard
                    key={alert.id}
                    alert={alert}
                    onAcknowledge={(id) => acknowledgeMutation.mutate(id)}
                    isAcknowledging={acknowledgeMutation.isPending}
                  />
                ))
              )}
            </div>
          )}
        </>
      )}

      {/* Detail slide-over */}
      {detailParser && (
        <DetailPanel parserName={detailParser} onClose={() => setDetailParser(null)} />
      )}

      {/* Test modal */}
      {testParser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" onClick={() => setTestParser(null)} />
          <div className="relative bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-xl max-h-screen overflow-y-auto">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="font-semibold text-gray-900 dark:text-white">
                Kiểm tra: {testParser}
              </h3>
              <button
                onClick={() => setTestParser(null)}
                className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-5">
              <ParserTester spec={{ name: testParser }} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
