/**
 * QueueWise AI — Operational Analytics & Supervisor Dashboard
 *
 * Live supervisor intelligence computing all operational metrics
 * directly from stored database ServiceEvent and Token records.
 *
 * Features:
 * - Filterable time windows (Today / 24h, Past 7 Days, Past 30 Days, All Time)
 * - Executive KPI Scorecards (Volume, Avg Wait, Service Duration, SLA %, Utilization)
 * - Hourly Traffic & Rush Hour Distribution Visualizer
 * - Service Category Performance Breakdown & SLA Compliance
 * - Physical Counter Desk Efficiency Leaderboard
 * - Live Immutable Service Event Audit Trail
 * - Bilingual English/Urdu support
 */
import { useState, useEffect, useCallback } from 'react'
import { useLanguage } from '../context/LanguageContext'
import { getOperationalDashboard } from '../services/api'
import type {
  OperationalAnalyticsResponse,
  ServiceAnalyticsItem,
  CounterAnalyticsItem,
  ServiceEventLogItem,
} from '../types/api'

type TimeFilter = '24h' | '7d' | '30d' | 'all'

export function AnalyticsPage() {
  const { lang, t, isRTL } = useLanguage()

  // State
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('24h')
  const [data, setData] = useState<OperationalAnalyticsResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true)
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date())

  // Fetch analytics data
  const fetchData = useCallback(async () => {
    try {
      setErrorMsg(null)
      const hoursBack =
        timeFilter === '24h'
          ? 24
          : timeFilter === '7d'
          ? 168
          : timeFilter === '30d'
          ? 720
          : undefined

      const res = await getOperationalDashboard({
        hoursBack,
        slaSeconds: 600,
        includeSimulations: false,
      })
      setData(res)
      setLastRefreshedAt(new Date())
    } catch (err: unknown) {
      console.error('Failed to load operational analytics', err)
      const msg = err instanceof Error ? err.message : 'Failed to fetch analytics.'
      setErrorMsg(msg)
    } finally {
      setLoading(false)
    }
  }, [timeFilter])

  // Initial fetch and on time filter change
  useEffect(() => {
    setLoading(true)
    fetchData()
  }, [fetchData])

  // Auto-refresh interval (every 10s)
  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(() => {
      fetchData()
    }, 10000)
    return () => clearInterval(interval)
  }, [autoRefresh, fetchData])

  // Peak hour calculation
  const peakHour = data?.hourly_trends
    ? [...data.hourly_trends].sort((a, b) => b.arrivals_count - a.arrivals_count)[0]
    : null

  const maxHourlyVolume = data?.hourly_trends
    ? Math.max(...data.hourly_trends.map((h) => Math.max(h.arrivals_count, h.completed_count, 1)))
    : 1

  return (
    <div className={`space-y-8 pb-16 px-4 sm:px-6 max-w-7xl mx-auto ${isRTL ? 'font-urdu' : ''}`}>
      {/* Page Header */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-700/60 bg-gradient-to-br from-slate-900/90 via-slate-800/80 to-blue-950/40 p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl" />
        <div className="absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-emerald-500/10 blur-3xl" />

        <div className="relative flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>{lang === 'ur' ? 'اصل ڈیٹا بیس کے واقعات' : 'Computed from Stored Service Events'}</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
              {t.analytics}
            </h1>
            <p className="text-sm sm:text-base text-slate-300 max-w-2xl">
              {t.analyticsSubtitle}
            </p>
          </div>

          {/* Controls: Time Filter + Auto Refresh */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Time Filter Buttons */}
            <div className="inline-flex rounded-xl bg-slate-950/80 p-1 border border-slate-800 text-xs">
              <button
                onClick={() => setTimeFilter('24h')}
                id="btn-filter-24h"
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  timeFilter === '24h'
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {t.today}
              </button>
              <button
                onClick={() => setTimeFilter('7d')}
                id="btn-filter-7d"
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  timeFilter === '7d'
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {t.past7Days}
              </button>
              <button
                onClick={() => setTimeFilter('30d')}
                id="btn-filter-30d"
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  timeFilter === '30d'
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {t.past30Days}
              </button>
              <button
                onClick={() => setTimeFilter('all')}
                id="btn-filter-all"
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  timeFilter === 'all'
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {t.allTime}
              </button>
            </div>

            {/* Refresh Button */}
            <button
              onClick={() => fetchData()}
              disabled={loading}
              id="btn-refresh-analytics"
              className="px-3.5 py-2 rounded-xl border border-slate-700 bg-slate-850 hover:bg-slate-800 text-slate-200 text-xs font-semibold flex items-center gap-1.5 active:scale-95 transition-all"
              title="Refresh Analytics"
            >
              <span className={loading ? 'animate-spin' : ''}>🔄</span>
              <span className="hidden sm:inline">Refresh</span>
            </button>

            {/* Auto-Refresh Toggle */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-2 rounded-xl text-xs font-semibold border flex items-center gap-1.5 transition-all ${
                autoRefresh
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                  : 'border-slate-800 bg-slate-900/60 text-slate-400'
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${autoRefresh ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
              <span className="text-[11px]">{t.liveRefresh}</span>
            </button>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300 flex items-center gap-3">
          <span>⚠️</span>
          <span>{errorMsg}</span>
        </div>
      )}

      {loading && !data ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-28 rounded-2xl bg-slate-800/40 border border-slate-800 animate-pulse" />
          ))}
        </div>
      ) : data ? (
        <>
          {/* Executive KPI Scorecards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4" id="kpi-scorecards-grid">
            {/* Total Issued */}
            <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-850 p-5 shadow-lg">
              <div className="text-xs font-medium text-slate-400">Total Tokens</div>
              <div className="mt-2 text-3xl font-extrabold text-white">
                {data.summary.total_tokens_issued}
              </div>
              <div className="mt-1 text-[11px] text-emerald-400 font-semibold">
                {data.summary.tokens_completed} served ({data.summary.completion_rate_pct}%)
              </div>
            </div>

            {/* Average Wait Time */}
            <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-850 p-5 shadow-lg">
              <div className="text-xs font-medium text-slate-400">{t.estimatedWait} (Avg)</div>
              <div className="mt-2 text-3xl font-extrabold text-blue-400">
                {Math.floor(data.summary.avg_wait_seconds / 60)}m {data.summary.avg_wait_seconds % 60}s
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                P95: {Math.round(data.summary.p95_wait_seconds / 60)}m | Peak: {Math.round(data.summary.max_wait_seconds / 60)}m
              </div>
            </div>

            {/* Average Service Time */}
            <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-850 p-5 shadow-lg">
              <div className="text-xs font-medium text-slate-400">{t.avgServiceDuration}</div>
              <div className="mt-2 text-3xl font-extrabold text-teal-400">
                {Math.floor(data.summary.avg_service_seconds / 60)}m {data.summary.avg_service_seconds % 60}s
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                At service counters
              </div>
            </div>

            {/* SLA Compliance */}
            <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-850 p-5 shadow-lg">
              <div className="text-xs font-medium text-slate-400">SLA (&lt; 10 min)</div>
              <div className={`mt-2 text-3xl font-extrabold ${data.summary.sla_compliance_pct < 80 ? 'text-amber-400' : 'text-emerald-400'}`}>
                {data.summary.sla_compliance_pct}%
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                {data.summary.sla_breach_count} SLA breaches
              </div>
            </div>

            {/* Counter Utilization */}
            <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-850 p-5 shadow-lg">
              <div className="text-xs font-medium text-slate-400">{t.activeCounters}</div>
              <div className="mt-2 text-3xl font-extrabold text-indigo-400">
                {data.summary.active_counters_count} / {data.summary.total_counters_count}
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                {data.summary.avg_counter_utilization_pct}% avg utilization
              </div>
            </div>

            {/* Churn (No-Show & Cancelled) */}
            <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-850 p-5 shadow-lg">
              <div className="text-xs font-medium text-slate-400">Skipped & Cancelled</div>
              <div className="mt-2 text-3xl font-extrabold text-purple-400">
                {data.summary.tokens_skipped + data.summary.tokens_cancelled}
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                {data.summary.no_show_rate_pct}% skip | {data.summary.cancellation_rate_pct}% cancel
              </div>
            </div>
          </div>

          {/* Hourly Traffic & Rush Hour Trends */}
          <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 backdrop-blur-xl shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-800">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <span>📈</span>
                  <span>{t.hourlyVolume}</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  {lang === 'ur'
                    ? 'دن کے مختلف اوقات میں شہریوں کی آمد اور سروس کی رفتار کا موازنہ'
                    : 'Visualizing hourly arrival surges vs service completion throughput'}
                </p>
              </div>

              {peakHour && peakHour.arrivals_count > 0 && (
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 text-xs text-amber-300 font-semibold">
                  <span>🔥</span>
                  <span>Peak Traffic: {peakHour.hour_label} ({peakHour.arrivals_count} citizens)</span>
                </div>
              )}
            </div>

            {/* Custom SVG / CSS Bar Chart */}
            <div className="space-y-2 pt-2">
              <div className="h-44 w-full flex items-end gap-1 sm:gap-2 px-2 overflow-x-auto pb-4">
                {data.hourly_trends.map((h) => {
                  const arrivalHeight = Math.max(8, (h.arrivals_count / maxHourlyVolume) * 130)
                  const completedHeight = Math.max(6, (h.completed_count / maxHourlyVolume) * 130)

                  return (
                    <div
                      key={h.hour}
                      className="flex-1 min-w-[20px] flex flex-col items-center gap-1 group relative cursor-pointer"
                    >
                      {/* Tooltip on hover */}
                      <div className="absolute -top-14 hidden group-hover:flex flex-col items-center z-20 bg-slate-950 text-white text-[10px] rounded-lg p-2 border border-slate-700 shadow-xl whitespace-nowrap">
                        <span className="font-bold text-blue-300">{h.hour_label}</span>
                        <span>Arrivals: {h.arrivals_count} | Done: {h.completed_count}</span>
                        <span>Avg Wait: {Math.round(h.avg_wait_seconds / 60)} min</span>
                      </div>

                      {/* Bars container */}
                      <div className="w-full flex items-end justify-center gap-0.5">
                        {/* Arrival Bar */}
                        <div
                          className="w-1/2 rounded-t bg-gradient-to-t from-blue-600 to-blue-400 group-hover:from-blue-500 group-hover:to-blue-300 transition-all"
                          style={{ height: `${arrivalHeight}px` }}
                        />
                        {/* Completed Bar */}
                        <div
                          className="w-1/2 rounded-t bg-gradient-to-t from-emerald-600 to-emerald-400 group-hover:from-emerald-500 group-hover:to-emerald-300 transition-all"
                          style={{ height: `${completedHeight}px` }}
                        />
                      </div>

                      {/* Hour label */}
                      <span className="text-[9px] font-mono text-slate-400 block truncate">
                        {h.hour % 3 === 0 ? `${h.hour}h` : ''}
                      </span>
                    </div>
                  )
                })}
              </div>

              {/* Chart Legend */}
              <div className="flex items-center justify-center gap-6 pt-2 border-t border-slate-800 text-xs">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded bg-blue-500" />
                  <span className="text-slate-300">Citizen Arrivals</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded bg-emerald-500" />
                  <span className="text-slate-300">Completed Services</span>
                </div>
              </div>
            </div>
          </div>

          {/* Two-Column Grid: Services Breakdown & Counter Efficiency */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Services Category Breakdown */}
            <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 backdrop-blur-xl shadow-xl space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>📑</span>
                <span>{t.servicePerformance}</span>
              </h3>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="py-2.5 px-3">Service</th>
                      <th className="py-2.5 px-3 text-right">Volume</th>
                      <th className="py-2.5 px-3 text-right">Avg Wait</th>
                      <th className="py-2.5 px-3 text-right">Avg Duration</th>
                      <th className="py-2.5 px-3 text-right">SLA %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-sans">
                    {data.services.map((s: ServiceAnalyticsItem) => (
                      <tr key={s.service_id} className="hover:bg-slate-850/60 transition-colors">
                        <td className="py-3 px-3">
                          <div className="font-bold text-white">{s.service_name}</div>
                          <span className="text-[10px] font-mono text-blue-400">{s.service_code}</span>
                        </td>
                        <td className="py-3 px-3 text-right font-mono">
                          <span className="text-white font-semibold">{s.total_issued}</span>
                          <span className="text-slate-400 block text-[10px]">({s.completed} done)</span>
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-200">
                          {Math.floor(s.avg_wait_seconds / 60)}m {s.avg_wait_seconds % 60}s
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-300">
                          {Math.floor(s.avg_service_seconds / 60)}m {s.avg_service_seconds % 60}s
                        </td>
                        <td className="py-3 px-3 text-right font-mono font-bold">
                          <span className={s.sla_compliance_pct < 80 ? 'text-amber-400' : 'text-emerald-400'}>
                            {s.sla_compliance_pct}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Counter Desk Efficiency */}
            <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 backdrop-blur-xl shadow-xl space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>🪑</span>
                <span>{t.counterEfficiency}</span>
              </h3>

              <div className="space-y-3">
                {data.counters.map((c: CounterAnalyticsItem) => {
                  const statusColors: Record<string, string> = {
                    OPEN_SERVING: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
                    OPEN_IDLE: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
                    PAUSED: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
                    CLOSED: 'bg-slate-800 text-slate-400 border-slate-700',
                  }

                  return (
                    <div
                      key={c.counter_id}
                      className="p-4 rounded-2xl border border-slate-800 bg-slate-850/80 space-y-2 hover:border-slate-700 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-sm">{c.counter_name}</span>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${statusColors[c.current_status] || 'bg-slate-800 text-slate-400'}`}>
                            {c.current_status}
                          </span>
                        </div>
                        <span className="text-xs font-mono font-bold text-emerald-400">
                          {c.utilization_pct}% Busy
                        </span>
                      </div>

                      {/* Utilization Bar */}
                      <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-blue-500 to-emerald-400 h-full rounded-full transition-all"
                          style={{ width: `${Math.min(100, c.utilization_pct)}%` }}
                        />
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                        <span>Tokens Served: <strong className="text-white">{c.tokens_served}</strong></span>
                        <span>Avg Service: <strong className="text-slate-300">{Math.round(c.avg_service_seconds / 60)}m</strong></span>
                        <span>Supported: <span className="font-mono text-blue-300">{c.supported_services.join(', ') || 'All'}</span></span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Live Service Event Audit Trail (Exit Condition Guarantee) */}
          <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 backdrop-blur-xl shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span>📜</span>
                  <span>{t.auditLogTitle}</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {lang === 'ur'
                    ? 'ڈیٹا بیس میں محفوظ کیے گئے حقیقی واقعات کا لائیو لاگ'
                    : 'Real-time feed of immutable transitions stored in the ServiceEvent ledger'}
                </p>
              </div>

              <span className="text-xs text-slate-400 font-mono">
                Last updated: {lastRefreshedAt.toLocaleTimeString()}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">Timestamp</th>
                    <th className="py-2.5 px-3">Event Type</th>
                    <th className="py-2.5 px-3">Token #</th>
                    <th className="py-2.5 px-3">Counter</th>
                    <th className="py-2.5 px-3">Reason / Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-[11px]">
                  {data.recent_events.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-500 font-sans">
                        No service events recorded yet. Issue or call tokens to populate audit log.
                      </td>
                    </tr>
                  ) : (
                    data.recent_events.map((ev: ServiceEventLogItem) => {
                      const eventColors: Record<string, string> = {
                        TOKEN_CREATED: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
                        TOKEN_CALLED: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
                        TOKEN_SERVING: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
                        TOKEN_COMPLETED: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
                        TOKEN_SKIPPED: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
                        TOKEN_CANCELLED: 'text-slate-400 bg-slate-800 border-slate-700',
                      }

                      return (
                        <tr key={ev.id} className="hover:bg-slate-850/50 transition-colors">
                          <td className="py-2.5 px-3 text-slate-400">
                            {new Date(ev.timestamp).toLocaleTimeString()}
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${eventColors[ev.event_type] || 'text-slate-300'}`}>
                              {ev.event_type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-bold text-white">
                            {ev.token_display_number || '—'}
                          </td>
                          <td className="py-2.5 px-3 text-slate-300 font-sans">
                            {ev.counter_name || '—'}
                          </td>
                          <td className="py-2.5 px-3 text-slate-400 font-sans truncate max-w-xs">
                            {ev.reason || 'Normal queue transition'}
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}
