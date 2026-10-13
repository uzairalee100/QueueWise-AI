import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLanguage } from '../context/LanguageContext'

/**
 * QueueWise AI — Citizen Home Page
 *
 * The primary landing page with three main actions:
 * 1. Token Lo — Get a Token -> Navigates to /kiosk
 * 2. Mera Token — Check My Token -> Navigates to /track
 * 3. Madad — Get Help
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
      <section className="px-4 sm:px-6 pt-12 pb-16 sm:pt-20 sm:pb-24">
        <div className="max-w-4xl mx-auto text-center">
          {/* Floating badge */}
          <div className="inline-flex items-center gap-2 glass-light rounded-full px-4 py-2 mb-8 animate-float">
            <span className="w-2 h-2 rounded-full bg-accent-400" />
            <span className="text-sm text-surface-200 font-medium">
              SC-03 Public Service Queue Optimizer
            </span>
          </div>

          {/* Main headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight mb-6 leading-tight">
            <span className="gradient-text">Smarter Queues.</span>
            <br />
            <span className="text-white">Less Waiting.</span>
            <br />
            <span className="text-surface-200 font-semibold text-3xl sm:text-4xl lg:text-5xl">
              Better Public Services.
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl text-surface-200/80 max-w-2xl mx-auto mb-12 leading-relaxed">
            {t.tagline}
          </p>

          {/* Three primary action cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 max-w-3xl mx-auto stagger">
            {/* Get a Token */}
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
              subtitle={t.tokenLoSub}
              description={t.tokenLoDesc}
              gradient="from-primary-600 to-primary-700"
              hoverGlow="shadow-primary-500/30"
            />

            {/* Check My Token */}
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
              subtitle={t.meraTokenSub}
              description={t.meraTokenDesc}
              gradient="from-accent-600 to-accent-700"
              hoverGlow="shadow-accent-500/30"
            />

            {/* Get Help */}
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
              subtitle={t.madadSub}
              description={t.madadDesc}
              gradient="from-violet-600 to-violet-700"
              hoverGlow="shadow-violet-500/30"
            />
          </div>
        </div>
      </section>

      {/* Backend Status */}
      <section className="px-4 sm:px-6 pb-12">
        <div className="max-w-md mx-auto">
          <div className="glass-card p-4 flex items-center justify-between" id="backend-status">
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
              <span className="text-sm font-medium text-surface-200">
                Backend API
              </span>
            </div>
            <span
              className={`text-xs font-semibold px-3 py-1 rounded-full ${
                backendStatus === 'online'
                  ? 'bg-success-400/10 text-success-400'
                  : backendStatus === 'offline'
                  ? 'bg-danger-400/10 text-danger-400'
                  : 'bg-warning-400/10 text-warning-400'
              }`}
            >
              {backendStatus === 'online'
                ? '● Connected'
                : backendStatus === 'offline'
                ? '○ Offline'
                : '◌ Checking...'}
            </span>
          </div>
        </div>
      </section>

      {/* Operations & Supervisor Intelligence Modules */}
      <section className="px-4 sm:px-6 pb-14">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl sm:text-2xl font-bold text-white">
                Operations & Management Portal
              </h2>
              <p className="text-xs sm:text-sm text-surface-200/60 mt-0.5">
                Live staff counters, discrete simulation lab, analytics ledger, and AI operational advisor
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Staff Counter Desk */}
            <button
              onClick={() => navigate('/staff')}
              className="glass p-5 rounded-2xl border border-white/10 hover:border-primary-500/40 text-left transition-all group hover:bg-white/5 cursor-pointer shadow-lg hover:shadow-primary-500/10 active:scale-95 flex flex-col justify-between"
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
                Open Desk &rarr;
              </span>
            </button>

            {/* Simulation Lab */}
            <button
              onClick={() => navigate('/simulation')}
              className="glass p-5 rounded-2xl border border-white/10 hover:border-amber-500/40 text-left transition-all group hover:bg-white/5 cursor-pointer shadow-lg hover:shadow-amber-500/10 active:scale-95 flex flex-col justify-between"
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
                Launch Lab &rarr;
              </span>
            </button>

            {/* Operational Analytics */}
            <button
              onClick={() => navigate('/analytics')}
              className="glass p-5 rounded-2xl border border-white/10 hover:border-emerald-500/40 text-left transition-all group hover:bg-white/5 cursor-pointer shadow-lg hover:shadow-emerald-500/10 active:scale-95 flex flex-col justify-between"
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
                View Reports &rarr;
              </span>
            </button>

            {/* AI Operations Advisor */}
            <button
              onClick={() => navigate('/agent')}
              className="glass p-5 rounded-2xl border border-accent-500/30 hover:border-accent-400 text-left transition-all group hover:bg-white/5 cursor-pointer shadow-lg hover:shadow-accent-500/20 active:scale-95 flex flex-col justify-between relative overflow-hidden"
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
                Consult Advisor &rarr;
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* Features preview */}
      <section className="px-4 sm:px-6 pb-16">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-center text-2xl font-bold text-white mb-8">
            How It Works
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger">
            <FeatureCard
              step="1"
              title="1. Issue Digital Token"
              description="Pick your desired service on the touch kiosk to receive a token number & QR code."
            />
            <FeatureCard
              step="2"
              title="2. Real-Time Tracking"
              description="Open the tracker on your mobile to view live position ahead and estimated wait."
            />
            <FeatureCard
              step="3"
              title="3. Instant Notifications"
              description="Get audible and visual alerts when your turn approaches or is called."
            />
            <FeatureCard
              step="4"
              title="4. Proceed to Counter"
              description="When called, proceed to your assigned counter with zero guesswork."
            />
          </div>
        </div>
      </section>

      {/* Help Modal */}
      {showHelpModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-surface-900 border border-white/10 rounded-3xl max-w-md w-full p-6 text-left shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-2">{t.madadSub}</h3>
            <div className="space-y-4 my-4 text-xs text-surface-200/80 leading-relaxed">
              <div className="p-3 rounded-xl bg-surface-950 border border-white/5">
                <span className="font-bold text-primary-400 block mb-1">1. How to get a token?</span>
                Click "Token Lo", choose your required service (e.g. General, Pharmacy), and tap "Issue Token".
              </div>
              <div className="p-3 rounded-xl bg-surface-950 border border-white/5">
                <span className="font-bold text-accent-400 block mb-1">2. How to track my position?</span>
                Scan the QR code on your mobile phone or click "Mera Token" and enter your token number.
              </div>
              <div className="p-3 rounded-xl bg-surface-950 border border-white/5">
                <span className="font-bold text-success-400 block mb-1">3. What should I do when called?</span>
                When your screen pulses green and chimes, proceed immediately to the counter indicated on your screen.
              </div>
            </div>
            <button
              onClick={() => setShowHelpModal(false)}
              className="w-full py-3 rounded-xl btn-primary font-bold text-xs cursor-pointer"
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
  subtitle: string
  description: string
  gradient: string
  hoverGlow: string
  onClick?: () => void
}

function ActionCard({
  id,
  icon,
  title,
  subtitle,
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
        glass-card p-6 sm:p-8 flex flex-col items-center gap-4 text-center
        cursor-pointer group animate-slide-up
        hover:${hoverGlow}
      `}
      tabIndex={0}
      aria-label={`${title} — ${subtitle}`}
    >
      <div
        className={`
        w-16 h-16 rounded-2xl bg-gradient-to-br ${gradient}
        flex items-center justify-center text-white
        shadow-lg group-hover:scale-110 transition-transform duration-300
      `}
      >
        {icon}
      </div>
      <div>
        <h3 className="text-xl font-bold text-white mb-1">{title}</h3>
        <p className="text-sm font-medium text-primary-300 mb-2">{subtitle}</p>
        <p className="text-xs text-surface-200/70">{description}</p>
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
    <div className="glass-card p-5 animate-slide-up">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white text-sm font-bold mb-3">
        {step}
      </div>
      <h3 className="text-sm font-semibold text-white mb-2">{title}</h3>
      <p className="text-xs text-surface-200/70 leading-relaxed">{description}</p>
    </div>
  )
}
