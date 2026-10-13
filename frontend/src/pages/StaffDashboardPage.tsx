/**
 * QueueWise AI — Staff Counter Operations Dashboard
 *
 * Full-featured operator control desk enabling counter management,
 * token calling/serving/completing/skipping, live waiting queue,
 * and real-time WebSocket event feed. Supports bilingual UI (en/ur).
 *
 * Milestone 6: Staff Dashboard & Real-Time Operations
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useLanguage } from '../context/LanguageContext'
import { useQueueWebSocket } from '../hooks/useQueueWebSocket'
import type { Counter, TokenPublicStatus, ServiceCategory } from '../types/api'
import {
  getCounters,
  getCounter,
  getServices,
  getWaitingTokens,
  callNextToken,
  startServingToken,
  completeServingToken,
  skipToken,
  recallToken,
  openCounter,
  pauseCounter,
  resumeCounter,
  closeCounter,
  createCounter,
  updateCounterServices,
} from '../services/api'

/* ─── Types ────────────────────────────────────────────────────── */

interface EventLogEntry {
  id: string
  event: string
  message: string
  timestamp: Date
}

/* ─── Utility: Human-friendly elapsed time ─────────────────────── */

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return s > 0 ? `${m}m ${s}s` : `${m}m`
}

function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

/* ─── Counter Status UI config ─────────────────────────────────── */

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; dot: string }> = {
  OPEN_IDLE: { label: 'Open — Idle', color: 'text-success-400', bg: 'bg-success-400/10', dot: 'bg-success-400' },
  OPEN_SERVING: { label: 'Open — Serving', color: 'text-accent-400', bg: 'bg-accent-400/10', dot: 'bg-accent-400 animate-pulse' },
  PAUSED: { label: 'Paused', color: 'text-warning-400', bg: 'bg-warning-400/10', dot: 'bg-warning-400' },
  CLOSED: { label: 'Closed', color: 'text-surface-200/50', bg: 'bg-surface-200/5', dot: 'bg-surface-200/40' },
}

/* ─── Token Status badge ───────────────────────────────────────── */

