import { useState, useEffect, useRef } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useLanguage } from '../context/LanguageContext'

/**
 * QueueWise AI — Root Application Layout
 *
 * Provides a responsive public-service layout:
 * - Desktop: Full inline top navigation bar with all 7 links visible.
 * - Mobile: Top-right hamburger menu with drawer navigation.
 * - Bilingual language switcher (English & Urdu).
 * - Live system status telemetry.
 * - Zero bottom navigation bars and zero voice assistance.
 */
export function Layout() {
  const { t, lang, toggleLang, isRTL } = useLanguage()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const hamburgerBtnRef = useRef<HTMLButtonElement>(null)
  const location = useLocation()

  // Close menu on location change
  useEffect(() => {
    setIsMenuOpen(false)
  }, [location.pathname])

  // Close menu on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMenuOpen) {
        setIsMenuOpen(false)
        hamburgerBtnRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isMenuOpen])

  // Prevent background scroll when menu is open on mobile
  useEffect(() => {
    if (isMenuOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isMenuOpen])

  const navItems = [
    {
      to: '/',
      label: t.home,
      badge: null,
      icon: (
        <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
    },
    {
      to: '/kiosk',
      label: t.kiosk,
      badge: null,
      icon: (
        <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
        </svg>
      ),
    },
    {
      to: '/track',
      label: t.trackToken,
      badge: 'Live',
      icon: (
        <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      to: '/staff',
      label: t.staffDesk,
      badge: null,
      icon: (
        <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      ),
    },
    {
      to: '/simulation',
      label: t.simulationLab,
      badge: 'M/M/c',
      icon: (
        <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
        </svg>
      ),
    },
    {
      to: '/analytics',
      label: t.analytics,
      badge: null,
      icon: (
        <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
    },
    {
      to: '/agent',
      label: t.aiAdvisor,
      badge: 'AI',
      icon: (
        <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
    },
  ]

  return (
    <div className={`min-h-screen bg-mesh flex flex-col text-surface-100 ${isRTL ? 'font-urdu' : ''}`}>
      {/* Header */}
      <header className="glass sticky top-0 z-40 px-3 py-2.5 sm:px-6 sm:py-3 border-b border-white/10">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-2">
          {/* Brand Logo */}
          <NavLink
            to="/"
            className="flex items-center gap-2.5 group shrink-0 min-h-[44px]"
            id="nav-logo"
            aria-label="QueueWise AI Home"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-lg shadow-primary-500/20 group-hover:scale-105 transition-transform shrink-0">
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
            <div className="hidden sm:block">
              <span className="text-lg font-black tracking-tight gradient-text">
                QueueWise
              </span>
              <span className="text-surface-200 font-bold ml-1 text-xs bg-white/10 px-1.5 py-0.5 rounded-md border border-white/10">
                AI
              </span>
            </div>
          </NavLink>

          {/* ===== Desktop Navigation — Visible on lg+ screens ===== */}
          <nav className="hidden lg:flex items-center gap-1" aria-label="Main Navigation (Desktop)">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `px-3 py-2 rounded-xl flex items-center gap-2 text-[13px] font-medium transition-all duration-200 whitespace-nowrap ${
                    isActive
                      ? 'bg-gradient-to-r from-primary-600/30 to-accent-600/20 text-white border border-primary-400/40 shadow-sm shadow-primary-500/10 font-bold'
                      : 'text-surface-200/70 hover:text-white hover:bg-white/5 border border-transparent'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span className={isActive ? 'text-primary-300' : 'text-surface-200/50'}>
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                    {item.badge && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-accent-500/20 text-accent-300 border border-accent-500/30 leading-none">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Right Header Controls */}
          <div className="flex items-center gap-2">
            {/* System Status Pill — Hidden on small screens */}
            <div
              className="hidden xl:flex items-center gap-1.5 text-xs text-surface-200/80 px-2.5 py-1.5 rounded-xl bg-white/5 border border-white/10"
              title="System Status"
            >
              <span className="w-2 h-2 rounded-full bg-success-400 animate-pulse" />
              <span className="font-medium text-[11px]">{t.systemOnline}</span>
            </div>

            {/* Language Switcher Button */}
            <button
              type="button"
              onClick={toggleLang}
              className="min-h-[40px] px-2.5 py-1.5 rounded-xl glass-light border border-white/10 hover:border-accent-400/40 hover:bg-white/10 text-xs font-bold text-surface-200 hover:text-white transition-all cursor-pointer flex items-center gap-1.5 shadow-sm active:scale-95"
              title="Toggle English / اردو"
              aria-label="Toggle Language (English / Urdu)"
            >
              <svg className="w-4 h-4 text-accent-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
              </svg>
              <span className="font-semibold hidden sm:inline">{lang === 'en' ? 'اردو' : 'English'}</span>
            </button>

            {/* Hamburger Menu Button — Visible ONLY on mobile (below lg) */}
            <button
              ref={hamburgerBtnRef}
              type="button"
              onClick={() => setIsMenuOpen((prev) => !prev)}
              className="lg:hidden min-h-[44px] min-w-[44px] p-2.5 rounded-xl glass border border-white/15 hover:border-primary-400/50 hover:bg-white/10 text-white transition-all cursor-pointer flex items-center justify-center shadow-lg shadow-primary-500/10 active:scale-95 focus-visible:ring-2 focus-visible:ring-primary-400"
              aria-label={isMenuOpen ? t.closeMenu : t.menuTitle}
              aria-expanded={isMenuOpen}
              aria-controls="navigation-drawer"
              id="hamburger-menu-button"
            >
              {isMenuOpen ? (
                /* Close Icon */
                <svg className="w-6 h-6 text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                /* 3 Horizontal Lines (Hamburger) */
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* ===== Mobile Navigation Drawer & Backdrop (only renders when open) ===== */}
      {isMenuOpen && (
        <div className="fixed inset-0 z-50 flex justify-end animate-fade-in lg:hidden" id="navigation-drawer" role="dialog" aria-modal="true">
          {/* Backdrop Overlay */}
          <div
            className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
            onClick={() => setIsMenuOpen(false)}
            aria-hidden="true"
          />

          {/* Drawer Panel */}
          <div
            ref={menuRef}
            className={`relative w-full max-w-sm h-full bg-surface-950/95 border-l border-white/15 backdrop-blur-2xl shadow-2xl flex flex-col justify-between z-10 overflow-y-auto animate-slide-up ${
              isRTL ? 'border-l-0 border-r text-right' : 'text-left'
            }`}
          >
            {/* Drawer Header */}
            <div>
              <div className="p-5 border-b border-white/10 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-lg shadow-primary-500/30 shrink-0">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
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
                    <h2 className="text-base font-extrabold text-white">QueueWise AI</h2>
                    <p className="text-xs text-surface-200/60 font-medium">{t.menuTitle}</p>
                  </div>
                </div>

                {/* Close Drawer Button */}
                <button
                  type="button"
                  onClick={() => setIsMenuOpen(false)}
                  className="min-h-[44px] min-w-[44px] p-2.5 rounded-xl glass-light border border-white/10 hover:border-white/25 hover:bg-white/10 text-surface-200 hover:text-white transition-all cursor-pointer flex items-center justify-center"
                  aria-label={t.closeMenu}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Navigation Items (All 7 Pages) */}
              <nav className="p-4 space-y-2" aria-label="Main Navigation (Mobile)">
                {navItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/'}
                    onClick={() => setIsMenuOpen(false)}
                    className={({ isActive }) =>
                      `min-h-[48px] px-4 py-3.5 rounded-2xl flex items-center justify-between gap-3 transition-all duration-200 cursor-pointer ${
                        isActive
                          ? 'bg-gradient-to-r from-primary-600/30 to-accent-600/20 text-white border-2 border-primary-400/50 shadow-lg shadow-primary-500/15 font-bold'
                          : 'glass-light border border-white/5 text-surface-200/80 hover:text-white hover:border-white/20 hover:bg-white/5 font-medium'
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <div className="flex items-center gap-3.5">
                          <span className={`w-5 h-5 ${isActive ? 'text-primary-300' : 'text-surface-200/60'}`}>
                            {item.icon}
                          </span>
                          <span className="text-sm tracking-wide">{item.label}</span>
                        </div>

                        <div className="flex items-center gap-2">
                          {item.badge && (
                            <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-accent-500/20 text-accent-300 border border-accent-500/30">
                              {item.badge}
                            </span>
                          )}
                          {isActive && (
                            <span className="w-2 h-2 rounded-full bg-primary-400 shadow-sm shadow-primary-400" />
                          )}
                        </div>
                      </>
                    )}
                  </NavLink>
                ))}
              </nav>
            </div>

            {/* Drawer Footer Controls */}
            <div className="p-5 border-t border-white/10 space-y-3">
              {/* Language Switch inside menu */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 text-xs">
                <span className="text-surface-200/70 font-medium">
                  {lang === 'en' ? 'Language: English' : 'زبان: اردو'}
                </span>
                <button
                  type="button"
                  onClick={toggleLang}
                  className="px-3 py-1.5 rounded-lg btn-primary text-xs font-bold shadow-md cursor-pointer"
                >
                  {lang === 'en' ? 'اردو میں دیکھیں' : 'Switch to English'}
                </button>
              </div>

              {/* Status pill */}
              <div className="flex items-center justify-between text-xs text-surface-200/50 px-2">
                <span>{t.brandName}</span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-success-400 animate-pulse" />
                  {t.systemOnline}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area — No bottom bar spacing needed */}
      <main className="flex-1 pb-8 sm:pb-12 overflow-x-hidden">
        <Outlet />
      </main>

      {/* Responsive Footer */}
      <footer className="px-4 py-6 sm:px-6 border-t border-white/5 text-center mt-auto">
        <p className="text-xs text-surface-200/60 font-medium">
          QueueWise AI — {t.tagline}
        </p>
        <p className="text-[11px] text-surface-200/40 mt-1">
          SC-03 Public Service Queue Optimizer • Hackathon Prototype
        </p>
      </footer>
    </div>
  )
}
