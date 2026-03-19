import React, { useState } from 'react'
import { CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui'
import { cn } from '@/utils/cn'
import { useTestParser } from '@/hooks/useParsers'
import type { ParserTestResult } from '@/types/parser'

interface ParserTesterProps {
  spec: unknown
  className?: string
  initialEmailBody?: string
  initialSender?: string
  initialSubject?: string
}

export const ParserTester: React.FC<ParserTesterProps> = ({
  spec,
  className,
  initialEmailBody = '',
  initialSender = '',
  initialSubject = '',
}) => {
  const [emailBody, setEmailBody] = useState(initialEmailBody)
  const [sender, setSender] = useState(initialSender)
  const [subject, setSubject] = useState(initialSubject)

  const testMutation = useTestParser()

  const handleTest = () => {
    if (!emailBody.trim()) return
    testMutation.mutate({ spec, email_body: emailBody, sender: sender || undefined, subject: subject || undefined })
  }

  const result: ParserTestResult | undefined = testMutation.data

  return (
    <div className={cn('space-y-4', className)}>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Người gửi (sender)
          </label>
          <input
            type="text"
            value={sender}
            onChange={(e) => setSender(e.target.value)}
            className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            placeholder="notify@bank.com"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Tiêu đề email (subject)
          </label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            placeholder="Thông báo giao dịch"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Nội dung email
        </label>
        <textarea
          value={emailBody}
          onChange={(e) => setEmailBody(e.target.value)}
          rows={6}
          className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono resize-y"
          placeholder="Dán nội dung email ngân hàng vào đây..."
        />
      </div>

      <Button
        variant="primary"
        onClick={handleTest}
        isLoading={testMutation.isPending}
        disabled={!emailBody.trim()}
        size="sm"
      >
        Kiểm tra Parser
      </Button>

      {testMutation.isError && (
        <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700 dark:text-red-300">
            {testMutation.error?.message || 'Đã xảy ra lỗi khi kiểm tra parser'}
          </p>
        </div>
      )}

      {result && (
        <div
          className={cn(
            'rounded-lg border p-4 space-y-3',
            result.matched
              ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
              : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
          )}
        >
          <div className="flex items-center gap-2">
            {result.matched ? (
              <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
            ) : (
              <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            )}
            <span
              className={cn(
                'font-semibold text-sm',
                result.matched
                  ? 'text-green-700 dark:text-green-300'
                  : 'text-red-700 dark:text-red-300'
              )}
            >
              {result.matched ? 'Parser khớp thành công' : 'Parser không khớp'}
            </span>
            <span className="ml-auto flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              {result.execution_time_ms.toFixed(1)}ms
            </span>
          </div>

          {result.matched && result.parsed && (
            <div>
              <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                Dữ liệu trích xuất:
              </p>
              <div className="space-y-1">
                {Object.entries(result.parsed).map(([key, value]) => (
                  <div key={key} className="flex gap-2 text-sm">
                    <span className="font-mono text-green-600 dark:text-green-400 font-medium min-w-24">
                      {key}:
                    </span>
                    <span className="text-gray-700 dark:text-gray-300 font-mono">
                      {String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.errors && result.errors.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">
                Lỗi:
              </p>
              <ul className="space-y-0.5">
                {result.errors.map((err, i) => (
                  <li key={i} className="text-xs text-red-600 dark:text-red-400 font-mono">
                    {err}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
