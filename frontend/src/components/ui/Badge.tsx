import React from 'react'
import { cn } from '@/utils/cn'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'danger' | 'warning' | 'info'
  size?: 'sm' | 'md'
  children: React.ReactNode
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', size = 'md', children, ...props }, ref) => {
    const variants = {
      default: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
      success: 'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200',
      danger: 'bg-danger-100 text-danger-800 dark:bg-danger-900 dark:text-danger-200',
      warning: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200',
      info: 'bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200',
    }

    const sizes = {
      sm: 'px-2 py-1 text-xs font-medium rounded',
      md: 'px-3 py-1.5 text-sm font-medium rounded-md',
    }

    return (
      <span
        ref={ref}
        className={cn(variants[variant], sizes[size], className)}
        {...props}
      >
        {children}
      </span>
    )
  }
)

Badge.displayName = 'Badge'
