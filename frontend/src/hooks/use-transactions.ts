import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { transactionApi } from '@/api'
import { Transaction, TransactionQueryParams, PaginatedResponse } from '@/types'

// Query keys
const transactionKeys = {
  all: ['transactions'] as const,
  lists: () => [...transactionKeys.all, 'list'] as const,
  list: (params: TransactionQueryParams) =>
    [...transactionKeys.lists(), params] as const,
  detail: (id: string) => [...transactionKeys.all, 'detail', id] as const,
  pending: () => [...transactionKeys.all, 'pending'] as const,
  statistics: (params?: any) =>
    [...transactionKeys.all, 'statistics', params] as const,
}

// Hooks
export const useTransactions = (params?: TransactionQueryParams) => {
  return useQuery({
    queryKey: transactionKeys.list(params || {}),
    queryFn: () => transactionApi.getTransactions(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
  })
}

export const useTransaction = (id?: string) => {
  return useQuery({
    queryKey: id ? transactionKeys.detail(id) : ['transaction', null],
    queryFn: () => (id ? transactionApi.getTransaction(id) : null),
    enabled: !!id,
  })
}

export const usePendingTransactions = () => {
  return useQuery({
    queryKey: transactionKeys.pending(),
    queryFn: () => transactionApi.getPendingTransactions(),
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000,
  })
}

export const useUpdateTransaction = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Transaction> }) =>
      transactionApi.updateTransaction(id, data),
    onSuccess: (data) => {
      queryClient.setQueryData(
        transactionKeys.detail(data.id),
        data
      )
      queryClient.invalidateQueries({
        queryKey: transactionKeys.lists(),
      })
    },
  })
}

export const useCategorizeTransaction = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, categoryId }: { id: string; categoryId: string }) =>
      transactionApi.categorizeTransaction(id, categoryId),
    onSuccess: (data) => {
      queryClient.setQueryData(
        transactionKeys.detail(data.id),
        data
      )
      queryClient.invalidateQueries({
        queryKey: transactionKeys.lists(),
      })
    },
  })
}

export const useDeleteTransaction = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => transactionApi.deleteTransaction(id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: transactionKeys.lists(),
      })
    },
  })
}

export const useTransactionStatistics = (params?: {
  startDate?: string
  endDate?: string
  accountId?: string
}) => {
  return useQuery({
    queryKey: transactionKeys.statistics(params),
    queryFn: () => transactionApi.getStatistics(params),
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}
