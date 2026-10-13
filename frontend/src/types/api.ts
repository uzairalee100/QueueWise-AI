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

/** Counter representation */
export interface Counter {
  id: string
  name: string
  status: CounterStatus
  assigned_operator_id?: string | null
  current_token_id?: string | null
  status_changed_at: string
  created_at: string
  supported_services: ServiceCategory[]
}

/** API error response */
export interface ApiError {
  detail: string
  status_code?: number
}
