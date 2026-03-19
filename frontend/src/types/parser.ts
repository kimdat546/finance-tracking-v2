export interface ParserInfo {
  name: string;
  description: string;
  version: string;
  enabled: boolean;
  priority: number;
  supported_senders?: string;
  is_builtin: boolean;
  success_rate_24h?: number;
  total_attempts_24h?: number;
  avg_time_ms?: number;
  status: 'healthy' | 'degraded' | 'failed' | 'disabled' | 'unknown';
  last_attempt_at?: string;
}

export interface ParserMetric {
  metric_date: string;
  success_count: number;
  failure_count: number;
  success_rate: number;
  avg_parse_time_ms: number;
}

export interface ParserAlert {
  id: string;
  parser_name: string;
  status: 'healthy' | 'degraded' | 'failed';
  message: string;
  error_count_24h: number;
  success_count_24h: number;
  is_acknowledged: boolean;
  created_at: string;
}

export interface DynamicParserSpec {
  id: string;
  name: string;
  version: string;
  enabled: boolean;
  priority: number;
  description: string;
  spec_json?: string;
  created_at: string;
}

export interface ParserTestResult {
  matched: boolean;
  parsed: Record<string, unknown> | null;
  errors: string[];
  execution_time_ms: number;
}
