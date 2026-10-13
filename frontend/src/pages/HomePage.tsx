import { useState, useEffect } from 'react'

/**
 * QueueWise AI — Citizen Home Page
 *
 * The primary landing page with three main actions:
 * 1. Token Lo — Get a Token
 * 2. Mera Token — Check My Token
 * 3. Madad — Get Help
 *
 * Also shows a backend connectivity check and animated hero.
 */
export function HomePage() {
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking')

  useEffect(() => {
    fetch('/health')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'healthy') {
          setBackendStatus('online')
        } else {
          setBackendStatus('offline')
        }
      })
      .catch(() => setBackendStatus('offline'))
  }, [])

  return (
    <div className="animate-fade-in">
      {/* Hero Section */}
      <section className="px-4 sm:px-6 pt-12 pb-16 sm:pt-20 sm:pb-24">
        <div className="max-w-4xl mx-auto text-center">
          {/* Floating badge */}
          <div className="inline-flex items-center gap-2 glass-light rounded-full px-4 py-2 mb-8 animate-float">
            <span className="w-2 h-2 rounded-full bg-accent-400" />
            <span className="text-sm text-surface-200 font-medium">
              Public Service Queue Optimizer
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
            Get your digital token, track your queue position, and know exactly
            when it's your turn — at hospitals, banks, and government offices.
          </p>

          {/* Three primary action cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 max-w-3xl mx-auto stagger">
            {/* Get a Token */}
            <ActionCard
              id="action-get-token"
              icon={
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="2" width="20" height="20" rx="3" />
                  <path d="M12 8v8" />
                  <path d="M8 12h8" />
                </svg>
              }
              title="Token Lo"
              subtitle="Get a Token"
              description="Join the queue for any service"
              gradient="from-primary-600 to-primary-700"
              hoverGlow="shadow-primary-500/30"
            />

            {/* Check My Token */}
            <ActionCard
              id="action-check-token"
              icon={
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v6l4 2" />
                </svg>
              }
              title="Mera Token"
              subtitle="Check My Token"
              description="View your queue position & wait"
              gradient="from-accent-600 to-accent-700"
              hoverGlow="shadow-accent-500/30"
            />

            {/* Get Help */}
            <ActionCard
              id="action-help"
              icon={
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                  <path d="M12 17h.01" />
                </svg>
              }
              title="Madad"
              subtitle="Get Help"
              description="Instructions & voice assistance"
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
              <div className={`w-3 h-3 rounded-full ${
                backendStatus === 'online' ? 'bg-success-400 animate-pulse' :
                backendStatus === 'offline' ? 'bg-danger-400' :
                'bg-warning-400 animate-pulse'
              }`} />
              <span className="text-sm font-medium text-surface-200">
                Backend API
              </span>
            </div>
            <span className={`text-xs font-semibold px-3 py-1 rounded-full ${
              backendStatus === 'online'
                ? 'bg-success-400/10 text-success-400'
                : backendStatus === 'offline'
                ? 'bg-danger-400/10 text-danger-400'
                : 'bg-warning-400/10 text-warning-400'
            }`}>
              {backendStatus === 'online' ? '● Connected' :
               backendStatus === 'offline' ? '○ Offline' :
               '◌ Checking...'}
            </span>
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
              title="Get Your Token"
              description="Select a service and receive a unique digital token with a QR code."
            />
            <FeatureCard
              step="2"
              title="Track Your Position"
              description="See your real-time queue position and dynamic wait-time estimate."
            />
            <FeatureCard
              step="3"
              title="Get Notified"
              description="Receive alerts when your turn is approaching — no more guessing."
            />
            <FeatureCard
              step="4"
              title="Get Served"
              description="When called, head to the counter and get the service you need."
            />
          </div>
        </div>
      </section>
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
}

function ActionCard({ id, icon, title, subtitle, description, gradient, hoverGlow }: ActionCardProps) {
  return (
    <button
      id={id}
      className={`
        glass-card p-6 sm:p-8 flex flex-col items-center gap-4 text-center
        cursor-pointer group animate-slide-up
        hover:${hoverGlow}
      `}
      tabIndex={0}
      aria-label={`${title} — ${subtitle}`}
    >
      <div className={`
        w-16 h-16 rounded-2xl bg-gradient-to-br ${gradient}
        flex items-center justify-center text-white
        shadow-lg group-hover:scale-110 transition-transform duration-300
      `}>
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
