import React, { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ChevronRight,
  ChevronLeft,
  Check,
  CheckCircle,
  XCircle,
  AlertCircle,
  Plus,
  Trash2,
  ArrowLeft,
} from 'lucide-react'
import { Button, Badge, Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui'
import { cn } from '@/utils/cn'
import { RegexTester } from './components/RegexTester'
import { ParserTester } from './components/ParserTester'
import { useCreateDynamicParser } from '@/hooks/useParsers'

// Types for wizard state
interface Extractor {
  field: string
  pattern: string
  transform?: string
}

interface Matcher {
  type: 'sender' | 'subject' | 'body'
  pattern: string
}

interface ParserSpec {
  name: string
  version: string
  description: string
  matchers: Matcher[]
  extractors: Extractor[]
  rules: unknown[]
}

interface WizardState {
  // Step 1
  emailBody: string
  sender: string
  subject: string
  // Step 2 - detected fields
  detectedFields: Record<string, { found: boolean; sample: string }>
  // Step 3 - extractor config
  extractors: Extractor[]
  // Step 4 - matchers
  matchers: Matcher[]
  // Step 6 - save
  parserName: string
  parserDescription: string
  isPublic: boolean
}

const STEPS = [
  { id: 1, label: 'Tải email mẫu', short: 'Email mẫu' },
  { id: 2, label: 'Phân tích cấu trúc', short: 'Phân tích' },
  { id: 3, label: 'Cấu hình extractor', short: 'Extractor' },
  { id: 4, label: 'Bộ lọc email', short: 'Bộ lọc' },
  { id: 5, label: 'Kiểm tra', short: 'Kiểm tra' },
  { id: 6, label: 'Lưu', short: 'Lưu' },
]

const FIELD_LABELS: Record<string, string> = {
  amount: 'Số tiền',
  merchant: 'Người nhận/Nơi chi tiêu',
  date: 'Ngày giao dịch',
  balance: 'Số dư',
  transaction_id: 'Mã giao dịch',
  account: 'Tài khoản',
}

// Patterns to detect fields in email body
const FIELD_DETECTION_PATTERNS: Record<string, RegExp[]> = {
  amount: [
    /(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:VND|đồng|₫|vnd)/i,
    /(?:số tiền|amount|tiền)\s*[:\s]+(\d[\d.,]+)/i,
  ],
  merchant: [
    /(?:tại|at|merchant|người thụ hưởng|beneficiary)\s*[:\s]+([^\n]+)/i,
  ],
  date: [
    /(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/,
    /(\d{4}-\d{2}-\d{2})/,
  ],
  balance: [
    /(?:số dư|balance|remaining)\s*[:\s]+(\d[\d.,]+)/i,
  ],
  transaction_id: [
    /(?:mã gd|transaction id|ref|mã giao dịch)\s*[:\s]+([A-Z0-9]+)/i,
  ],
}

function detectFields(emailBody: string): Record<string, { found: boolean; sample: string }> {
  const result: Record<string, { found: boolean; sample: string }> = {}
  for (const [field, patterns] of Object.entries(FIELD_DETECTION_PATTERNS)) {
    let found = false
    let sample = ''
    for (const pattern of patterns) {
      const match = emailBody.match(pattern)
      if (match) {
        found = true
        sample = match[1] ?? match[0]
        break
      }
    }
    result[field] = { found, sample }
  }
  return result
}

function buildDefaultExtractors(detected: Record<string, { found: boolean; sample: string }>): Extractor[] {
  const defaults: Record<string, string> = {
    amount: '(\\d{1,3}(?:[.,]\\d{3})*(?:[.,]\\d{2})?)\\s*(?:VND|đồng|₫)',
    merchant: '(?:tại|at|merchant)\\s*[:\\s]+([^\\n]+)',
    date: '(\\d{1,2}[/\\-]\\d{1,2}[/\\-]\\d{2,4})',
    balance: '(?:số dư|balance)\\s*[:\\s]+(\\d[\\d.,]+)',
    transaction_id: '(?:mã gd|ref)\\s*[:\\s]+([A-Z0-9]+)',
  }

  return Object.entries(detected)
    .filter(([, v]) => v.found)
    .map(([field]) => ({
      field,
      pattern: defaults[field] ?? '',
    }))
}

// Step 1: Load sample email
interface Step1Props {
  state: WizardState
  onChange: (updates: Partial<WizardState>) => void
}
const Step1: React.FC<Step1Props> = ({ state, onChange }) => (
  <div className="space-y-4">
    <p className="text-sm text-gray-600 dark:text-gray-400">
      Dán nội dung email ngân hàng mẫu vào đây. Hệ thống sẽ tự động phát hiện các trường dữ liệu.
    </p>

    <div className="grid grid-cols-2 gap-3">
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Người gửi (sender)
        </label>
        <input
          type="text"
          value={state.sender}
          onChange={(e) => onChange({ sender: e.target.value })}
          className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          placeholder="notify@vietcombank.com.vn"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Tiêu đề email
        </label>
        <input
          type="text"
          value={state.subject}
          onChange={(e) => onChange({ subject: e.target.value })}
          className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          placeholder="Thông báo giao dịch thẻ"
        />
      </div>
    </div>

    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        Nội dung email <span className="text-red-500">*</span>
      </label>
      <textarea
        value={state.emailBody}
        onChange={(e) => onChange({ emailBody: e.target.value })}
        rows={10}
        className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono resize-y"
        placeholder={`Ví dụ:\nKính gửi Quý khách,\nTài khoản của quý khách vừa phát sinh giao dịch:\nSố tiền: 500,000 VND\nTại: GRAB\nNgày: 15/03/2026\nSố dư: 2,500,000 VND`}
      />
    </div>
  </div>
)

// Step 2: Analyze structure
interface Step2Props {
  state: WizardState
}
const Step2: React.FC<Step2Props> = ({ state }) => {
  const detected = state.detectedFields

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Kết quả phân tích tự động nội dung email. Các trường được phát hiện sẽ được thêm vào cấu hình extractor.
      </p>

      <div className="space-y-2">
        {Object.entries(FIELD_LABELS).map(([field, label]) => {
          const info = detected[field]
          return (
            <div
              key={field}
              className={cn(
                'flex items-center gap-3 p-3 rounded-lg border',
                info?.found
                  ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                  : 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700'
              )}
            >
              {info?.found ? (
                <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" />
              ) : (
                <XCircle className="w-4 h-4 text-gray-400 flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium text-gray-900 dark:text-white">{label}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400 ml-2 font-mono">{field}</span>
              </div>
              {info?.found && info.sample && (
                <span className="text-xs font-mono text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-900/40 px-2 py-0.5 rounded truncate max-w-32">
                  {info.sample}
                </span>
              )}
              {!info?.found && (
                <span className="text-xs text-gray-400">Không phát hiện</span>
              )}
            </div>
          )
        })}
      </div>

      {Object.values(detected).every((v) => !v.found) && (
        <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-yellow-700 dark:text-yellow-300">
            Không phát hiện trường nào tự động. Bạn có thể tự định nghĩa các extractor ở bước tiếp theo.
          </p>
        </div>
      )}
    </div>
  )
}

// Step 3: Extractor configuration
interface Step3Props {
  state: WizardState
  onChange: (updates: Partial<WizardState>) => void
}
const Step3: React.FC<Step3Props> = ({ state, onChange }) => {
  const addExtractor = () => {
    onChange({ extractors: [...state.extractors, { field: '', pattern: '' }] })
  }

  const updateExtractor = (i: number, updates: Partial<Extractor>) => {
    const updated = state.extractors.map((e, idx) => idx === i ? { ...e, ...updates } : e)
    onChange({ extractors: updated })
  }

  const removeExtractor = (i: number) => {
    onChange({ extractors: state.extractors.filter((_, idx) => idx !== i) })
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Định nghĩa các regex để trích xuất dữ liệu từ email. Sử dụng nhóm capture <code className="font-mono bg-gray-100 dark:bg-gray-800 px-1 rounded">()</code> để lấy giá trị.
      </p>

      <div className="space-y-4">
        {state.extractors.map((ext, i) => (
          <Card key={i} className="p-4">
            <CardContent className="p-0 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Extractor #{i + 1}
                </span>
                <button
                  onClick={() => removeExtractor(i)}
                  className="text-red-500 hover:text-red-700 p-1 rounded"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Tên trường
                </label>
                <select
                  value={ext.field}
                  onChange={(e) => updateExtractor(i, { field: e.target.value })}
                  className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Chọn trường...</option>
                  {Object.entries(FIELD_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v} ({k})</option>
                  ))}
                  <option value="custom">Tùy chỉnh...</option>
                </select>
                {ext.field === 'custom' && (
                  <input
                    type="text"
                    className="mt-1 w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="Tên trường tùy chỉnh"
                    onChange={(e) => updateExtractor(i, { field: e.target.value })}
                  />
                )}
              </div>

              <RegexTester
                pattern={ext.pattern}
                onPatternChange={(v) => updateExtractor(i, { pattern: v })}
                label="Pattern (regex)"
                placeholder={state.emailBody || 'Nhập chuỗi từ email để kiểm tra...'}
              />

              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Biến đổi (transform) <span className="text-gray-400 font-normal">- tùy chọn</span>
                </label>
                <select
                  value={ext.transform ?? ''}
                  onChange={(e) => updateExtractor(i, { transform: e.target.value || undefined })}
                  className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Không</option>
                  <option value="number">Chuyển thành số</option>
                  <option value="date_vn">Ngày Việt Nam (dd/mm/yyyy)</option>
                  <option value="remove_dots">Xóa dấu chấm phân cách</option>
                  <option value="trim">Trim khoảng trắng</option>
                </select>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Button variant="secondary" size="sm" onClick={addExtractor}>
        <Plus className="w-4 h-4 mr-1.5" />
        Thêm Extractor
      </Button>
    </div>
  )
}

// Step 4: Email filters / matchers
interface Step4Props {
  state: WizardState
  onChange: (updates: Partial<WizardState>) => void
}
const Step4: React.FC<Step4Props> = ({ state, onChange }) => {
  const addMatcher = () => {
    onChange({ matchers: [...state.matchers, { type: 'sender', pattern: '' }] })
  }

  const updateMatcher = (i: number, updates: Partial<Matcher>) => {
    onChange({ matchers: state.matchers.map((m, idx) => idx === i ? { ...m, ...updates } : m) })
  }

  const removeMatcher = (i: number) => {
    onChange({ matchers: state.matchers.filter((_, idx) => idx !== i) })
  }

  const MATCHER_TYPE_LABELS: Record<Matcher['type'], string> = {
    sender: 'Người gửi (sender)',
    subject: 'Tiêu đề (subject)',
    body: 'Nội dung (body)',
  }

  const MATCHER_PLACEHOLDERS: Record<Matcher['type'], string> = {
    sender: 'notify@.*\\.vietcombank\\.com\\.vn',
    subject: 'Thông báo giao dịch.*',
    body: 'Tài khoản.*phát sinh giao dịch',
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Định nghĩa điều kiện để parser nhận ra email ngân hàng. Tất cả điều kiện phải khớp (AND).
      </p>

      <div className="space-y-3">
        {state.matchers.map((matcher, i) => (
          <Card key={i} className="p-4">
            <CardContent className="p-0 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Bộ lọc #{i + 1}
                </span>
                <button
                  onClick={() => removeMatcher(i)}
                  className="text-red-500 hover:text-red-700 p-1 rounded"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Loại bộ lọc
                  </label>
                  <select
                    value={matcher.type}
                    onChange={(e) => updateMatcher(i, { type: e.target.value as Matcher['type'] })}
                    className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    {Object.entries(MATCHER_TYPE_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </div>
              </div>

              <RegexTester
                pattern={matcher.pattern}
                onPatternChange={(v) => updateMatcher(i, { pattern: v })}
                label="Pattern (regex)"
                placeholder={
                  matcher.type === 'sender'
                    ? state.sender || MATCHER_PLACEHOLDERS.sender
                    : matcher.type === 'subject'
                    ? state.subject || MATCHER_PLACEHOLDERS.subject
                    : state.emailBody.substring(0, 100) || MATCHER_PLACEHOLDERS.body
                }
              />
            </CardContent>
          </Card>
        ))}
      </div>

      <Button variant="secondary" size="sm" onClick={addMatcher}>
        <Plus className="w-4 h-4 mr-1.5" />
        Thêm Bộ lọc
      </Button>

      {state.matchers.length === 0 && (
        <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-yellow-700 dark:text-yellow-300">
            Khuyến nghị thêm ít nhất một bộ lọc để parser không khớp sai với các email khác.
          </p>
        </div>
      )}
    </div>
  )
}

// Step 5: Test
interface Step5Props {
  spec: ParserSpec
  emailBody: string
  sender: string
  subject: string
}
const Step5: React.FC<Step5Props> = ({ spec, emailBody, sender, subject }) => (
  <div className="space-y-3">
    <p className="text-sm text-gray-600 dark:text-gray-400">
      Kiểm tra parser với email mẫu đã nhập. Nhấn "Kiểm tra Parser" để xem kết quả.
    </p>
    <ParserTester
      spec={spec}
      initialEmailBody={emailBody}
      initialSender={sender}
      initialSubject={subject}
    />
  </div>
)

// Step 6: Save
interface Step6Props {
  state: WizardState
  onChange: (updates: Partial<WizardState>) => void
  spec: ParserSpec
  onSave: () => void
  isSaving: boolean
  saveError: string | null
}
const Step6: React.FC<Step6Props> = ({ state, onChange, spec, onSave, isSaving, saveError }) => (
  <div className="space-y-4">
    <p className="text-sm text-gray-600 dark:text-gray-400">
      Đặt tên và lưu parser mới. Parser sẽ được kích hoạt ngay sau khi lưu.
    </p>

    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        Tên parser <span className="text-red-500">*</span>
      </label>
      <input
        type="text"
        value={state.parserName}
        onChange={(e) => onChange({ parserName: e.target.value })}
        className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500"
        placeholder="vd: Vietcombank Debit Notification"
      />
    </div>

    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        Mô tả
      </label>
      <textarea
        value={state.parserDescription}
        onChange={(e) => onChange({ parserDescription: e.target.value })}
        rows={2}
        className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
        placeholder="Mô tả ngắn về parser này..."
      />
    </div>

    <div className="flex items-center gap-3">
      <button
        role="switch"
        aria-checked={state.isPublic}
        onClick={() => onChange({ isPublic: !state.isPublic })}
        className={cn(
          'relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500',
          state.isPublic ? 'bg-primary-600' : 'bg-gray-300 dark:bg-gray-600'
        )}
      >
        <span
          className={cn(
            'inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform',
            state.isPublic ? 'translate-x-[18px]' : 'translate-x-[2px]'
          )}
        />
      </button>
      <span className="text-sm text-gray-700 dark:text-gray-300">
        Chia sẻ công khai với người dùng khác
      </span>
    </div>

    {/* Spec preview */}
    <div>
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
        Xem trước cấu hình (JSON):
      </p>
      <pre className="text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 overflow-auto max-h-40 text-gray-700 dark:text-gray-300">
        {JSON.stringify(spec, null, 2)}
      </pre>
    </div>

    {saveError && (
      <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-red-700 dark:text-red-300">{saveError}</p>
      </div>
    )}

    <Button
      variant="primary"
      onClick={onSave}
      isLoading={isSaving}
      disabled={!state.parserName.trim()}
    >
      <Check className="w-4 h-4 mr-1.5" />
      Lưu Parser
    </Button>
  </div>
)

export const ParserGeneratorPage: React.FC = () => {
  const navigate = useNavigate()
  const createMutation = useCreateDynamicParser()

  const [step, setStep] = useState(1)
  const [saveError, setSaveError] = useState<string | null>(null)

  const [wizardState, setWizardState] = useState<WizardState>({
    emailBody: '',
    sender: '',
    subject: '',
    detectedFields: {},
    extractors: [],
    matchers: [],
    parserName: '',
    parserDescription: '',
    isPublic: false,
  })

  const updateState = useCallback((updates: Partial<WizardState>) => {
    setWizardState((prev) => ({ ...prev, ...updates }))
  }, [])

  const buildSpec = (): ParserSpec => ({
    name: wizardState.parserName || 'unnamed_parser',
    version: '1.0.0',
    description: wizardState.parserDescription,
    matchers: wizardState.matchers,
    extractors: wizardState.extractors.filter((e) => e.field && e.pattern),
    rules: [],
  })

  const canProceed = (): boolean => {
    if (step === 1) return wizardState.emailBody.trim().length > 0
    if (step === 6) return wizardState.parserName.trim().length > 0
    return true
  }

  const handleNext = () => {
    if (step === 1) {
      // Run detection
      const detected = detectFields(wizardState.emailBody)
      const defaultExtractors = buildDefaultExtractors(detected)
      const defaultMatchers: Matcher[] = []
      if (wizardState.sender) {
        defaultMatchers.push({
          type: 'sender',
          pattern: wizardState.sender.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
        })
      }
      updateState({
        detectedFields: detected,
        extractors: defaultExtractors.length > 0 ? defaultExtractors : [{ field: '', pattern: '' }],
        matchers: defaultMatchers,
      })
    }
    setStep((s) => Math.min(s + 1, STEPS.length))
  }

  const handleBack = () => {
    setStep((s) => Math.max(s - 1, 1))
  }

  const handleSave = async () => {
    setSaveError(null)
    const spec = buildSpec()
    spec.name = wizardState.parserName
    spec.description = wizardState.parserDescription

    try {
      await createMutation.mutateAsync({ spec, is_public: wizardState.isPublic })
      navigate('/settings/email-parsers')
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Đã xảy ra lỗi khi lưu parser')
    }
  }

  const spec = buildSpec()

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/settings/email-parsers')}
          className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </button>
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Tạo Email Parser
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
            Hướng dẫn tạo parser từ email mẫu
          </p>
        </div>
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-0 overflow-x-auto pb-1">
        {STEPS.map((s, idx) => (
          <React.Fragment key={s.id}>
            <div
              className={cn(
                'flex items-center gap-1.5 px-2 py-1.5 rounded-lg transition-colors flex-shrink-0',
                step === s.id
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : step > s.id
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-gray-400 dark:text-gray-600'
              )}
            >
              <div
                className={cn(
                  'w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0',
                  step === s.id
                    ? 'bg-primary-600 text-white'
                    : step > s.id
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                )}
              >
                {step > s.id ? <Check className="w-3 h-3" /> : s.id}
              </div>
              <span className="text-xs font-medium hidden sm:inline">{s.short}</span>
            </div>
            {idx < STEPS.length - 1 && (
              <div
                className={cn(
                  'flex-1 h-px min-w-2',
                  step > s.id
                    ? 'bg-green-400 dark:bg-green-600'
                    : 'bg-gray-200 dark:bg-gray-700'
                )}
              />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Step content */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Bước {step}: {STEPS[step - 1].label}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {step === 1 && <Step1 state={wizardState} onChange={updateState} />}
          {step === 2 && <Step2 state={wizardState} />}
          {step === 3 && <Step3 state={wizardState} onChange={updateState} />}
          {step === 4 && <Step4 state={wizardState} onChange={updateState} />}
          {step === 5 && (
            <Step5
              spec={spec}
              emailBody={wizardState.emailBody}
              sender={wizardState.sender}
              subject={wizardState.subject}
            />
          )}
          {step === 6 && (
            <Step6
              state={wizardState}
              onChange={updateState}
              spec={spec}
              onSave={handleSave}
              isSaving={createMutation.isPending}
              saveError={saveError}
            />
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      {step < 6 && (
        <div className="flex justify-between">
          <Button
            variant="secondary"
            onClick={handleBack}
            disabled={step === 1}
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Quay lại
          </Button>
          <Button
            variant="primary"
            onClick={handleNext}
            disabled={!canProceed()}
          >
            {step === 5 ? 'Tiếp tục lưu' : 'Tiếp theo'}
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      )}
    </div>
  )
}
