/**
 * QueueWise AI — useQueueWebSocket Hook
 *
 * React hook for consuming real-time WebSocket events and notifications.
 * Automatically synchronizes connection state and unsubscribes on unmount.
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { QueueWebSocketClient } from '../services/websocket'
import type { WebSocketMessage, NotificationResponse } from '../types/api'
import { getNotifications } from '../services/api'

interface UseQueueWebSocketOptions {
  sessionId?: string
  tokenPublicId?: string
  counterId?: string
  onMessage?: (message: WebSocketMessage) => void
  onNotification?: (notification: NotificationResponse) => void
  onTokenStatusChange?: (data: any) => void
  onCounterStatusChange?: (data: any) => void
}

export function useQueueWebSocket({
  sessionId = 'default',
  tokenPublicId,
  counterId,
  onMessage,
  onNotification,
  onTokenStatusChange,
  onCounterStatusChange,
}: UseQueueWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [notifications, setNotifications] = useState<NotificationResponse[]>([])
  const clientRef = useRef<QueueWebSocketClient | null>(null)

  // Fetch initial notifications if tokenPublicId is provided
  const loadNotifications = useCallback(async () => {
    if (!tokenPublicId) return
    try {
      const data = await getNotifications(tokenPublicId)
      setNotifications(data)
    } catch {
      // ignore
    }
  }, [tokenPublicId])

  useEffect(() => {
    loadNotifications()
  }, [loadNotifications])

  useEffect(() => {
    const client = new QueueWebSocketClient({
      sessionId,
      tokenPublicId,
      counterId,
    })
    clientRef.current = client

    const unbindConn = client.onConnectionChange((connected) => {
      setIsConnected(connected)
    })

    const unbindAll = client.on('*', (msg) => {
      setLastMessage(msg)
      onMessage?.(msg)

      if (msg.event === 'NOTIFICATION' && msg.data) {
        const notif = msg.data as NotificationResponse
        setNotifications((prev) => [notif, ...prev])
        onNotification?.(notif)
      }

      if (
        (msg.event === 'TOKEN_CREATED' ||
          msg.event === 'TOKEN_CALLED' ||
          msg.event === 'TOKEN_SERVING' ||
          msg.event === 'TOKEN_COMPLETED' ||
          msg.event === 'TOKEN_SKIPPED' ||
          msg.event === 'TOKEN_RECALLED' ||
          msg.event === 'TOKEN_CANCELLED') &&
        msg.data
      ) {
        onTokenStatusChange?.(msg.data)
      }

      if (msg.event === 'COUNTER_STATUS_CHANGED' && msg.data) {
        onCounterStatusChange?.(msg.data)
      }
    })

    client.connect()

    return () => {
      unbindConn()
      unbindAll()
      client.disconnect()
      clientRef.current = null
    }
  }, [sessionId, tokenPublicId, counterId, onMessage, onNotification, onTokenStatusChange, onCounterStatusChange])

  return {
    isConnected,
    lastMessage,
    notifications,
    refreshNotifications: loadNotifications,
    sendMessage: (payload: Record<string, unknown>) => clientRef.current?.send(payload),
  }
}
