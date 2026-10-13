/**
 * QueueWise AI — API Client
 *
 * Centralized API client with error handling.
 * All backend communication goes through this module.
 */
import type {
  ServiceCategory,
  TokenPublicStatus,
  TokenCreateRequest,
  TokenResponse,
  Counter,
  QueueSummaryResponse,
  WaitEstimateDetail,
  NotificationResponse,
  ScenarioInfo,
  SimulationRunCreatePayload,
  SimulationRunResponse,
  OptimizerResponse,
  AnalyticsSummary,
  HourlyTrafficPoint,
  ServiceAnalyticsItem,
  CounterAnalyticsItem,
  ServiceEventLogItem,
  OperationalAnalyticsResponse,
  AgentResponse,
  AgentCapabilitiesResponse,
  VoiceQueryRequest,
  VoiceQueryResponse,
  VoiceAnnouncementsResponse,
} from '../types/api'

const API_BASE = '/api/v1'

export class ApiError extends Error {
  statusCode: number
  detail: string

  constructor(statusCode: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.statusCode = statusCode
    this.detail = detail
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new ApiError(response.status, error.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

/** GET request to the API */
export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  return handleResponse<T>(response)
}

/** POST request to the API */
export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  return handleResponse<T>(response)
}

/** PATCH request to the API */
export async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  return handleResponse<T>(response)
}

/** PUT request to the API */
export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  return handleResponse<T>(response)
}

/** Health check — uses root endpoint, not /api/v1 */
export async function checkHealth() {
  const response = await fetch('/health')
  return handleResponse<{ status: string; app: string; version: string }>(response)
}

/** List available services */
export async function getServices(): Promise<ServiceCategory[]> {
  return apiGet<ServiceCategory[]>('/services')
}

/** Issue a new token */
export async function createToken(data: TokenCreateRequest): Promise<TokenPublicStatus> {
  return apiPost<TokenPublicStatus>('/tokens', data)
}

/** Fetch public status of a token */
export async function getTokenStatus(publicId: string): Promise<TokenPublicStatus> {
  return apiGet<TokenPublicStatus>(`/tokens/${publicId}`)
}

/** Cancel a token */
export async function cancelToken(publicId: string, reason?: string): Promise<TokenPublicStatus> {
  const query = reason ? `?reason=${encodeURIComponent(reason)}` : ''
  return apiPost<TokenPublicStatus>(`/tokens/${publicId}/cancel${query}`)
}

/** List counters */
export async function getCounters(): Promise<Counter[]> {
  return apiGet<Counter[]>('/counters')
}

/** Get a single counter */
export async function getCounter(counterId: string): Promise<Counter> {
  return apiGet<Counter>(`/counters/${counterId}`)
}

/** Create a new counter */
export async function createCounter(data: { name: string; supported_service_ids?: string[] }): Promise<Counter> {
  return apiPost<Counter>('/counters', data)
}

/** Update counter supported services */
export async function updateCounterServices(counterId: string, serviceIds: string[]): Promise<Counter> {
  return apiPut<Counter>(`/counters/${counterId}/services`, { supported_service_ids: serviceIds })
}

/** Counter operator controls */
export async function openCounter(counterId: string): Promise<Counter> {
  return apiPost<Counter>(`/counters/${counterId}/open`)
}

export async function pauseCounter(counterId: string): Promise<Counter> {
  return apiPost<Counter>(`/counters/${counterId}/pause`)
}

export async function resumeCounter(counterId: string): Promise<Counter> {
  return apiPost<Counter>(`/counters/${counterId}/resume`)
}

export async function closeCounter(counterId: string): Promise<Counter> {
  return apiPost<Counter>(`/counters/${counterId}/close`)
}

export async function callNextToken(counterId: string, sessionId: string = 'default'): Promise<TokenResponse | null> {
  return apiPost<TokenResponse | null>(`/counters/${counterId}/call-next?session_id=${encodeURIComponent(sessionId)}`)
}

