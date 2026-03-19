import React, { useState } from 'react'
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  MinusCircle,
  HelpCircle,
  Eye,
  FlaskConical,
} from 'lucide-react'
import { Badge, Button, Card, CardContent } from '@/components/ui'
import { cn } from '@/utils/cn'
import type { ParserInfo } from '@/types/parser'

interface ParserCardProps {
  parser: ParserInfo
  onToggle?: (name: string, enabled: boolean) => void
  onTest?: (name: string) => void
  onViewDetails?: (name: string) => void
  isCustom?: boolean
}

const STATUS_CONFIG: Record<
  ParserInfo['status'],
  {
    label: string
    icon: React.ReactNode
    badgeVariant: 'success' | 'warning' | 'danger' | 'default'
    dotClass: string
  }
> = {
  healthy: {
    label: 'Hoạt động',
    icon: <CheckCircle className="w-4 h-4" />,
    badgeVariant: 'success',
    dotClass: 'bg-green-500',
  },
  degraded: {
    label: 'Cảnh báo',
    icon: <AlertTriangle className="w-4 h-4" />,
    badgeVariant: 'warning',
    dotClass: 'bg-yellow-500',
  },
  failed: {
    label: 'Lỗi',
    icon: <XCircle className="w-4 h-4" />,
    badgeVariant: 'danger',
    dotClass: 'bg-red-500',
  },
  disabled: {
    label: 'Tắt',
    icon: <MinusCircle className="w-4 h-4" />,
    badgeVariant: 'default',
    dotClass: 'bg-gray-400',
  },
  unknown: {
    label: 'Không rõ',
    icon: <HelpCircle className="w-4 h-4" />,
    badgeVariant: 'default',
    dotClass: 'bg-gray-400',
  },
}

export const ParserCard: React.FC<ParserCardProps> = ({
  parser,
  onToggle,
  onTest,
  onViewDetails,
  isCustom = false,
}) => {
  const [toggling, setToggling] = useState(false)
  const config = STATUS_CONFIG[parser.status]

  const handleToggle = async () => {
    if (!onToggle) return
    setToggling(true)
    try {
      onToggle(parser.name, !parser.enabled)
    } finally {
      setToggling(false)
    }
  }

  const successRate =
    parser.success_rate_24h !== undefined ? parser.success_rate_24h : null
  const totalAttempts = parser.total_attempts_24h ?? 0
  const avgTime = parser.avg_time_ms !== undefined ? parser.avg_time_ms : null

  return (
    <Card className="p-4">
      <CardContent className="p-0">
        <div className="flex items-start gap-3">
          {/* Status dot */}
          <div className="flex-shrink-0 mt-1">
            <span className={cn('inline-block w-2.5 h-2.5 rounded-full', config.dotClass)} />
          </div>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            {/* Header row */}
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <h4 className="font-semibold text-sm text-gray-900 dark:text-white truncate">
                {parser.name}
              </h4>
              <Badge variant="default" size="sm">
                v{parser.version}
              </Badge>
              <Badge variant={config.badgeVariant} size="sm">
                {config.label}
              </Badge>
              {parser.is_builtin && (
                <Badge variant="info" size="sm">
                  Tích hợp
                </Badge>
              )}
            </div>

            {/* Description */}
            {parser.description && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 line-clamp-1">
                {parser.description}
              </p>
            )}

            {/* Metrics row */}
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600 dark:text-gray-400">
              <span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {successRate !== null ? `${successRate.toFixed(1)}%` : '—'}
                </span>
                {' '}tỉ lệ thành công (24h)
              </span>
              <span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {totalAttempts}
                </span>
                {' '}lượt thử
              </span>
              {avgTime !== null && (
                <span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {avgTime.toFixed(0)}ms
                  </span>
                  {' '}trung bình
                </span>
              )}
              {parser.supported_senders && (
                <span className="truncate max-w-40" title={parser.supported_senders}>
                  {parser.supported_senders}
                </span>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {onViewDetails && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onViewDetails(parser.name)}
                title="Xem chi tiết"
              >
                <Eye className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">Chi tiết</span>
              </Button>
            )}
            {onTest && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onTest(parser.name)}
                title="Kiểm tra parser"
              >
                <FlaskConical className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">Kiểm tra</span>
              </Button>
            )}
            {isCustom && onToggle && (
              <button
                role="switch"
                aria-checked={parser.enabled}
                onClick={handleToggle}
                disabled={toggling}
                className={cn(
                  'relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 disabled:opacity-50',
                  parser.enabled ? 'bg-primary-600' : 'bg-gray-300 dark:bg-gray-600'
                )}
              >
                <span
                  className={cn(
                    'inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform',
                    parser.enabled ? 'translate-x-[18px]' : 'translate-x-[2px]'
                  )}
                />
              </button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