function TokenStatusBadge({ status }: { status: string }) {
  const config: Record<string, { text: string; cls: string }> = {
    WAITING: { text: 'Waiting', cls: 'bg-warning-400/15 text-warning-400' },
    CALLED: { text: 'Called', cls: 'bg-primary-400/15 text-primary-400 animate-pulse' },
    SERVING: { text: 'Serving', cls: 'bg-accent-400/15 text-accent-400' },
    COMPLETED: { text: 'Done', cls: 'bg-success-400/15 text-success-400' },
    SKIPPED: { text: 'Skipped', cls: 'bg-surface-200/15 text-surface-200' },
    CANCELLED: { text: 'Cancelled', cls: 'bg-danger-400/15 text-danger-400' },
  }
  const c = config[status] || { text: status, cls: 'bg-white/10 text-white/70' }
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${c.cls}`}>
      {c.text}
    </span>
  )
}

/* ─── Main Component ───────────────────────────────────────────── */

export function StaffDashboardPage() {
  const { t } = useLanguage()

  // Data state
  const [counters, setCounters] = useState<Counter[]>([])
  const [services, setServices] = useState<ServiceCategory[]>([])
  const [selectedCounterId, setSelectedCounterId] = useState<string | null>(null)
  const [selectedCounter, setSelectedCounter] = useState<Counter | null>(null)
  const [waitingQueue, setWaitingQueue] = useState<TokenPublicStatus[]>([])

  // Action state
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [successFlash, setSuccessFlash] = useState<string | null>(null)

  // Service duration timer
  const [serviceDuration, setServiceDuration] = useState(0)
  const timerRef = useRef<number | null>(null)

  // Event log
  const [eventLog, setEventLog] = useState<EventLogEntry[]>([])
  const logIdRef = useRef(0)

  // Settings panel
  const [showSettings, setShowSettings] = useState(false)
  const [selectedServiceIds, setSelectedServiceIds] = useState<string[]>([])
  const [newCounterName, setNewCounterName] = useState('')
  const [creatingCounter, setCreatingCounter] = useState(false)

  // ── Derived state ─────────────────────────────────────────
  const counterStatus = selectedCounter?.status || 'CLOSED'
  const activeToken = selectedCounter?.current_token || null
  const isIdle = counterStatus === 'OPEN_IDLE'
  const isServing = counterStatus === 'OPEN_SERVING'
  const isPaused = counterStatus === 'PAUSED'
  const isClosed = counterStatus === 'CLOSED'
  const canCallNext = (isIdle || (isServing && !activeToken)) && !actionLoading
  const canStartServing = isServing && activeToken?.status === 'CALLED' && !actionLoading
  const canComplete = isServing && (activeToken?.status === 'SERVING' || activeToken?.status === 'CALLED') && !actionLoading
  const canSkip = isServing && activeToken && !actionLoading
  const canRecall = isServing && activeToken?.status === 'CALLED' && !actionLoading

  // ── Logging helper ────────────────────────────────────────
  const addLog = useCallback((event: string, message: string) => {
    logIdRef.current++
    setEventLog((prev) => [
      { id: `log-${logIdRef.current}`, event, message, timestamp: new Date() },
      ...prev.slice(0, 49), // keep last 50 entries
    ])
  }, [])

  // ── Flash helper ──────────────────────────────────────────
  const flash = useCallback((msg: string) => {
    setSuccessFlash(msg)
    setTimeout(() => setSuccessFlash(null), 3000)
  }, [])

  // ── Load counters and services ────────────────────────────
  const loadCounters = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([getCounters(), getServices()])
      setCounters(c)
      setServices(s)
    } catch (e: any) {
      setError(e.detail || 'Failed to load counters')
    }
  }, [])

  useEffect(() => {
    loadCounters()
  }, [loadCounters])

  // ── Load selected counter + waiting queue ─────────────────
  const refreshSelectedCounter = useCallback(async () => {
    if (!selectedCounterId) return
    try {
      const counter = await getCounter(selectedCounterId)
      setSelectedCounter(counter)

      // Load waiting tokens for the counter's supported services
      const allWaiting: TokenPublicStatus[] = []
      for (const svc of counter.supported_services) {
        const tokens = await getWaitingTokens(svc.id)
        allWaiting.push(...tokens)
      }

      // De-duplicate and sort
      const seen = new Set<string>()
      const unique = allWaiting.filter((t) => {
        if (seen.has(t.public_id)) return false
        seen.add(t.public_id)
        return true
      })
      unique.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      setWaitingQueue(unique)
    } catch (e: any) {
      setError(e.detail || 'Failed to refresh counter')
    }
  }, [selectedCounterId])

  useEffect(() => {
    refreshSelectedCounter()
  }, [refreshSelectedCounter])

  // ── Service duration timer ────────────────────────────────
  useEffect(() => {
    if (activeToken?.status === 'SERVING' && activeToken?.service_started_at) {
      const startTime = new Date(activeToken.service_started_at).getTime()
      const tick = () => {
        setServiceDuration(Math.floor((Date.now() - startTime) / 1000))
      }
      tick()
      timerRef.current = window.setInterval(tick, 1000)
      return () => {
        if (timerRef.current) window.clearInterval(timerRef.current)
      }
    } else {
      setServiceDuration(0)
      if (timerRef.current) window.clearInterval(timerRef.current)
    }
  }, [activeToken?.status, activeToken?.service_started_at])

  // ── WebSocket real-time events ────────────────────────────
  const wsCallbacks = useMemo(() => ({
    onTokenStatusChange: (data: any) => {
      addLog(data.status || 'TOKEN_EVENT', `${data.display_number || data.public_id} → ${data.status || 'updated'}`)
      refreshSelectedCounter()
      loadCounters()
    },
    onCounterStatusChange: (data: any) => {
      addLog('COUNTER', `${data.counter_name}: ${data.old_status} → ${data.status}`)
      refreshSelectedCounter()
      loadCounters()
    },
  }), [addLog, refreshSelectedCounter, loadCounters])

  const { isConnected } = useQueueWebSocket({
    counterId: selectedCounterId || undefined,
    ...wsCallbacks,
  })

  // ── Counter Action Handlers ───────────────────────────────
  const handleSelectCounter = (id: string) => {
    setSelectedCounterId(id)
    setError(null)
    setSuccessFlash(null)
    setEventLog([])
    addLog('INFO', 'Counter selected — ready to operate')
  }

  const handleCallNext = async () => {
    if (!selectedCounterId) return
    setActionLoading('call')
    setError(null)
    try {
      const token = await callNextToken(selectedCounterId)
      if (token) {
        flash(`Called ${token.display_number}`)
        addLog('CALLED', `${token.display_number} called to counter`)
      } else {
        flash('No waiting tokens')
        addLog('INFO', 'No tokens waiting in queue')
      }
      await refreshSelectedCounter()
      await loadCounters()
    } catch (e: any) {
      setError(e.detail || 'Failed to call next token')
    } finally {
      setActionLoading(null)
    }
  }

  const handleStartServing = async () => {
    if (!selectedCounterId) return
    setActionLoading('serve')
    setError(null)
    try {
      const token = await startServingToken(selectedCounterId)
      flash(`Serving ${token.display_number}`)
      addLog('SERVING', `${token.display_number} — service started`)
      await refreshSelectedCounter()
    } catch (e: any) {
      setError(e.detail || 'Failed to start serving')
    } finally {
      setActionLoading(null)
    }
  }

  const handleComplete = async () => {
    if (!selectedCounterId) return
    setActionLoading('complete')
    setError(null)
    try {
      const token = await completeServingToken(selectedCounterId)
      flash(`Completed ${token.display_number} (${formatElapsed(serviceDuration)})`)
      addLog('COMPLETED', `${token.display_number} — service completed in ${formatElapsed(serviceDuration)}`)
      await refreshSelectedCounter()
      await loadCounters()
    } catch (e: any) {
      setError(e.detail || 'Failed to complete service')
    } finally {
      setActionLoading(null)
    }
  }

  const handleSkip = async () => {
    if (!selectedCounterId) return
    setActionLoading('skip')
    setError(null)
    try {
      const token = await skipToken(selectedCounterId)
      flash(`Skipped ${token.display_number}`)
      addLog('SKIPPED', `${token.display_number} — no-show, skipped`)
      await refreshSelectedCounter()
      await loadCounters()
    } catch (e: any) {
      setError(e.detail || 'Failed to skip token')
    } finally {
      setActionLoading(null)
    }
  }

  const handleRecall = async () => {
    if (!selectedCounterId) return
    setActionLoading('recall')
    setError(null)
    try {
      const token = await recallToken(selectedCounterId)
      flash(`Recalled ${token.display_number}`)
      addLog('RECALLED', `${token.display_number} — returned to waiting queue`)
      await refreshSelectedCounter()
      await loadCounters()
    } catch (e: any) {
      setError(e.detail || 'Failed to recall token')
    } finally {
      setActionLoading(null)
    }
  }

  // ── Counter Status Controls ───────────────────────────────
  const handleOpenCounter = async () => {
    if (!selectedCounterId) return
    setActionLoading('open')
    try {
      await openCounter(selectedCounterId)
      flash('Counter opened')
      addLog('COUNTER', 'Counter opened for service')
      await refreshSelectedCounter()
      await loadCounters()
    } catch (e: any) {
      setError(e.detail || 'Failed to open counter')
    } finally {
      setActionLoading(null)
    }
  }

  const handlePauseCounter = async () => {
    if (!selectedCounterId) return
    setActionLoading('pause')
    try {
      await pauseCounter(selectedCounterId)
      flash('Counter paused')
      addLog('COUNTER', 'Counter paused (break)')
      await refreshSelectedCounter()
      await loadCounters()
    } catch (e: any) {
      setError(e.detail || 'Failed to pause counter')
    } finally {
      setActionLoading(null)
    }
  }

  const handleResumeCounter = async () => {
    if (!selectedCounterId) return
    setActionLoading('resume')
    try {
      await resumeCounter(selectedCounterId)
      flash('Counter resumed')
      addLog('COUNTER', 'Counter resumed operations')
      await refreshSelectedCounter()
      await loadCounters()
    } catch (e: any) {
      setError(e.detail || 'Failed to resume counter')
    } finally {
      setActionLoading(null)
    }
  }

  const handleCloseCounter = async () => {
    if (!selectedCounterId) return
    setActionLoading('close')
    try {
      await closeCounter(selectedCounterId)
      flash('Counter closed')
      addLog('COUNTER', 'Counter closed')
      await refreshSelectedCounter()
      await loadCounters()
    } catch (e: any) {
      setError(e.detail || 'Failed to close counter')
    } finally {
      setActionLoading(null)
    }
  }

  // ── Settings: Services & Create Counter ──────────────────
  const handleSaveServices = async () => {
    if (!selectedCounterId) return
    setActionLoading('services')
    try {
      await updateCounterServices(selectedCounterId, selectedServiceIds)
      flash('Services updated')
      addLog('CONFIG', 'Counter services reconfigured')
      await refreshSelectedCounter()
      await loadCounters()
    } catch (e: any) {
      setError(e.detail || 'Failed to update services')
    } finally {
      setActionLoading(null)
    }
  }

  const handleCreateCounter = async () => {
    if (!newCounterName.trim()) return
    setCreatingCounter(true)
    try {
      const c = await createCounter({ name: newCounterName.trim() })
      flash(`Counter "${c.name}" created`)
      addLog('CONFIG', `New counter "${c.name}" created`)
      setNewCounterName('')
      await loadCounters()
    } catch (e: any) {
      setError(e.detail || 'Failed to create counter')
    } finally {
      setCreatingCounter(false)
    }
  }

  // Open settings panel
  useEffect(() => {
    if (showSettings && selectedCounter) {
      setSelectedServiceIds(selectedCounter.supported_services.map((s) => s.id))
    }
  }, [showSettings, selectedCounter])

  /* ═══════════════════════════════════════════════════════════
   *  RENDER
   * ═══════════════════════════════════════════════════════════ */
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 animate-fade-in" id="staff-dashboard">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-black gradient-text" id="staff-title">
          {t.staffDesk}
        </h1>
        <p className="text-sm text-surface-200/60 mt-1">{t.staffSubtitle}</p>
        {/* Connection indicator */}
        <div className="flex items-center gap-2 mt-2">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success-400 animate-pulse' : 'bg-danger-400'}`} />
          <span className="text-xs text-surface-200/50">{isConnected ? 'Live Updates Connected' : 'Reconnecting...'}</span>
        </div>
      </div>

      {/* Success / Error Banners */}
      {successFlash && (
        <div className="mb-4 px-4 py-2.5 rounded-xl bg-success-400/10 border border-success-400/20 text-success-400 text-sm font-semibold animate-slide-up" id="success-flash">
          ✓ {successFlash}
        </div>
      )}
      {error && (
        <div className="mb-4 px-4 py-2.5 rounded-xl bg-danger-400/10 border border-danger-400/20 text-danger-400 text-sm font-medium" id="error-banner">
          {error}
          <button onClick={() => setError(null)} className="ml-3 text-danger-400/60 hover:text-danger-400 cursor-pointer">✕</button>
        </div>
      )}

      {/* ═════ Counter Selection Grid ═════ */}
      <section className="mb-6" id="counter-selection">
        <h2 className="text-base font-bold text-surface-200/80 mb-3 flex items-center gap-2">
          <svg className="w-4 h-4 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
          </svg>
          {t.selectCounter}
        </h2>
        <p className="text-xs text-surface-200/40 mb-3">{t.selectCounterPrompt}</p>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 stagger">
          {counters.map((c) => {
            const sc = STATUS_CONFIG[c.status] || STATUS_CONFIG.CLOSED
            const isSelected = selectedCounterId === c.id
            return (
              <button
                key={c.id}
                type="button"
                id={`counter-btn-${c.id}`}
                onClick={() => handleSelectCounter(c.id)}
                className={`glass-card p-3 cursor-pointer text-left transition-all duration-200 animate-fade-in ${
                  isSelected
                    ? 'ring-2 ring-primary-400/60 border-primary-400/40 shadow-lg shadow-primary-500/10'
                    : 'hover:border-white/20'
                }`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span className={`w-2.5 h-2.5 rounded-full ${sc.dot}`} />
                  <span className="text-sm font-bold text-surface-100 truncate">{c.name}</span>
                </div>
                <div className={`text-[10px] font-semibold px-2 py-0.5 rounded-full w-fit ${sc.bg} ${sc.color}`}>
                  {sc.label}
                </div>
                {c.current_token_display_number && (
                  <div className="mt-1.5 text-[11px] text-accent-300 font-mono font-bold">
                    → {c.current_token_display_number}
                  </div>
                )}
              </button>
            )
          })}

          {/* Add Counter button */}
          <button
            type="button"
            onClick={() => setShowSettings(!showSettings)}
            className="glass-card p-3 cursor-pointer border-dashed border-white/10 hover:border-primary-400/30 flex flex-col items-center justify-center gap-1 text-surface-200/40 hover:text-primary-400 transition-colors"
            id="add-counter-btn"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            <span className="text-[10px] font-semibold">{t.counterSettings}</span>
          </button>
        </div>
      </section>

      {/* ═════ Settings Panel (collapsible) ═════ */}
      {showSettings && (
        <section className="mb-6 glass-card p-4 sm:p-5 animate-slide-up" id="settings-panel">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-bold text-surface-100">{t.counterSettings}</h3>
            <button onClick={() => setShowSettings(false)} className="text-surface-200/40 hover:text-white cursor-pointer text-xl">✕</button>
          </div>

          {/* Create New Counter */}
          <div className="mb-4 flex gap-2">
            <input
              type="text"
              value={newCounterName}
              onChange={(e) => setNewCounterName(e.target.value)}
              placeholder={t.newCounterName}
              className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-sm text-surface-100 placeholder:text-surface-200/30 focus:border-primary-400/40 focus:outline-none"
              id="new-counter-input"
            />
            <button
              onClick={handleCreateCounter}
              disabled={creatingCounter || !newCounterName.trim()}
              className="btn-primary text-xs px-4 disabled:opacity-40"
              id="create-counter-submit"
            >
              {creatingCounter ? '...' : t.createCounterBtn}
            </button>
          </div>

          {/* Service assignment (for selected counter) */}
          {selectedCounter && (
            <div>
              <p className="text-xs text-surface-200/50 mb-2">
                Assign services to <span className="font-bold text-primary-300">{selectedCounter.name}</span>:
              </p>
              <div className="flex flex-wrap gap-2 mb-3">
                {services.map((svc) => {
                  const active = selectedServiceIds.includes(svc.id)
                  return (
                    <button
                      key={svc.id}
                      type="button"
                      onClick={() =>
                        setSelectedServiceIds((prev) =>
                          active ? prev.filter((id) => id !== svc.id) : [...prev, svc.id]
                        )
                      }
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold border cursor-pointer transition-all ${
                        active
                          ? 'bg-primary-500/20 border-primary-400/40 text-primary-300'
                          : 'bg-white/5 border-white/10 text-surface-200/60 hover:border-white/20'
                      }`}
                    >
                      {svc.code} — {svc.name}
                    </button>
                  )
                })}
              </div>
              <button
                onClick={handleSaveServices}
                disabled={actionLoading === 'services'}
                className="btn-accent text-xs px-4"
                id="save-services-btn"
              >
                {actionLoading === 'services' ? '...' : t.saveServices}
              </button>
            </div>
          )}
        </section>
      )}

      {/* ═════ No Counter Selected State ═════ */}
      {!selectedCounterId && (
        <div className="glass-card p-8 sm:p-12 text-center animate-slide-up" id="no-counter-prompt">
          <svg className="w-16 h-16 mx-auto mb-4 text-surface-200/20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p className="text-surface-200/50 text-sm">{t.noCounterSelected}</p>
        </div>
      )}

      {/* ═════ Main Operations Panel ═════ */}
      {selectedCounterId && selectedCounter && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 animate-slide-up">
          {/* ── LEFT: Token Operations (2/3 width) ────────── */}
          <div className="lg:col-span-2 space-y-5">

            {/* Counter Status Bar */}
            <div className="glass-card p-4 flex flex-wrap items-center justify-between gap-3" id="counter-status-bar">
              <div className="flex items-center gap-3">
                <div className={`w-3.5 h-3.5 rounded-full ${STATUS_CONFIG[counterStatus]?.dot || 'bg-surface-200/40'}`} />
                <div>
                  <h3 className="text-lg font-black text-surface-100">{selectedCounter.name}</h3>
                  <span className={`text-xs font-semibold ${STATUS_CONFIG[counterStatus]?.color}`}>
                    {STATUS_CONFIG[counterStatus]?.label}
                  </span>
                </div>
              </div>
              {/* Counter Status Actions */}
              <div className="flex flex-wrap gap-2">
                {(isClosed || isPaused) && (
                  <button onClick={isPaused ? handleResumeCounter : handleOpenCounter} disabled={!!actionLoading}
                    className="px-3 py-1.5 rounded-xl bg-success-400/10 border border-success-400/25 text-success-400 text-xs font-semibold hover:bg-success-400/20 transition-colors cursor-pointer disabled:opacity-40"
                    id="btn-open-counter">
                    {isPaused ? t.resumeCounterAction : t.openCounterAction}
                  </button>
                )}
                {(isIdle || isServing) && !activeToken && (
                  <button onClick={handlePauseCounter} disabled={!!actionLoading}
                    className="px-3 py-1.5 rounded-xl bg-warning-400/10 border border-warning-400/25 text-warning-400 text-xs font-semibold hover:bg-warning-400/20 transition-colors cursor-pointer disabled:opacity-40"
                    id="btn-pause-counter">
                    {t.pauseCounterAction}
                  </button>
                )}
                {(isIdle || (isServing && !activeToken)) && (
                  <button onClick={handleCloseCounter} disabled={!!actionLoading}
                    className="px-3 py-1.5 rounded-xl bg-danger-400/10 border border-danger-400/25 text-danger-400 text-xs font-semibold hover:bg-danger-400/20 transition-colors cursor-pointer disabled:opacity-40"
                    id="btn-close-counter">
                    {t.closeCounterAction}
                  </button>
                )}
              </div>
            </div>

            {/* Active Token Panel */}
            <div className="glass-card p-5" id="active-token-panel">
              <h3 className="text-sm font-bold text-surface-200/70 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4 text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
                </svg>
                {t.currentActiveToken}
              </h3>

              {activeToken ? (
                <div className="animate-fade-in">
                  {/* Token Display */}
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <div className="text-3xl sm:text-4xl font-black gradient-text tracking-tight">
                        {activeToken.display_number}
                      </div>
                      <div className="text-xs text-surface-200/50 mt-0.5 font-mono">
                        ID: {activeToken.public_id}
                      </div>
                    </div>
                    <div className="text-right">
                      <TokenStatusBadge status={activeToken.status} />
                      {activeToken.status === 'SERVING' && (
                        <div className="mt-2 text-xl font-mono font-bold text-accent-300" id="service-timer">
                          ⏱ {formatElapsed(serviceDuration)}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Token metadata */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-5">
                    {activeToken.service_category && (
                      <div className="p-2.5 rounded-xl bg-white/5">
                        <div className="text-[10px] text-surface-200/40 uppercase tracking-wider mb-0.5">{t.serviceCategory}</div>
                        <div className="text-sm font-semibold text-surface-100">
                          {activeToken.service_category.name}
                        </div>
                      </div>
                    )}
                    {activeToken.called_at && (
                      <div className="p-2.5 rounded-xl bg-white/5">
                        <div className="text-[10px] text-surface-200/40 uppercase tracking-wider mb-0.5">Called At</div>
                        <div className="text-sm font-semibold text-surface-100">
                          {new Date(activeToken.called_at).toLocaleTimeString()}
                        </div>
                      </div>
                    )}
                    {activeToken.service_started_at && (
                      <div className="p-2.5 rounded-xl bg-white/5">
                        <div className="text-[10px] text-surface-200/40 uppercase tracking-wider mb-0.5">{t.serviceDuration}</div>
                        <div className="text-sm font-semibold text-accent-300 font-mono">
                          {formatElapsed(serviceDuration)}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-wrap gap-2" id="token-actions">
                    {canStartServing && (
                      <button onClick={handleStartServing} disabled={!!actionLoading}
                        className="btn-accent text-sm flex-1 sm:flex-none disabled:opacity-40"
                        id="btn-start-serve">
                        {actionLoading === 'serve' ? '...' : `▶ ${t.startServing}`}
                      </button>
                    )}
                    {canComplete && (
                      <button onClick={handleComplete} disabled={!!actionLoading}
                        className="btn-primary text-sm flex-1 sm:flex-none disabled:opacity-40"
                        id="btn-complete">
                        {actionLoading === 'complete' ? '...' : `✓ ${t.completeService}`}
                      </button>
                    )}
                    {canSkip && (
                      <button onClick={handleSkip} disabled={!!actionLoading}
                        className="px-4 py-2 rounded-xl bg-surface-200/5 border border-surface-200/15 text-surface-200/70 text-sm font-semibold hover:bg-danger-400/10 hover:text-danger-400 hover:border-danger-400/25 transition-all cursor-pointer disabled:opacity-40"
                        id="btn-skip">
                        {actionLoading === 'skip' ? '...' : `✗ ${t.skipToken}`}
                      </button>
                    )}
                    {canRecall && (
                      <button onClick={handleRecall} disabled={!!actionLoading}
                        className="px-4 py-2 rounded-xl bg-surface-200/5 border border-surface-200/15 text-surface-200/70 text-sm font-semibold hover:bg-warning-400/10 hover:text-warning-400 hover:border-warning-400/25 transition-all cursor-pointer disabled:opacity-40"
                        id="btn-recall">
                        {actionLoading === 'recall' ? '...' : `↩ ${t.recallToken}`}
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="py-6 text-center" id="no-active-token">
                  <p className="text-surface-200/40 text-sm mb-4">{t.noActiveToken}</p>
                  {canCallNext && (
                    <button onClick={handleCallNext} disabled={!!actionLoading}
                      className="btn-primary text-base px-8 py-3 animate-pulse-glow disabled:opacity-40"
                      id="btn-call-next-main">
                      {actionLoading === 'call' ? t.callingNext : `📢 ${t.callNext}`}
                    </button>
                  )}
                  {(isPaused || isClosed) && (
                    <p className="text-xs text-warning-400 mt-3">
                      Counter is {counterStatus.toLowerCase().replace('_', ' ')}. Open to call tokens.
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Call Next Button (always visible if serving and no active) */}
            {activeToken && canCallNext && (
              <button onClick={handleCallNext} disabled={!!actionLoading}
                className="w-full btn-primary text-base py-3 disabled:opacity-40"
                id="btn-call-next-bottom">
                {actionLoading === 'call' ? t.callingNext : `📢 ${t.callNext}`}
              </button>
            )}

            {/* Waiting Queue */}
            <div className="glass-card p-4" id="waiting-queue-panel">
              <h3 className="text-sm font-bold text-surface-200/70 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4 text-warning-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {t.waitingQueueHeader}
                <span className="ml-auto text-xs text-surface-200/40 font-mono">{waitingQueue.length} {waitingQueue.length === 1 ? 'token' : 'tokens'}</span>
              </h3>

              {waitingQueue.length === 0 ? (
                <p className="text-surface-200/30 text-xs py-4 text-center">{t.noWaitingTokens}</p>
              ) : (
                <div className="space-y-1.5 max-h-64 overflow-y-auto">
                  {waitingQueue.map((token, i) => (
                    <div
                      key={token.public_id}
                      className="flex items-center justify-between px-3 py-2 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-surface-200/30 font-mono w-5 text-right">#{i + 1}</span>
                        <span className="text-sm font-bold text-surface-100">{token.display_number}</span>
                        <span className="text-[10px] text-surface-200/40">{token.service_name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-surface-200/30">
                          ~{Math.ceil(token.estimated_wait_seconds / 60)}m
                        </span>
                        <TokenStatusBadge status={token.status} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ── RIGHT: Event Feed & Quick Info (1/3 width) ── */}
          <div className="space-y-5">
            {/* Counter Info Card */}
            <div className="glass-card p-4" id="counter-info-card">
              <h3 className="text-sm font-bold text-surface-200/70 mb-3">Counter Details</h3>
              <div className="space-y-2.5">
                <div className="flex justify-between text-xs">
                  <span className="text-surface-200/40">Status</span>
                  <span className={`font-semibold ${STATUS_CONFIG[counterStatus]?.color}`}>
                    {STATUS_CONFIG[counterStatus]?.label}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-surface-200/40">Supported Services</span>
                  <span className="text-surface-100 font-semibold">
                    {selectedCounter.supported_services.length || '—'}
                  </span>
                </div>
                {selectedCounter.supported_services.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {selectedCounter.supported_services.map((svc) => (
                      <span key={svc.id} className="px-2 py-0.5 rounded-full bg-primary-500/10 text-primary-300 text-[10px] font-semibold">
                        {svc.code}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex justify-between text-xs">
                  <span className="text-surface-200/40">Queue Depth</span>
                  <span className="text-surface-100 font-bold">{waitingQueue.length}</span>
                </div>
              </div>
            </div>

            {/* Live Event Feed */}
            <div className="glass-card p-4" id="event-feed">
              <h3 className="text-sm font-bold text-surface-200/70 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Live Event Feed
                <span className={`ml-auto w-2 h-2 rounded-full ${isConnected ? 'bg-success-400 animate-pulse' : 'bg-danger-400'}`} />
              </h3>

              {eventLog.length === 0 ? (
                <p className="text-surface-200/30 text-xs py-4 text-center">
                  Events will appear here as operations are performed.
                </p>
              ) : (
                <div className="space-y-1 max-h-80 overflow-y-auto">
                  {eventLog.map((entry) => (
                    <div key={entry.id} className="flex gap-2 text-xs py-1.5 border-b border-white/[0.04] last:border-0 animate-fade-in">
                      <span className="text-surface-200/30 font-mono shrink-0 w-16">
                        {formatTimestamp(entry.timestamp)}
                      </span>
                      <span className={`shrink-0 font-bold ${
                        entry.event === 'CALLED' ? 'text-primary-400' :
                        entry.event === 'SERVING' ? 'text-accent-400' :
                        entry.event === 'COMPLETED' ? 'text-success-400' :
                        entry.event === 'SKIPPED' ? 'text-surface-200/50' :
                        entry.event === 'RECALLED' ? 'text-warning-400' :
                        entry.event === 'COUNTER' ? 'text-primary-300' :
                        entry.event === 'CONFIG' ? 'text-accent-300' :
                        'text-surface-200/40'
                      }`}>
                        {entry.event}
                      </span>
                      <span className="text-surface-200/60 truncate">{entry.message}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