export async function startServingToken(counterId: string): Promise<TokenResponse> {
  return apiPost<TokenResponse>(`/counters/${counterId}/serve`)
}

export async function completeServingToken(counterId: string): Promise<TokenResponse> {
  return apiPost<TokenResponse>(`/counters/${counterId}/complete`)
}

export async function skipToken(counterId: string, reason: string = 'No-show'): Promise<TokenResponse> {
  return apiPost<TokenResponse>(`/counters/${counterId}/skip?reason=${encodeURIComponent(reason)}`)
}

export async function recallToken(counterId: string, reason: string = 'Requeued'): Promise<TokenResponse> {
  return apiPost<TokenResponse>(`/counters/${counterId}/recall?reason=${encodeURIComponent(reason)}`)
}

/** List waiting tokens for a service */
export async function getWaitingTokens(serviceId: string, sessionId: string = 'default'): Promise<TokenPublicStatus[]> {
  return apiGet<TokenPublicStatus[]>(`/queues/${serviceId}/waiting?session_id=${encodeURIComponent(sessionId)}`)
}

/** Queue summary and wait estimates */
export async function getQueueSummary(sessionId: string = 'default'): Promise<QueueSummaryResponse> {
  return apiGet<QueueSummaryResponse>(`/queues/summary?session_id=${encodeURIComponent(sessionId)}`)
}

export async function getProspectiveWaitEstimate(
  serviceId: string,
  priority: number = 0,
  sessionId: string = 'default',
): Promise<WaitEstimateDetail> {
  return apiGet<WaitEstimateDetail>(
    `/queues/${serviceId}/estimate?priority=${priority}&session_id=${encodeURIComponent(sessionId)}`,
  )
}

/** Notifications for a token */
export async function getNotifications(tokenPublicId: string): Promise<NotificationResponse[]> {
  return apiGet<NotificationResponse[]>(`/notifications/${encodeURIComponent(tokenPublicId)}`)
}

/** --- Simulation Lab & Optimizer APIs --- */

export async function getScenarios(): Promise<ScenarioInfo[]> {
  return apiGet<ScenarioInfo[]>('/simulation/scenarios')
}

export async function getScenario(scenarioKey: string): Promise<ScenarioInfo> {
  return apiGet<ScenarioInfo>(`/simulation/scenarios/${encodeURIComponent(scenarioKey)}`)
}

export async function runSimulation(
  payload: SimulationRunCreatePayload,
  persist: boolean = true,
): Promise<SimulationRunResponse> {
  return apiPost<SimulationRunResponse>(`/simulation/runs?persist=${persist}`, payload)
}

export async function getSimulationRuns(limit: number = 20): Promise<SimulationRunResponse[]> {
  return apiGet<SimulationRunResponse[]>(`/simulation/runs?limit=${limit}`)
}

export async function getSimulationRun(runId: string): Promise<SimulationRunResponse> {
  return apiGet<SimulationRunResponse>(`/simulation/runs/${encodeURIComponent(runId)}`)
}

export async function optimizeCounters(payload: {
  total_counters: number
  target_sla_seconds?: number
  services?: Array<{
    code: string
    name: string
    arrival_rate_per_min: number
    avg_duration_seconds: number
    current_counters: number
  }>
}): Promise<OptimizerResponse> {
  return apiPost<OptimizerResponse>('/simulation/optimizer/recommend', payload)
}

/** --- Operational Analytics APIs --- */

export async function getAnalyticsSummary(params?: {
  hoursBack?: number
  sessionId?: string
  includeSimulations?: boolean
  slaSeconds?: number
}): Promise<AnalyticsSummary> {
  const query = new URLSearchParams()
  if (params?.hoursBack) query.set('hours_back', String(params.hoursBack))
  if (params?.sessionId) query.set('session_id', params.sessionId)
  if (params?.includeSimulations !== undefined) query.set('include_simulations', String(params.includeSimulations))
  if (params?.slaSeconds) query.set('sla_seconds', String(params.slaSeconds))
  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiGet<AnalyticsSummary>(`/analytics/summary${qs}`)
}

