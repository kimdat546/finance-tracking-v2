import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getParsers,
  getParserMetrics,
  getDynamicParsers,
  createDynamicParser,
  toggleDynamicParser,
  deleteDynamicParser,
  testDynamicParser,
  getParserAlerts,
  acknowledgeAlert,
} from '@/api/parsers'
import type { ParserInfo, ParserMetric, DynamicParserSpec, ParserTestResult, ParserAlert } from '@/types/parser'

// Query keys
const parserKeys = {
  all: ['parsers'] as const,
  dashboard: () => [...parserKeys.all, 'dashboard'] as const,
  metrics: (name: string, days: number) => [...parserKeys.all, 'metrics', name, days] as const,
  dynamic: () => [...parserKeys.all, 'dynamic'] as const,
  alerts: () => [...parserKeys.all, 'alerts'] as const,
}

export interface ParserDashboard {
  parsers: ParserInfo[]
  total: number
  healthy: number
  degraded: number
  failed: number
}

export const useParsers = () => {
  return useQuery<ParserDashboard>({
    queryKey: parserKeys.dashboard(),
    queryFn: getParsers,
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
  })
}

export const useParserMetrics = (name: string, days = 30) => {
  return useQuery<ParserMetric[]>({
    queryKey: parserKeys.metrics(name, days),
    queryFn: () => getParserMetrics(name, days),
    enabled: !!name,
    staleTime: 5 * 60 * 1000,
  })
}

export const useDynamicParsers = () => {
  return useQuery<DynamicParserSpec[]>({
    queryKey: parserKeys.dynamic(),
    queryFn: getDynamicParsers,
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
  })
}

export const useCreateDynamicParser = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { spec: unknown; is_public: boolean }) => createDynamicParser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: parserKeys.dynamic() })
      queryClient.invalidateQueries({ queryKey: parserKeys.dashboard() })
    },
  })
}

export const useToggleDynamicParser = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      toggleDynamicParser(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: parserKeys.dynamic() })
    },
  })
}

export const useDeleteDynamicParser = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteDynamicParser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: parserKeys.dynamic() })
      queryClient.invalidateQueries({ queryKey: parserKeys.dashboard() })
    },
  })
}

export const useTestParser = () => {
  return useMutation<
    ParserTestResult,
    Error,
    { spec: unknown; email_body: string; sender?: string; subject?: string }
  >({
    mutationFn: testDynamicParser,
  })
}

export const useParserAlerts = () => {
  return useQuery<ParserAlert[]>({
    queryKey: parserKeys.alerts(),
    queryFn: getParserAlerts,
    staleTime: 1 * 60 * 1000,
    gcTime: 3 * 60 * 1000,
  })
}

export const useAcknowledgeAlert = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => acknowledgeAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: parserKeys.alerts() })
    },
  })
}
