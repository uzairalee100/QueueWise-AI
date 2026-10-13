/**
 * QueueWise AI — Citizen Digital Kiosk Page
 *
 * High-accessibility, touch-friendly digital token issuance kiosk.
 * Displays live service statuses, dynamic wait times, and generates
 * tokens with printable QR codes for live mobile tracking.
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { getServices, getQueueSummary, createToken } from '../services/api'
import type { ServiceCategory, QueueSummaryResponse, TokenPublicStatus } from '../types/api'
import { useLanguage } from '../context/LanguageContext'

export function KioskPage() {
  const { t, isRTL } = useLanguage()
  const navigate = useNavigate()

  const [services, setServices] = useState<ServiceCategory[]>([])
  const [summary, setSummary] = useState<QueueSummaryResponse | null>(null)
  const [selectedServiceId, setSelectedServiceId] = useState<string>('')
  const [priority, setPriority] = useState<number>(0)
  const [contactInfo, setContactInfo] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Issued token state for modal
  const [issuedToken, setIssuedToken] = useState<TokenPublicStatus | null>(null)

  // Fetch services and initial summary
  useEffect(() => {
    let isMounted = true
    async function loadData() {
      try {
        setIsLoading(true)
        const [servicesData, summaryData] = await Promise.all([
          getServices(),
          getQueueSummary().catch(() => null),
        ])
        if (!isMounted) return
        setServices(servicesData)
        if (servicesData.length > 0) {
          setSelectedServiceId(servicesData[0].id)
        }
        if (summaryData) {
          setSummary(summaryData)
        }
      } catch (err: any) {
        if (!isMounted) return
        setError(err.message || 'Failed to load services')
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }
    loadData()
    return () => {
      isMounted = false
    }
  }, [])

  // Helper to get metrics for a service
  const getMetrics = (serviceId: string) => {
    if (!summary) return null
    return summary.services.find((s) => s.service_id === serviceId)
  }

  const handleIssueToken = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedServiceId) return

    try {
      setIsSubmitting(true)
      setError(null)
      const token = await createToken({
        service_id: selectedServiceId,
        priority,
        contact_info: contactInfo.trim() || undefined,
        idempotency_key: `kiosk-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`,
      })
      setIssuedToken(token)
    } catch (err: any) {
      setError(err.message || 'Failed to issue token. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const formatWaitTime = (seconds: number) => {
    const minutes = Math.ceil(seconds / 60)
    return `~${minutes} min`
  }

  const trackingUrl = issuedToken
    ? `${window.location.origin}/track/${issuedToken.public_id}`
    : ''

  return (
    <div className={`max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12 ${isRTL ? 'font-urdu' : ''}`}>
      {/* Kiosk Header */}
      <div className="text-center mb-8 sm:mb-12">
        <div className="inline-flex items-center gap-2 glass-light rounded-full px-4 py-1.5 mb-4 text-xs font-semibold text-accent-400">
          <span className="w-2 h-2 rounded-full bg-accent-400 animate-pulse" />
          {t.kioskTitle}
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-2">
          {t.kioskSubtitle}
        </h1>
        <p className="text-sm text-surface-200/70 max-w-xl mx-auto">
          {t.chooseService}
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-danger-500/10 border border-danger-500/20 text-danger-400 text-sm flex items-center gap-3">
          <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-surface-200/60">Loading available service counters...</p>
        </div>
      ) : (
        <form onSubmit={handleIssueToken} className="space-y-8">
          {/* Service Cards Grid */}
          <div>
            <label className="block text-sm font-semibold text-surface-200 mb-3">
              1. {t.chooseService}
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {services.map((service) => {
                const metrics = getMetrics(service.id)
                const isSelected = selectedServiceId === service.id
                const isStalled = metrics?.is_stalled

                return (
                  <button
                    key={service.id}
                    type="button"
                    onClick={() => setSelectedServiceId(service.id)}
                    className={`
                      relative p-5 text-left rounded-2xl transition-all duration-200 cursor-pointer flex flex-col justify-between
                      ${
                        isSelected
                          ? 'glass border-2 border-primary-500 shadow-lg shadow-primary-500/20 bg-primary-950/30 ring-2 ring-primary-500/30'
                          : 'glass-card hover:border-white/20'
                      }
                    `}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="text-xs font-bold px-2.5 py-1 rounded-md bg-white/10 text-primary-300 tracking-wider dir-ltr font-mono">
                          {service.code}
                        </span>
                        <div className="flex items-center gap-1.5 text-xs">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              isStalled ? 'bg-warning-400' : 'bg-success-400 animate-pulse'
                            }`}
                          />
                          <span className="text-surface-200/70 font-medium">
                            {metrics ? `${metrics.active_counters} ${t.activeCounters}` : 'Active'}
                          </span>
                        </div>
                      </div>
                      <h3 className="text-lg font-bold text-white mb-1">
                        {service.name}
                      </h3>
                      {service.description && (
                        <p className="text-xs text-surface-200/60 line-clamp-2 mb-4">
                          {service.description}
                        </p>
                      )}
                    </div>

                    {/* Operational metrics badge */}
                    <div className="pt-3 border-t border-white/5 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1 text-surface-200/70">
                        <svg className="w-4 h-4 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                        </svg>
                        <span>
                          {metrics ? metrics.waiting_count : 0} {t.waitingQueue}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 font-semibold text-accent-400 dir-ltr font-mono">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>
                          {metrics
                            ? formatWaitTime(metrics.estimated_wait_for_next_arrival)
                            : formatWaitTime(service.default_duration_seconds)}
                        </span>
                      </div>
                    </div>

                    {isStalled && (
                      <div className="mt-2 text-[11px] text-warning-400/90 font-medium">
                        ⚠️ {t.stalledWarning}
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Priority Assistance Toggle */}
          <div className="glass-card p-5">
            <label className="block text-sm font-semibold text-surface-200 mb-3">
              2. {t.priorityTitle}
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setPriority(0)}
                className={`p-3.5 rounded-xl text-sm font-medium transition-all text-start flex items-center gap-3 cursor-pointer min-h-[44px] ${
                  priority === 0
                    ? 'bg-primary-600/30 border border-primary-500 text-white font-semibold'
                    : 'bg-white/5 border border-white/5 text-surface-200/70 hover:bg-white/10'
                }`}
              >
                <span className="w-4 h-4 rounded-full border-2 border-primary-400 flex items-center justify-center shrink-0">
                  {priority === 0 && <span className="w-2 h-2 rounded-full bg-primary-400" />}
                </span>
                <span>{t.priorityStandard}</span>
              </button>

              <button
                type="button"
                onClick={() => setPriority(1)}
                className={`p-3.5 rounded-xl text-sm font-medium transition-all text-start flex items-center gap-3 cursor-pointer min-h-[44px] ${
                  priority === 1
                    ? 'bg-accent-600/30 border border-accent-500 text-white font-semibold'
                    : 'bg-white/5 border border-white/5 text-surface-200/70 hover:bg-white/10'
                }`}
              >
                <span className="w-4 h-4 rounded-full border-2 border-accent-400 flex items-center justify-center shrink-0">
                  {priority === 1 && <span className="w-2 h-2 rounded-full bg-accent-400" />}
                </span>
                <span>{t.prioritySenior}</span>
              </button>
            </div>
          </div>

          {/* Contact Info (Optional) */}
          <div className="glass-card p-5">
            <label htmlFor="contact_info" className="block text-sm font-semibold text-surface-200 mb-2">
              3. {t.phoneOptional}
            </label>
            <input
              id="contact_info"
              type="tel"
              value={contactInfo}
              onChange={(e) => setContactInfo(e.target.value)}
              placeholder={t.phonePlaceholder}
              className="w-full px-4 py-3 rounded-xl bg-surface-900/60 border border-white/10 text-white placeholder-surface-200/30 focus:border-primary-500 focus:outline-none transition-colors"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting || !selectedServiceId}
            className="w-full py-4 px-6 rounded-2xl btn-primary text-lg font-bold tracking-wide shadow-xl shadow-primary-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3 cursor-pointer"
          >
            {isSubmitting ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>{t.issuing}</span>
              </>
            ) : (
              <>
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
                </svg>
                <span>{t.issueTokenBtn}</span>
              </>
            )}
          </button>
        </form>
      )}

      {/* Token Issued Confirmation Modal */}
      {issuedToken && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
          <div className="bg-surface-900 border border-white/15 rounded-3xl max-w-md w-full p-6 sm:p-8 text-center shadow-2xl relative">
            {/* Header */}
            <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-tr from-success-500 to-accent-500 flex items-center justify-center text-white mb-4 shadow-lg shadow-success-500/20">
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <h2 className="text-xl font-bold text-white mb-1">
              {t.tokenIssuedTitle}
            </h2>
            <p className="text-xs text-surface-200/70 mb-6">
              {t.keepThisSafe}
            </p>

            {/* Token Badge */}
            <div className="bg-surface-950/80 border border-white/10 rounded-2xl p-5 mb-6">
              <div className="text-xs font-semibold uppercase tracking-wider text-surface-200/60 mb-1">
                {issuedToken.service_name}
              </div>
              <div className="text-4xl sm:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-primary-400 via-accent-300 to-white tracking-wider my-2 dir-ltr inline-block">
                {issuedToken.display_number}
              </div>
              <div className="flex items-center justify-center gap-4 text-xs text-surface-200/80 pt-2 border-t border-white/5 mt-2">
                <div>
                  <span className="text-surface-200/50 block">{t.peopleAhead}</span>
                  <span className="text-sm font-bold text-white">{issuedToken.position_ahead}</span>
                </div>
                <div className="h-6 w-px bg-white/10" />
                <div>
                  <span className="text-surface-200/50 block">{t.estimatedWait}</span>
                  <span className="text-sm font-bold text-accent-400">
                    {formatWaitTime(issuedToken.estimated_wait_seconds)}
                  </span>
                </div>
              </div>
            </div>

            {/* QR Code Container */}
            <div className="bg-white p-3 rounded-2xl inline-block mb-4 shadow-md">
              <QRCodeSVG
                value={trackingUrl}
                size={140}
                level="M"
                includeMargin={false}
              />
            </div>
            <p className="text-[11px] text-surface-200/50 mb-6">
              {t.scanToTrack}
            </p>

            {/* Actions */}
            <div className="space-y-3">
              <button
                type="button"
                onClick={() => navigate(`/track/${issuedToken.public_id}`)}
                className="w-full py-3.5 px-4 rounded-xl btn-primary font-bold text-sm shadow-lg shadow-primary-500/25 flex items-center justify-center gap-2 cursor-pointer"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                <span>{t.trackOnDevice}</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setIssuedToken(null)
                  setContactInfo('')
                }}
                className="w-full py-2.5 px-4 rounded-xl text-surface-200/70 hover:text-white hover:bg-white/5 text-xs font-semibold transition-colors cursor-pointer"
              >
                {t.close}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
