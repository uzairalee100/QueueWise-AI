import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLanguage } from '../context/LanguageContext'

/**
 * QueueWise AI — Citizen Home Page
 *
 * Cleaned primary landing page with 3 clear citizen actions:
 * 1. Get a Digital Token -> /kiosk
 * 2. Check My Token -> /track
 * 3. How It Works & Help -> interactive modal
 *
 * All Roman Urdu completely removed. Full English & proper Urdu script support.
 */
export function HomePage() {
  const navigate = useNavigate()
  const { t, isRTL } = useLanguage()
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const [showHelpModal, setShowHelpModal] = useState<boolean>(false)

  useEffect(() => {
    fetch('/health')
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'healthy') {
          setBackendStatus('online')
        } else {
          setBackendStatus('offline')
        }
      })
      .catch(() => setBackendStatus('offline'))
  }, [])

  return (
    <div className={`animate-fade-in ${isRTL ? 'font-urdu' : ''}`}>
      {/* Hero Section */}
      <section className="px-4 sm:px-6 pt-8 pb-12 sm:pt-16 sm:pb-20">
        <div className="max-w-4xl mx-auto text-center">
          {/* Floating badge */}
          <div className="inline-flex items-center gap-2 glass-light rounded-full px-4 py-2 mb-6 sm:mb-8 animate-float">
            <span className="w-2 h-2 rounded-full bg-accent-400" />
            <span className="text-xs sm:text-sm text-surface-200 font-medium">
              SC-03 Public Service Queue Optimizer
            </span>
          </div>

          {/* Main headline */}
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight mb-4 sm:mb-6 leading-tight">
            <span className="gradient-text">Smarter Queues.</span>
            <br />
            <span className="text-white">Less Waiting.</span>
            <br />
            <span className="text-surface-200 font-semibold text-2xl sm:text-4xl lg:text-5xl">
              Better Public Services.
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg lg:text-xl text-surface-200/80 max-w-2xl mx-auto mb-8 sm:mb-12 leading-relaxed px-2">
            {t.tagline}
          </p>

          {/* Three primary action cards — Cleaned: No Roman Urdu headings */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 max-w-3xl mx-auto stagger">
            {/* 1. Get a Digital Token */}
            <ActionCard
              id="action-get-token"
              onClick={() => navigate('/kiosk')}
              icon={
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="2" width="20" height="20" rx="3" />
                  <path d="M12 8v8" />
                  <path d="M8 12h8" />
                </svg>
              }
              title={t.tokenLo}
              description={t.tokenLoDesc}
              gradient="from-primary-600 to-primary-700"
              hoverGlow="shadow-primary-500/30"
            />

            {/* 2. Check My Token */}
            <ActionCard
              id="action-check-token"
              onClick={() => navigate('/track')}
              icon={
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v6l4 2" />
                </svg>
              }
              title={t.meraToken}
              description={t.meraTokenDesc}
              gradient="from-accent-600 to-accent-700"
              hoverGlow="shadow-accent-500/30"
            />

            {/* 3. How It Works & Help */}
            <ActionCard
              id="action-help"
              onClick={() => setShowHelpModal(true)}
              icon={
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                  <path d="M12 17h.01" />
                </svg>
              }
              title={t.madad}
              description={t.madadDesc}
              gradient="from-violet-600 to-violet-700"
              hoverGlow="shadow-violet-500/30"
            />
          </div>
        </div>
      </section>

      {/* Backend Status Section */}
      <section className="px-4 sm:px-6 pb-8 sm:pb-12">
        <div className="max-w-md mx-auto">
          <div className="glass-card p-3.5 sm:p-4 flex items-center justify-between" id="backend-status">
            <div className="flex items-center gap-3">
              <div
                className={`w-3 h-3 rounded-full ${
                  backendStatus === 'online'
                    ? 'bg-success-400 animate-pulse'
                    : backendStatus === 'offline'
                    ? 'bg-danger-400'
                    : 'bg-warning-400 animate-pulse'
                }`}
              />
              <span className="text-xs sm:text-sm font-medium text-surface-200">
                Backend API
              </span>
            </div>
            <span
              className={`text-xs font-semibold px-3 py-1 rounded-full flex items-center gap-1.5 ${
                backendStatus === 'online'
                  ? 'bg-success-400/10 text-success-400'
                  : backendStatus === 'offline'
                  ? 'bg-danger-400/10 text-danger-400'
                  : 'bg-warning-400/10 text-warning-400'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  backendStatus === 'online'
                    ? 'bg-success-400'
                    : backendStatus === 'offline'
                    ? 'bg-danger-400'
                    : 'bg-warning-400 animate-pulse'
                }`}
              />
              <span>
                {backendStatus === 'online'
                  ? t.connected
                  : backendStatus === 'offline'
                  ? t.offline
                  : t.checking}
              </span>
            </span>
          </div>
        </div>
      </section>

      {/* Operations & Management Portal Modules */}
      <section className="px-4 sm:px-6 pb-12 sm:pb-14">
        <div className="max-w-5xl mx-auto">
          <div className="mb-6">
            <h2 className="text-xl sm:text-2xl font-bold text-white">
              {t.portalTitle}
            </h2>
            <p className="text-xs sm:text-sm text-surface-200/60 mt-1">
              {t.portalSubtitle}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Staff Counter Desk */}
            <button
              onClick={() => navigate('/staff')}
              className="glass p-5 rounded-2xl border border-white/10 hover:border-primary-500/40 text-left transition-all group hover:bg-white/5 cursor-pointer shadow-lg hover:shadow-primary-500/10 active:scale-95 flex flex-col justify-between min-h-[160px]"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-primary-500/20 text-primary-300 flex items-center justify-center text-xl mb-3 group-hover:scale-110 transition-transform">
                  🪑
                </div>
                <h3 className="font-bold text-white text-sm mb-1">{t.staffDesk}</h3>
                <p className="text-xs text-surface-200/70 leading-relaxed">
                  Call next tokens, manage serving desks, and handle no-shows in real time.
                </p>
              </div>
              <span className="text-[11px] font-semibold text-primary-400 mt-4 flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                {t.openDeskAction} &rarr;
              </span>
            </button>

            {/* Simulation Lab */}
            <button
              onClick={() => navigate('/simulation')}
              className="glass p-5 rounded-2xl border border-white/10 hover:border-amber-500/40 text-left transition-all group hover:bg-white/5 cursor-pointer shadow-lg hover:shadow-amber-500/10 active:scale-95 flex flex-col justify-between min-h-[160px]"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-300 flex items-center justify-center text-xl mb-3 group-hover:scale-110 transition-transform">
                  🧪
                </div>
                <h3 className="font-bold text-white text-sm mb-1">{t.simulationLab}</h3>
                <p className="text-xs text-surface-200/70 leading-relaxed">
                  Test scenarios A-F and optimize counter reallocation with M/M/c queue theory.
                </p>
              </div>
              <span className="text-[11px] font-semibold text-amber-400 mt-4 flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                {t.launchLabAction} &rarr;
              </span>
            </button>

            {/* Operational Analytics */}
            <button
              onClick={() => navigate('/analytics')}
              className="glass p-5 rounded-2xl border border-white/10 hover:border-emerald-500/40 text-left transition-all group hover:bg-white/5 cursor-pointer shadow-lg hover:shadow-emerald-500/10 active:scale-95 flex flex-col justify-between min-h-[160px]"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-300 flex items-center justify-center text-xl mb-3 group-hover:scale-110 transition-transform">
                  📈
                </div>
                <h3 className="font-bold text-white text-sm mb-1">{t.analytics}</h3>
                <p className="text-xs text-surface-200/70 leading-relaxed">
                  Real-time SLA compliance, rush hour hourly volume, and immutable audit trail.
                </p>
              </div>
              <span className="text-[11px] font-semibold text-emerald-400 mt-4 flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                {t.viewReportsAction} &rarr;
              </span>
            </button>

            {/* AI Operations Advisor */}
            <button
              onClick={() => navigate('/agent')}
              className="glass p-5 rounded-2xl border border-accent-500/30 hover:border-accent-400 text-left transition-all group hover:bg-white/5 cursor-pointer shadow-lg hover:shadow-accent-500/20 active:scale-95 flex flex-col justify-between relative overflow-hidden min-h-[160px]"
            >
              <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[9px] font-bold bg-accent-500/20 text-accent-300 border border-accent-500/30">
                Grounded AI
              </div>
              <div>
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-500 to-indigo-600 text-white flex items-center justify-center text-xl mb-3 group-hover:scale-110 transition-transform shadow-md shadow-accent-500/30">
                  ⚡
                </div>
                <h3 className="font-bold text-white text-sm mb-1">{t.aiAdvisor}</h3>
                <p className="text-xs text-surface-200/70 leading-relaxed">
                  Ask natural language questions on live wait times, bottlenecks, and staffing.
                </p>
              </div>
              <span className="text-[11px] font-semibold text-accent-400 mt-4 flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                {t.consultAdvisorAction} &rarr;
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* Features preview */}
      <section className="px-4 sm:px-6 pb-12 sm:pb-16">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-center text-xl sm:text-2xl font-bold text-white mb-6 sm:mb-8">
            {t.howItWorks}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger">
            <FeatureCard
              step="1"
              title={t.feature1Title}
              description={t.feature1Desc}
            />
            <FeatureCard
              step="2"
              title={t.feature2Title}
              description={t.feature2Desc}
            />
            <FeatureCard
              step="3"
              title={t.feature3Title}
              description={t.feature3Desc}
            />
            <FeatureCard
              step="4"
              title={t.feature4Title}
              description={t.feature4Desc}
            />
          </div>
        </div>
      </section>

      {/* Help Modal — Fully translated, no Roman Urdu */}
      {showHelpModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in" role="dialog" aria-modal="true">
          <div className="bg-surface-900 border border-white/15 rounded-3xl max-w-md w-full p-6 text-left shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-4">
              <h3 className="text-lg sm:text-xl font-bold text-white">{t.madad}</h3>
              <button
                type="button"
                onClick={() => setShowHelpModal(false)}
                className="w-8 h-8 rounded-lg glass-light flex items-center justify-center text-surface-200 hover:text-white cursor-pointer"
                aria-label="Close Help"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3.5 my-4 text-xs text-surface-200/80 leading-relaxed">
              <div className="p-3.5 rounded-2xl bg-surface-950/80 border border-white/5">
                <span className="font-bold text-primary-400 block mb-1 text-sm">{t.helpStep1Title}</span>
                {t.helpStep1Desc}
              </div>
              <div className="p-3.5 rounded-2xl bg-surface-950/80 border border-white/5">
                <span className="font-bold text-accent-400 block mb-1 text-sm">{t.helpStep2Title}</span>
                {t.helpStep2Desc}
              </div>
              <div className="p-3.5 rounded-2xl bg-surface-950/80 border border-white/5">
                <span className="font-bold text-success-400 block mb-1 text-sm">{t.helpStep3Title}</span>
                {t.helpStep3Desc}
              </div>
            </div>

            <button
              onClick={() => setShowHelpModal(false)}
              className="w-full py-3.5 rounded-xl btn-primary font-bold text-xs cursor-pointer shadow-lg"
            >
              {t.close}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/* ===== Sub-components ===== */

interface ActionCardProps {
  id: string
  icon: React.ReactNode
  title: string
  description: string
  gradient: string
  hoverGlow: string
  onClick?: () => void
}

function ActionCard({
  id,
  icon,
  title,
  description,
  gradient,
  hoverGlow,
  onClick,
}: ActionCardProps) {
  return (
    <button
      id={id}
      onClick={onClick}
      className={`
        glass-card p-6 sm:p-7 flex flex-col items-center gap-4 text-center
        cursor-pointer group animate-slide-up min-h-[200px] justify-between
        hover:${hoverGlow}
      `}
      tabIndex={0}
      aria-label={title}
    >
      <div
        className={`
        w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br ${gradient}
        flex items-center justify-center text-white
        shadow-lg group-hover:scale-110 transition-transform duration-300
      `}
      >
        {icon}
      </div>
      <div>
        <h3 className="text-lg sm:text-xl font-bold text-white mb-2">{title}</h3>
        <p className="text-xs text-surface-200/70 leading-relaxed">{description}</p>
      </div>
    </button>
  )
}

interface FeatureCardProps {
  step: string
  title: string
  description: string
}

function FeatureCard({ step, title, description }: FeatureCardProps) {
  return (
    <div className="glass-card p-4 sm:p-5 animate-slide-up">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white text-xs sm:text-sm font-bold mb-3">
        {step}
      </div>
      <h3 className="text-sm font-semibold text-white mb-1.5">{title}</h3>
      <p className="text-xs text-surface-200/70 leading-relaxed">{description}</p>
    </div>
  )
}