export async function getHourlyTrends(params?: {
  hoursBack?: number
  sessionId?: string
  includeSimulations?: boolean
}): Promise<HourlyTrafficPoint[]> {
  const query = new URLSearchParams()
  if (params?.hoursBack) query.set('hours_back', String(params.hoursBack))
  if (params?.sessionId) query.set('session_id', params.sessionId)
  if (params?.includeSimulations !== undefined) query.set('include_simulations', String(params.includeSimulations))
  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiGet<HourlyTrafficPoint[]>(`/analytics/hourly${qs}`)
}

export async function getServiceAnalytics(params?: {
  hoursBack?: number
  sessionId?: string
  includeSimulations?: boolean
  slaSeconds?: number
}): Promise<ServiceAnalyticsItem[]> {
  const query = new URLSearchParams()
  if (params?.hoursBack) query.set('hours_back', String(params.hoursBack))
  if (params?.sessionId) query.set('session_id', params.sessionId)
  if (params?.includeSimulations !== undefined) query.set('include_simulations', String(params.includeSimulations))
  if (params?.slaSeconds) query.set('sla_seconds', String(params.slaSeconds))
  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiGet<ServiceAnalyticsItem[]>(`/analytics/services${qs}`)
}

export async function getCounterAnalytics(params?: {
  hoursBack?: number
  includeSimulations?: boolean
}): Promise<CounterAnalyticsItem[]> {
  const query = new URLSearchParams()
  if (params?.hoursBack) query.set('hours_back', String(params.hoursBack))
  if (params?.includeSimulations !== undefined) query.set('include_simulations', String(params.includeSimulations))
  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiGet<CounterAnalyticsItem[]>(`/analytics/counters${qs}`)
}

export async function getRecentAuditEvents(limit: number = 50): Promise<ServiceEventLogItem[]> {
  return apiGet<ServiceEventLogItem[]>(`/analytics/events?limit=${limit}`)
}

export async function getOperationalDashboard(params?: {
  hoursBack?: number
  sessionId?: string
  includeSimulations?: boolean
  slaSeconds?: number
}): Promise<OperationalAnalyticsResponse> {
  const query = new URLSearchParams()
  if (params?.hoursBack) query.set('hours_back', String(params.hoursBack))
  if (params?.sessionId) query.set('session_id', params.sessionId)
  if (params?.includeSimulations !== undefined) query.set('include_simulations', String(params.includeSimulations))
  if (params?.slaSeconds) query.set('sla_seconds', String(params.slaSeconds))
  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiGet<OperationalAnalyticsResponse>(`/analytics/dashboard${qs}`)
}

/** Ask the AI Operations Agent */
export async function askAgent(params: {
  query: string
  language?: string
  sessionId?: string
}): Promise<AgentResponse> {
  return apiPost<AgentResponse>('/agent/ask', {
    query: params.query,
    language: params.language || 'en',
    session_id: params.sessionId || 'default',
  })
}

/** Get AI Agent capabilities and sample queries */
export async function getAgentCapabilities(): Promise<AgentCapabilitiesResponse> {
  return apiGet<AgentCapabilitiesResponse>('/agent/capabilities')
}

/** Process a spoken or typed natural language voice query */
export async function processVoiceQuery(payload: VoiceQueryRequest): Promise<VoiceQueryResponse> {
  return apiPost<VoiceQueryResponse>('/voice/query', payload)
}

/** Get standard multilingual announcement templates */
export async function getVoiceAnnouncements(): Promise<VoiceAnnouncementsResponse> {
  return apiGet<VoiceAnnouncementsResponse>('/voice/announcements')
}



