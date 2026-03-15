import { format, formatDistance, parseISO } from 'date-fns'
import { vi } from 'date-fns/locale'

/**
 * Format amount as Vietnamese Dong
 * @example formatVND(1234567) => "1.234.567 ₫"
 */
export const formatVND = (amount: number, includeSymbol = true): string => {
  const formatted = new Intl.NumberFormat('vi-VN').format(Math.round(amount))
  return includeSymbol ? `${formatted} ₫` : formatted
}

/**
 * Format currency amount
 * @example formatCurrency(1234.56, 'USD') => "1,234.56 USD"
 */
export const formatCurrency = (
  amount: number,
  currency: string = 'VND'
): string => {
  if (currency === 'VND') {
    return formatVND(amount)
  }
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
  return `${currency} ${formatted}`
}

/**
 * Format date as DD/MM/YYYY
 * @example formatDate(new Date()) => "15/03/2026"
 */
export const formatDate = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? parseISO(date) : date
  return format(dateObj, 'dd/MM/yyyy', { locale: vi })
}

/**
 * Format datetime as DD/MM/YYYY HH:mm
 */
export const formatDateTime = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? parseISO(date) : date
  return format(dateObj, 'dd/MM/yyyy HH:mm', { locale: vi })
}

/**
 * Format time as HH:mm
 */
export const formatTime = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? parseISO(date) : date
  return format(dateObj, 'HH:mm', { locale: vi })
}

/**
 * Format relative time
 * @example formatRelativeTime('2026-03-15T10:00:00Z') => "2 giờ trước"
 */
export const formatRelativeTime = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? parseISO(date) : date
  return formatDistance(dateObj, new Date(), {
    addSuffix: true,
    locale: vi,
  })
}

/**
 * Format month as "Tháng 3, 2026"
 */
export const formatMonth = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? parseISO(date) : date
  return format(dateObj, 'MMMM, yyyy', { locale: vi })
}

/**
 * Format week range as "15/03 - 21/03"
 */
export const formatWeek = (date: string | Date): string => {
  const dateObj = typeof date === 'string' ? parseISO(date) : date
  const weekStart = new Date(dateObj)
  weekStart.setDate(dateObj.getDate() - dateObj.getDay())
  const weekEnd = new Date(weekStart)
  weekEnd.setDate(weekStart.getDate() + 6)

  return `${format(weekStart, 'dd/MM')} - ${format(weekEnd, 'dd/MM')}`
}

/**
 * Parse date string to Date object
 */
export const parseDate = (dateString: string): Date => {
  return parseISO(dateString)
}

/**
 * Format percentage
 * @example formatPercentage(75.5) => "75.5%"
 */
export const formatPercentage = (value: number, decimals = 1): string => {
  return `${value.toFixed(decimals)}%`
}

/**
 * Shorten long text with ellipsis
 */
export const truncate = (text: string, length: number): string => {
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}
