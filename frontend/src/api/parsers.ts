import apiClient from '@/api/client'

// Built-in parsers (from registry)
export const getParsers = () => apiClient.get('/parser-health/dashboard').then(r => r.data)
export const getParserMetrics = (name: string, days = 30) =>
  apiClient.get(`/parser-health/parsers/${name}/metrics`, { params: { days } }).then(r => r.data)
export const getParserSummary = (name: string) =>
  apiClient.get(`/parser-health/parsers/${name}/summary`).then(r => r.data)

// Dynamic parsers
export const getDynamicParsers = () => apiClient.get('/dynamic-parsers').then(r => r.data)
export const createDynamicParser = (data: { spec: unknown; is_public: boolean }) =>
  apiClient.post('/dynamic-parsers', data).then(r => r.data)
export const toggleDynamicParser = (id: string, enabled: boolean) =>
  apiClient.patch(`/dynamic-parsers/${id}/toggle`, { enabled }).then(r => r.data)
export const deleteDynamicParser = (id: string) =>
  apiClient.delete(`/dynamic-parsers/${id}`).then(r => r.data)
export const testDynamicParser = (data: { spec: unknown; email_body: string; sender?: string; subject?: string }) =>
  apiClient.post('/dynamic-parsers/test', data).then(r => r.data)

// Alerts
export const getParserAlerts = () => apiClient.get('/parser-health/alerts').then(r => r.data)
export const acknowledgeAlert = (id: string) =>
  apiClient.post(`/parser-health/alerts/${id}/acknowledge`).then(r => r.data)
