/**
 * QueueWise AI — WebSocket Client
 *
 * Real-time event streaming service with automatic reconnection,
 * heartbeat management, and subscription handling.
 */
import type { WebSocketMessage } from '../types/api'

export type MessageHandler<T = unknown> = (data: WebSocketMessage<T>) => void

export interface WebSocketOptions {
  sessionId?: string
  tokenPublicId?: string
  counterId?: string
  autoReconnect?: boolean
  maxReconnectAttempts?: number
  heartbeatIntervalMs?: number
}

export class QueueWebSocketClient {
  private ws: WebSocket | null = null
  private options: WebSocketOptions
  private handlers: Map<string, Set<MessageHandler<any>>> = new Map()
  private reconnectAttempts = 0
  private reconnectTimer: number | null = null
  private heartbeatTimer: number | null = null
  private isExplicitlyClosed = false
  private connectionListeners: Set<(connected: boolean) => void> = new Set()

  constructor(options: WebSocketOptions = {}) {
    this.options = {
      sessionId: 'default',
      autoReconnect: true,
      maxReconnectAttempts: 10,
      heartbeatIntervalMs: 25000,
      ...options,
    }
  }

  /** Build WebSocket URL matching current host and protocol */
  private buildUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const params = new URLSearchParams()

    if (this.options.sessionId) {
      params.set('session_id', this.options.sessionId)
    }
    if (this.options.tokenPublicId) {
      params.set('token_public_id', this.options.tokenPublicId)
    }
    if (this.options.counterId) {
      params.set('counter_id', this.options.counterId)
    }

    const query = params.toString() ? `?${params.toString()}` : ''
    return `${protocol}//${host}/ws/live${query}`
  }

  /** Connect to the WebSocket server */
  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.isExplicitlyClosed = false
    const url = this.buildUrl()

    try {
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        this.reconnectAttempts = 0
        this.notifyConnectionState(true)
        this.startHeartbeat()
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          this.handleIncomingMessage(message)
        } catch {
          // ignore non-json messages
        }
      }

      this.ws.onclose = () => {
        this.stopHeartbeat()
        this.notifyConnectionState(false)
        if (!this.isExplicitlyClosed && this.options.autoReconnect) {
          this.scheduleReconnect()
        }
      }

      this.ws.onerror = () => {
        // ws.onclose will be called after onerror
      }
    } catch {
      if (!this.isExplicitlyClosed && this.options.autoReconnect) {
        this.scheduleReconnect()
      }
    }
  }

  /** Subscribe to a specific event or '*' for all events */
  public on<T = unknown>(event: string, handler: MessageHandler<T>): () => void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set())
    }
    this.handlers.get(event)!.add(handler as MessageHandler<any>)

    // Return unbind function
    return () => {
      this.handlers.get(event)?.delete(handler as MessageHandler<any>)
    }
  }

  /** Subscribe to connection status changes */
  public onConnectionChange(listener: (connected: boolean) => void): () => void {
    this.connectionListeners.add(listener)
    listener(this.isConnected())
    return () => {
      this.connectionListeners.delete(listener)
    }
  }

  /** Send message / command over the WebSocket */
  public send(payload: Record<string, unknown>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload))
    }
  }

  /** Update target subscription parameters */
  public updateSubscription(tokenPublicId?: string, counterId?: string): void {
    this.options.tokenPublicId = tokenPublicId
    this.options.counterId = counterId
    // Reconnect with new query parameters
    this.disconnect()
    this.connect()
  }

  /** Disconnect and stop reconnection */
  public disconnect(): void {
    this.isExplicitlyClosed = true
    this.stopHeartbeat()
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.notifyConnectionState(false)
  }

  /** Connection state check */
  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  private handleIncomingMessage(message: WebSocketMessage): void {
    // Respond to server ping if any
    if (message.event === 'PING') {
      this.send({ event: 'PONG' })
      return
    }

    // Trigger specific listeners
    const specificHandlers = this.handlers.get(message.event)
    if (specificHandlers) {
      specificHandlers.forEach((handler) => {
        try {
          handler(message)
        } catch (e) {
          console.error(`Error in handler for ${message.event}:`, e)
        }
      })
    }

    // Trigger wildcard listeners
    const wildcardHandlers = this.handlers.get('*')
    if (wildcardHandlers) {
      wildcardHandlers.forEach((handler) => {
        try {
          handler(message)
        } catch (e) {
          console.error('Error in wildcard WebSocket handler:', e)
        }
      })
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= (this.options.maxReconnectAttempts || 10)) {
      return
    }
    this.reconnectAttempts++
    // Exponential backoff capped at 15 seconds
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 15000)

    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer)
    }

    this.reconnectTimer = window.setTimeout(() => {
      if (!this.isExplicitlyClosed) {
        this.connect()
      }
    }, delay)
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => {
      if (this.isConnected()) {
        this.send({ event: 'PING' })
      }
    }, this.options.heartbeatIntervalMs || 25000)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      window.clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private notifyConnectionState(connected: boolean): void {
    this.connectionListeners.forEach((listener) => {
      try {
        listener(connected)
      } catch (e) {
        console.error('Error in connection listener:', e)
      }
    })
  }
}
