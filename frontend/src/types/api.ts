/**
 * QueueWise AI — Shared API types
 *
 * Type definitions for API responses and common data structures.
 * Synchronized with backend schemas.
 */

/** Health check response */
export interface HealthResponse {
  status: 'healthy' | 'unhealthy'
  app: string
  version: string
  environment: string
}

/** API status response */
export interface ApiStatusResponse {
  api_version: string
  status: string
}

/** Token status enum — mirrors backend state machine */
export type TokenStatus =
  | 'WAITING'
  | 'CALLED'
  | 'SERVING'
  | 'COMPLETED'
  | 'SKIPPED'
  | 'CANCELLED'

/** Counter status enum */
export type CounterStatus =
  | 'OPEN_IDLE'
  | 'OPEN_SERVING'
  | 'PAUSED'
  | 'CLOSED'

/** Service Category */
export interface ServiceCategory {
  id: string
  name: string
  code: string
  description?: string | null
  default_duration_seconds: number
  priority_policy: string
  is_active: boolean
  created_at: string
}

/** Citizen Token Public Status */
export interface TokenPublicStatus {
  public_id: string
  display_number: string
  status: TokenStatus
  service_name: string
  service_code: string
  position_ahead: number
  estimated_wait_seconds: number
  active_counters?: number
  is_stalled?: boolean
  called_counter_name?: string | null
  created_at: string
  called_at?: string | null
  session_id: string
}

/** Token creation request */
export interface TokenCreateRequest {
  service_id?: string
  service_code?: string
  session_id?: string
  contact_info?: string
  idempotency_key?: string
  priority?: number
}

/** Full Staff Token Response */
export interface TokenResponse {
  id: string
  public_id: string
  display_number: string
  service_category_id: string
  session_id: string
  status: TokenStatus
  priority: number
  idempotency_key?: string | null
  contact_info?: string | null
  called_counter_id?: string | null
  created_at: string
  called_at?: string | null
  service_started_at?: string | null
  completed_at?: string | null
  cancelled_at?: string | null
  service_category?: ServiceCategory | null
}

/** Counter representation */
export interface Counter {
  id: string
  name: string
  status: CounterStatus
  assigned_operator_id?: string | null
  current_token_id?: string | null
  current_token_display_number?: string | null
  current_token?: TokenResponse | null
  status_changed_at: string
  created_at: string
  supported_services: ServiceCategory[]
}

/** Counter creation payload */
export interface CounterCreatePayload {
  name: string
  supported_service_ids?: string[]
}

/** Counter service assignment payload */
export interface CounterAssignServicesPayload {
  supported_service_ids: string[]
}

/** Currently serving token details at a counter */
export interface ServingTokenInfo {
  counter_id: string
  counter_name: string
  token_id: string
  token_display_number: string
  service_started_at?: string | null
  duration_seconds?: number | null
}

/** Operational summary item for a service */
export interface QueueSummaryItem {
  service_id: string
  service_name: string
  service_code: string
  waiting_count: number
  serving_count: number
  completed_count: number
  skipped_count: number
  cancelled_count: number
  active_counters: number
  total_counters: number
  avg_service_duration_seconds: number
  estimated_wait_for_next_arrival: number
  is_stalled: boolean
  queue_status: 'NORMAL' | 'BUSY' | 'CONGESTED' | 'STALLED'
  next_token_display_number?: string | null
  currently_serving: ServingTokenInfo[]
}

/** System-wide queue status response */
export interface QueueSummaryResponse {
  session_id: string
  timestamp: string
  total_waiting: number
  total_serving: number
  total_active_counters: number
  services: QueueSummaryItem[]
}

/** Prospective wait estimation breakdown */
export interface WaitEstimateDetail {
  service_id: string
  service_name: string
  service_code: string
  position_ahead: number
  active_counters: number
  avg_service_duration_seconds: number
  estimated_wait_seconds: number
  estimated_wait_minutes: number
  is_stalled: boolean
  calculation_basis: string
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW'
  status_message: string
}

/** Notification Types */
export type NotificationType =
  | 'CREATED'
  | 'APPROACHING'
  | 'CALLED'
  | 'SKIPPED'
  | 'COMPLETED'

export type NotificationChannel = 'IN_APP' | 'BROWSER' | 'SMS'
export type NotificationStatus = 'PENDING' | 'SENT' | 'FAILED'

export interface NotificationResponse {
  id: string
  token_id: string
  type: NotificationType
  channel: NotificationChannel
  status: NotificationStatus
  title?: string | null
  message: string
  created_at: string
  sent_at?: string | null
  retry_count: number
}

/** WebSocket Real-Time Event Message */
export interface WebSocketMessage<T = unknown> {
  event: string
  data?: T
  timestamp?: string
  session_id?: string
  token_public_id?: string
  counter_id?: string
  message?: string
}

/** API error response */
export interface ApiError {
  detail: string
  status_code?: number
}
