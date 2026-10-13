/**
 * QueueWise AI — Citizen Mobile Tracking Page
 *
 * Real-time queue tracker for citizens on mobile viewports.
 * Uses WebSockets for zero-refresh state updates, auditory announcements,
 * queue depth indicators, and cancellation controls.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getTokenStatus, cancelToken } from '../services/api'
import type { TokenPublicStatus, NotificationResponse, WebSocketMessage } from '../types/api'
import { useQueueWebSocket } from '../hooks/useQueueWebSocket'
import { useLanguage } from '../context/LanguageContext'
import { playCallChime, playApproachingAlert } from '../utils/audio'

export function TrackTokenPage() {
  const { publicId: routePublicId } = useParams<{ publicId?: string }>()
  const navigate = useNavigate()
  const { t, isRTL } = useLanguage()

  const [inputTokenId, setInputTokenId] = useState<string>('')
  const [token, setToken] = useState<TokenPublicStatus | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(Boolean(routePublicId))
  const [error, setError] = useState<string | null>(null)
  const [showCancelModal, setShowCancelModal] = useState<boolean>(false)
  const [isCancelling, setIsCancelling] = useState<boolean>(false)
  const [notifications, setNotifications] = useState<NotificationResponse[]>([])

  const prevStatusRef = useRef<string | null>(null)
  const prevPositionRef = useRef<number | null>(null)

  // Fetch token status by public ID
  const loadToken = useCallback(async (id: string) => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await getTokenStatus(id)
      setToken(data)
      prevStatusRef.current = data.status
      prevPositionRef.current = data.position_ahead
    } catch (err: any) {
      setError(t.tokenNotFound)
      setToken(null)
    } finally {
      setIsLoading(false)
    }
  }, [t.tokenNotFound])

  useEffect(() => {
    if (routePublicId) {
      loadToken(routePublicId)
    }
  }, [routePublicId, loadToken])

  // WebSocket real-time subscription
  const handleWsEvent = useCallback((msg: WebSocketMessage) => {
    // If our token status was pushed directly
    if (msg.event === 'NOTIFICATION' && msg.data) {
      const notif = msg.data as NotificationResponse
      setNotifications((prev) => [notif, ...prev])
    }

    // Refresh token state on any queue change event
    if (
      msg.event === 'TOKEN_CALLED' ||
      msg.event === 'TOKEN_SERVING' ||
      msg.event === 'TOKEN_COMPLETED' ||
      msg.event === 'TOKEN_SKIPPED' ||
      msg.event === 'TOKEN_RECALLED' ||
      msg.event === 'COUNTER_STATUS_CHANGED'
    ) {
      if (routePublicId) {
        // Fetch refreshed position and status
        getTokenStatus(routePublicId).then((updated) => {
          setToken((prev) => {
            if (!prev) return updated

            // Check if status transitioned to CALLED
            if (prev.status !== 'CALLED' && updated.status === 'CALLED') {
              playCallChime()
            }

            // Check if position dropped to approaching threshold (<= 2)
            if (prev.position_ahead > 2 && updated.position_ahead <= 2 && updated.status === 'WAITING') {
              playApproachingAlert()
            }

            return updated
          })
        }).catch(() => {})
      }
    }
  }, [routePublicId])

  const { isConnected } = useQueueWebSocket({
    tokenPublicId: routePublicId,
    onMessage: handleWsEvent,
  })

  // Check state transitions on token changes
  useEffect(() => {
    if (!token) return

    if (prevStatusRef.current !== token.status) {
      if (token.status === 'CALLED') {
        playCallChime()
      }
      prevStatusRef.current = token.status
    }

    if (prevPositionRef.current !== null && prevPositionRef.current > 2 && token.position_ahead <= 2 && token.status === 'WAITING') {
      playApproachingAlert()
    }
    prevPositionRef.current = token.position_ahead
  }, [token])

  const handleLookup = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputTokenId.trim()) return
    navigate(`/track/${inputTokenId.trim()}`)
  }

  const handleConfirmCancel = async () => {
    if (!token) return
    try {
      setIsCancelling(true)
      await cancelToken(token.public_id, 'Citizen requested cancellation')
      setShowCancelModal(false)
      await loadToken(token.public_id)
    } catch (err: any) {
      setError(err.message || 'Failed to cancel token')
    } finally {
      setIsCancelling(false)
    }
  }

  const formatWaitMinutes = (seconds: number) => {
    const mins = Math.ceil(seconds / 60)
    return mins <= 1 ? '1 min' : `${mins} mins`
  }

  return (
    <div className={`max-w-md mx-auto px-4 py-6 sm:py-10 ${isRTL ? 'font-urdu' : ''}`}>
      {/* Search Bar if no token or user wants to switch */}
      {!routePublicId && (
        <div className="glass-card p-6 text-center animate-fade-in">
          <div className="w-12 h-12 mx-auto rounded-2xl bg-gradient-to-tr from-accent-500 to-primary-500 flex items-center justify-center text-white mb-4 shadow-lg shadow-accent-500/20">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-white mb-2">{t.trackTitle}</h1>
          <p className="text-xs text-surface-200/70 mb-5">{t.enterTokenPrompt}</p>

          <form onSubmit={handleLookup} className="space-y-3">
            <input
              type="text"
              value={inputTokenId}
              onChange={(e) => setInputTokenId(e.target.value)}
              placeholder="e.g. N7qK48bW8... or GEN-001"
              className="w-full px-4 py-3 rounded-xl bg-surface-900 border border-white/10 text-white placeholder-surface-200/30 text-center font-mono tracking-wider focus:border-accent-500 focus:outline-none"
              required
            />
            <button
              type="submit"
              className="w-full py-3 rounded-xl btn-accent font-bold text-sm shadow-lg shadow-accent-500/20 cursor-pointer"
            >
              {t.lookupBtn}
            </button>
          </form>
        </div>
      )}

      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="w-10 h-10 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-surface-200/60">Connecting to live queue stream...</p>
        </div>
      )}

      {error && (
        <div className="p-5 glass-card border border-danger-500/30 text-center animate-fade-in">
          <div className="w-10 h-10 mx-auto rounded-full bg-danger-500/20 flex items-center justify-center text-danger-400 mb-3">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <p className="text-sm text-danger-300 font-medium mb-4">{error}</p>
          <button
            onClick={() => navigate('/kiosk')}
            className="btn-primary text-xs py-2 px-4 rounded-xl cursor-pointer"
          >
            {t.tokenLo}
          </button>
        </div>
      )}

      {/* Active Token Tracker Card */}
      {token && !isLoading && (
        <div className="space-y-4 animate-fade-in">
          {/* Real-time Connection Indicator */}
          <div className="flex items-center justify-between text-xs px-2">
            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  isConnected ? 'bg-success-400 animate-pulse' : 'bg-warning-400'
                }`}
              />
              <span className="text-surface-200/60 font-medium">
                {isConnected ? 'Live WebSocket Active' : 'Connecting to Stream...'}
              </span>
            </div>
            <span className="text-surface-200/40 text-[11px] font-mono dir-ltr">
              ID: {token.public_id.substring(0, 8)}...
            </span>
          </div>

          {/* Status Banners */}
          {token.status === 'CALLED' && (
            <div className="p-6 rounded-3xl bg-gradient-to-r from-success-600 via-emerald-500 to-teal-500 text-white shadow-2xl shadow-success-500/30 animate-pulse text-center">
              <div className="text-3xl mb-1">🎉</div>
              <h2 className="text-2xl font-black tracking-tight">{t.statusCalled}</h2>
              <p className="text-sm font-medium mt-1 opacity-90">{t.statusCalledDesc}</p>
              <div className="mt-4 inline-block bg-black/25 px-5 py-2.5 rounded-2xl border border-white/20">
                <span className="text-xs uppercase tracking-wider text-emerald-100 block">
                  {t.calledTo}
                </span>
                <span className="text-2xl font-black text-white">
                  {token.called_counter_name || t.counter}
                </span>
              </div>
            </div>
          )}

          {token.status === 'SERVING' && (
            <div className="p-5 rounded-2xl bg-gradient-to-r from-primary-600 to-accent-600 text-white shadow-xl shadow-primary-500/25 text-center">
              <h2 className="text-xl font-bold">{t.statusServing}</h2>
              <p className="text-xs text-primary-100 mt-1">{t.statusServingDesc}</p>
              {token.called_counter_name && (
                <div className="mt-2 text-sm font-semibold text-white">
                  @ {token.called_counter_name}
                </div>
              )}
            </div>
          )}

          {token.status === 'WAITING' && token.position_ahead <= 2 && (
            <div className="p-4 rounded-2xl bg-amber-500/20 border border-amber-500/40 text-amber-300 text-center flex items-center justify-center gap-3 animate-pulse">
              <span className="text-xl">🔔</span>
              <div className="text-left text-xs font-semibold">
                <div>{t.statusApproaching}</div>
                <div className="text-amber-200/80 font-normal">{t.statusApproachingDesc}</div>
              </div>
            </div>
          )}

          {token.status === 'COMPLETED' && (
            <div className="p-5 rounded-2xl bg-surface-900 border border-success-500/40 text-center">
              <div className="w-10 h-10 mx-auto rounded-full bg-success-500/20 text-success-400 flex items-center justify-center mb-2">
                ✓
              </div>
              <h2 className="text-lg font-bold text-white">{t.statusCompleted}</h2>
              <p className="text-xs text-surface-200/60 mt-1">{t.statusCompletedDesc}</p>
            </div>
          )}

          {token.status === 'SKIPPED' && (
            <div className="p-5 rounded-2xl bg-surface-900 border border-warning-500/40 text-center">
              <div className="w-10 h-10 mx-auto rounded-full bg-warning-500/20 text-warning-400 flex items-center justify-center mb-2">
                ⚠️
              </div>
              <h2 className="text-lg font-bold text-white">{t.statusSkipped}</h2>
              <p className="text-xs text-surface-200/60 mt-1">{t.statusSkippedDesc}</p>
            </div>
          )}

          {token.status === 'CANCELLED' && (
            <div className="p-5 rounded-2xl bg-surface-900 border border-danger-500/30 text-center">
              <h2 className="text-lg font-bold text-danger-400">{t.statusCancelled}</h2>
              <p className="text-xs text-surface-200/60 mt-1">{t.statusCancelledDesc}</p>
            </div>
          )}

          {/* Main Token Info Card */}
          <div className="glass-card p-6 text-center shadow-xl">
            <span className="text-xs font-bold uppercase tracking-wider text-accent-400 bg-accent-500/10 px-3 py-1 rounded-full">
              {token.service_name}
            </span>

            {/* Giant Token Number */}
            <div className="my-6">
              <div className="text-5xl sm:text-6xl font-black tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-white via-primary-200 to-accent-300 dir-ltr inline-block">
                {token.display_number}
              </div>
            </div>

            {/* Live Metrics Row (for WAITING state) */}
            {token.status === 'WAITING' && (
              <div className="grid grid-cols-2 gap-3 pt-4 border-t border-white/10">
                <div className="bg-surface-950/60 rounded-xl p-3 border border-white/5">
                  <div className="text-[11px] text-surface-200/60 font-medium mb-1">
                    {t.peopleAhead}
                  </div>
                  <div className="text-2xl font-black text-white">
                    {token.position_ahead}
                  </div>
                </div>

                <div className="bg-surface-950/60 rounded-xl p-3 border border-white/5">
                  <div className="text-[11px] text-surface-200/60 font-medium mb-1">
                    {t.estTimeRemaining}
                  </div>
                  <div className="text-2xl font-black text-accent-400">
                    {formatWaitMinutes(token.estimated_wait_seconds)}
                  </div>
                </div>
              </div>
            )}

            {/* Waiting Queue Visual Progress Bar */}
            {token.status === 'WAITING' && (
              <div className="mt-5 text-left">
                <div className="flex justify-between text-[11px] text-surface-200/50 mb-1.5">
                  <span>Queue Progress</span>
                  <span>{token.position_ahead === 0 ? 'Next in Line!' : `${token.position_ahead} ahead`}</span>
                </div>
                <div className="w-full h-2.5 rounded-full bg-surface-950 overflow-hidden border border-white/5">
                  <div
                    className="h-full bg-gradient-to-r from-primary-500 to-accent-400 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.max(10, 100 - token.position_ahead * 15)}%`,
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Action Row */}
          {token.status === 'WAITING' && (
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setShowCancelModal(true)}
                className="w-full py-3 px-4 rounded-xl border border-danger-500/20 bg-danger-500/10 hover:bg-danger-500/20 text-danger-400 text-xs font-semibold transition-colors flex items-center justify-center gap-2 cursor-pointer"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span>{t.cancelToken}</span>
              </button>
            </div>
          )}

          {/* Issue Another Token Link */}
          {(token.status === 'COMPLETED' || token.status === 'CANCELLED' || token.status === 'SKIPPED') && (
            <button
              onClick={() => navigate('/kiosk')}
              className="w-full py-3.5 px-4 rounded-xl btn-primary text-sm font-bold shadow-lg shadow-primary-500/20 cursor-pointer"
            >
              {t.tokenLo}
            </button>
          )}

          {/* Real-time Notifications Log Drawer */}
          {notifications.length > 0 && (
            <div className="glass-card p-4 mt-6">
              <h3 className="text-xs font-bold text-surface-200/80 uppercase tracking-wider mb-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-accent-400" />
                {t.notificationsTitle}
              </h3>
              <div className="space-y-2">
                {notifications.map((notif) => (
                  <div
                    key={notif.id}
                    className="p-3 rounded-xl bg-surface-950/70 border border-white/5 text-xs text-left"
                  >
                    <div className="font-semibold text-white">{notif.title}</div>
                    <div className="text-surface-200/70 text-[11px] mt-0.5">{notif.message}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Cancellation Confirmation Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-surface-900 border border-white/10 rounded-2xl max-w-sm w-full p-6 text-center shadow-2xl">
            <div className="w-12 h-12 mx-auto rounded-full bg-danger-500/20 text-danger-400 flex items-center justify-center mb-4">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-white mb-2">{t.cancelConfirmTitle}</h3>
            <p className="text-xs text-surface-200/70 mb-6">{t.cancelConfirmDesc}</p>

            <div className="space-y-2">
              <button
                type="button"
                onClick={handleConfirmCancel}
                disabled={isCancelling}
                className="w-full py-3 rounded-xl bg-danger-600 hover:bg-danger-500 text-white font-bold text-xs transition-colors cursor-pointer"
              >
                {isCancelling ? 'Cancelling...' : t.confirmCancelBtn}
              </button>
              <button
                type="button"
                onClick={() => setShowCancelModal(false)}
                className="w-full py-2.5 rounded-xl text-surface-200/70 hover:text-white text-xs font-semibold cursor-pointer"
              >
                {t.keepTokenBtn}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
