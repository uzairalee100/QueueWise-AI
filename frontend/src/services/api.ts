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
  Counter,
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
