import React, { useState, useMemo } from 'react'
import { cn } from '@/utils/cn'

interface RegexMatch {
  fullMatch: string
  groups: string[]
  namedGroups: Record<string, string>
}

interface RegexTesterProps {
  pattern: string
  onPatternChange: (value: string) => void
  label?: string
  placeholder?: string
  className?: string
}

export const RegexTester: React.FC<RegexTesterProps> = ({
  pattern,
  onPatternChange,
  label,
  placeholder = 'Nhập chuỗi để kiểm tra...',
  className,
}) => {
  const [testString, setTestString] = useState('')
  const [flags, setFlags] = useState('i')

  const result = useMemo<{ matches: RegexMatch[]; error: string | null }>(() => {
    if (!pattern || !testString) return { matches: [], error: null }

    try {
      const regex = new RegExp(pattern, flags + 'g')
      const matches: RegexMatch[] = []
      let m: RegExpExecArray | null

      while ((m = regex.exec(testString)) !== null) {
        matches.push({
          fullMatch: m[0],
          groups: m.slice(1),
          namedGroups: (m.groups as Record<string, string>) ?? {},
        })
        // Prevent infinite loop on zero-length matches
        if (m[0].length === 0) {
          regex.lastIndex++
        }
      }

      return { matches, error: null }
    } catch (e) {
      return { matches: [], error: e instanceof Error ? e.message : 'Lỗi regex không hợp lệ' }
    }
  }, [pattern, testString, flags])

  const hasMatches = result.matches.length > 0

  return (
    <div className={cn('space-y-2', className)}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
        </label>
      )}

      {/* Pattern input */}
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-mono text-sm select-none">
            /
          </span>
          <input
            type="text"
            value={pattern}
            onChange={(e) => onPatternChange(e.target.value)}
            className={cn(
              'w-full pl-6 pr-6 py-2 font-mono text-sm border rounded-lg',
              'bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
              'border-gray-300 dark:border-gray-600',
              'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
              result.error && 'border-red-400 focus:ring-red-400'
            )}
            placeholder="pattern"
            spellCheck={false}
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 font-mono text-sm select-none">
            /
          </span>
        </div>
        <input
          type="text"
          value={flags}
          onChange={(e) => setFlags(e.target.value.replace(/[^gimsuy]/g, ''))}
          className="w-16 px-2 py-2 font-mono text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-center"
          placeholder="gi"
          maxLength={6}
        />
      </div>

      {result.error && (
        <p className="text-xs text-red-600 dark:text-red-400">{result.error}</p>
      )}

      {/* Test string */}
      <input
        type="text"
        value={testString}
        onChange={(e) => setTestString(e.target.value)}
        className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        placeholder={placeholder}
      />

      {/* Result */}
      {testString && pattern && !result.error && (
        <div
          className={cn(
            'px-3 py-2 rounded-lg text-sm',
            hasMatches
              ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
              : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
          )}
        >
          {hasMatches ? (
            <div className="space-y-1">
              <p className="font-medium text-green-700 dark:text-green-400">
                {result.matches.length} kết quả tìm thấy
              </p>
              {result.matches.map((match, i) => (
                <div key={i} className="text-green-600 dark:text-green-300">
                  <span className="font-mono bg-green-100 dark:bg-green-900/40 px-1 rounded">
                    {match.fullMatch}
                  </span>
                  {match.groups.length > 0 && (
                    <span className="text-xs ml-2 text-green-500">
                      Nhóm: [{match.groups.map((g) => JSON.stringify(g)).join(', ')}]
                    </span>
                  )}
                  {Object.keys(match.namedGroups).length > 0 && (
                    <div className="text-xs mt-0.5 space-x-1">
                      {Object.entries(match.namedGroups).map(([k, v]) => (
                        <span key={k} className="font-mono">
                          <span className="text-green-500">{k}</span>
                          <span className="text-green-400">: </span>
                          <span className="bg-green-100 dark:bg-green-900/40 px-0.5 rounded">
                            {v}
                          </span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-red-600 dark:text-red-400">Không khớp</p>
          )}
        </div>
      )}
    </div>
  )
}
