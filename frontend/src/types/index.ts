// Enums
export enum TransactionDirection {
  INFLOW = 'inflow',
  OUTFLOW = 'outflow',
}

export enum TransactionType {
  INCOME = 'income',
  EXPENSE = 'expense',
  TRANSFER = 'transfer',
}

// Models
export interface Category {
  id: string
  name: string
  icon?: string
  color?: string
  isCustom?: boolean
}

export interface Account {
  id: string
  name: string
  accountNumber?: string
  balance: number
  currency: string
  type: 'bank' | 'cash' | 'credit_card' | 'crypto'
  institution?: string
  account_type?: string
}

export interface Contact {
  id: string
  name: string
  email?: string
  phone?: string
  avatar?: string
}

export interface Transaction {
  id: string
  date: string
  amount: number
  currency: string
  description: string
  category?: Category
  categoryId?: string
  account?: Account
  accountId: string
  type: TransactionType
  direction: TransactionDirection
  counterparty?: string
  tags?: string[]
  notes?: string
  attachments?: Attachment[]
  status: 'confirmed' | 'pending' | 'review'
  createdAt: string
  updatedAt: string
}

export interface Attachment {
  id: string
  url: string
  fileName: string
  uploadedAt: string
}

export interface SplitParticipant {
  id: string
  name: string
  email?: string
  amount: number
  paid?: boolean
}

export interface SplitBill {
  id: string
  title: string
  totalAmount: number
  currency: string
  date: string
  createdBy: Contact
  participants: SplitParticipant[]
  description?: string
  status: 'pending' | 'settled' | 'partial'
  createdAt: string
  updatedAt: string
}

export interface Budget {
  id: string
  name: string
  category?: Category
  amount: number
  spent_amount: number
  remaining: number
  currency: string
  period: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly'
  start_date: string
  end_date?: string
  alert_threshold: number
  is_active: boolean
  createdAt: string
  updatedAt: string
}

export interface Goal {
  id: string
  name: string
  targetAmount: number
  currentAmount: number
  currency: string
  targetDate: string
  priority: 'low' | 'medium' | 'high'
  status: 'active' | 'completed' | 'cancelled'
  createdAt: string
  updatedAt: string
}

export interface Debt {
  id: string
  name: string
  creditor: string
  originalAmount: number
  remainingAmount: number
  currency: string
  interestRate?: number
  dueDate?: string
  monthlyPayment?: number
  status: 'active' | 'paid_off' | 'defaulted'
  createdAt: string
  updatedAt: string
}

export interface Subscription {
  id: string
  name: string
  amount: number
  currency: string
  billing_cycle: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly'
  next_billing_date: string
  start_date: string
  end_date?: string
  category?: Category
  is_active: boolean
  is_auto_renew: boolean
  createdAt: string
  updatedAt: string
}

// API Response Types
export interface PaginatedResponse<T> {
  data: T[]
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export interface ApiError {
  statusCode: number
  message: string
  errors?: Record<string, string[]>
}

// Query Params
export interface TransactionQueryParams {
  page?: number
  pageSize?: number
  startDate?: string
  endDate?: string
  categoryId?: string
  accountId?: string
  direction?: TransactionDirection
  type?: TransactionType
  status?: 'confirmed' | 'pending' | 'review'
  search?: string
  sortBy?: 'date' | 'amount' | 'description'
  sortOrder?: 'asc' | 'desc'
}

export interface BudgetQueryParams {
  month?: string
  year?: number
  categoryId?: string
}

export interface GoalQueryParams {
  status?: 'active' | 'completed' | 'cancelled'
  priority?: 'low' | 'medium' | 'high'
}
