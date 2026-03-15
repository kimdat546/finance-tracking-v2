import client from './client'
import { Transaction, PaginatedResponse, TransactionQueryParams } from '@/types'

export const transactionApi = {
  // Get paginated transactions
  getTransactions: async (params?: TransactionQueryParams) => {
    const response = await client.get<PaginatedResponse<Transaction>>(
      '/transactions',
      { params }
    )
    return response.data
  },

  // Get single transaction
  getTransaction: async (id: string) => {
    const response = await client.get<Transaction>(`/transactions/${id}`)
    return response.data
  },

  // Update transaction
  updateTransaction: async (id: string, data: Partial<Transaction>) => {
    const response = await client.put<Transaction>(`/transactions/${id}`, data)
    return response.data
  },

  // Get pending transactions (needs review)
  getPendingTransactions: async () => {
    const response = await client.get<PaginatedResponse<Transaction>>(
      '/transactions/pending'
    )
    return response.data
  },

  // Categorize a transaction
  categorizeTransaction: async (id: string, categoryId: string) => {
    const response = await client.patch<Transaction>(
      `/transactions/${id}/categorize`,
      { categoryId }
    )
    return response.data
  },

  // Bulk ingest transactions (for manual import)
  ingestTransactions: async (data: {
    transactions: Partial<Transaction>[]
  }) => {
    const response = await client.post<PaginatedResponse<Transaction>>(
      '/transactions/ingest',
      data
    )
    return response.data
  },

  // Delete transaction
  deleteTransaction: async (id: string) => {
    await client.delete(`/transactions/${id}`)
  },

  // Get transaction statistics
  getStatistics: async (params?: {
    startDate?: string
    endDate?: string
    accountId?: string
  }) => {
    const response = await client.get<{
      totalIncome: number
      totalExpense: number
      netSavings: number
      categoryBreakdown: Record<string, number>
    }>('/transactions/statistics', { params })
    return response.data
  },
}
