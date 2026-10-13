import { Outlet, NavLink } from 'react-router-dom'
import { useLanguage } from '../context/LanguageContext'

/**
 * Root layout with persistent navigation shell.
 * Wraps all pages and provides consistent responsive app structure,
 * mobile navigation bar, and bilingual language toggle.
 */
export function Layout() {
  const { t, lang, toggleLang, isRTL } = useLanguage()

  const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all duration-200 ${
      isActive
        ? 'bg-primary-500/20 text-primary-300 border border-primary-500/30'
        : 'text-surface-200/80 hover:text-white hover:bg-white/5'
    }`

  const mobileNavClasses = ({ isActive }: { isActive: boolean }) =>
    `flex-1 py-3 flex flex-col items-center justify-center gap-1 text-[11px] font-semibold transition-colors ${
      isActive ? 'text-primary-400 bg-primary-500/10' : 'text-surface-200/60 hover:text-white'
    }`

  return (
    <div className={`min-h-screen bg-mesh flex flex-col ${isRTL ? 'font-urdu' : ''}`}>
      {/* Header */}
      <header className="glass sticky top-0 z-50 px-4 py-3 sm:px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-2.5 group shrink-0" id="nav-logo">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-lg group-hover:shadow-primary-500/30 transition-shadow">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 3h5v5" />
                <path d="M8 3H3v5" />
                <path d="M12 22v-6" />
                <path d="M12 13V7" />
                <circle cx="12" cy="4" r="1" fill="white" />
                <path d="M21 3l-9 9" />
                <path d="M3 3l9 9" />
              </svg>
            </div>
            <div>
              <span className="text-lg font-black tracking-tight gradient-text">
                QueueWise
              </span>
              <span className="text-surface-200 font-semibold ml-1 text-sm">
                AI
              </span>
            </div>
          </NavLink>

          {/* Desktop Navigation */}
          <nav className="hidden sm:flex items-center gap-2" id="nav-main">
            <NavLink to="/" className={navLinkClasses}>
              {t.home}
            </NavLink>
            <NavLink to="/kiosk" className={navLinkClasses}>
              {t.kiosk}
            </NavLink>
            <NavLink to="/track" className={navLinkClasses}>
              {t.trackToken}
            </NavLink>
          </nav>

          {/* Right Controls: Language toggle + Status indicator */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Language Switcher */}
            <button
              type="button"
              onClick={toggleLang}
              className="px-3 py-1.5 rounded-xl glass-light border border-white/10 hover:border-white/20 text-xs font-bold text-accent-300 transition-all cursor-pointer flex items-center gap-1.5 shadow-sm"
              title="Toggle English / Urdu"
              aria-label="Toggle Language"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
              </svg>
              <span>{lang === 'en' ? 'اردو' : 'English'}</span>
            </button>

            {/* Status indicator */}
            <div className="flex items-center gap-1.5 text-xs text-surface-200/80 px-2 py-1 rounded-lg bg-white/5 border border-white/5">
              <span className="w-2 h-2 rounded-full bg-success-400 animate-pulse" />
              <span className="hidden md:inline font-medium">{t.systemOnline}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 pb-16 sm:pb-6">
        <Outlet />
      </main>

      {/* Mobile Bottom Navigation Bar */}
      <div className="sm:hidden fixed bottom-0 left-0 right-0 z-40 glass border-t border-white/10 flex items-center justify-around">
        <NavLink to="/" className={mobileNavClasses}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          <span>{t.home}</span>
        </NavLink>
        <NavLink to="/kiosk" className={mobileNavClasses}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
          </svg>
          <span>{t.kiosk}</span>
        </NavLink>
        <NavLink to="/track" className={mobileNavClasses}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{t.trackToken}</span>
        </NavLink>
      </div>

      {/* Footer */}
      <footer className="hidden sm:block px-4 py-6 sm:px-6 text-center">
        <p className="text-xs text-surface-200/50">
          QueueWise AI — {t.tagline}
        </p>
        <p className="text-xs text-surface-200/30 mt-1">
          SC-03 Public Service Queue Optimizer • Hackathon Prototype
        </p>
      </footer>
    </div>
  )
}
