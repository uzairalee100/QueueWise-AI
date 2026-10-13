import { Outlet } from 'react-router-dom'

/**
 * Root layout with persistent navigation shell.
 * Wraps all pages and provides consistent app structure.
 */
export function Layout() {
  return (
    <div className="min-h-screen bg-mesh flex flex-col">
      {/* Header */}
      <header className="glass sticky top-0 z-50 px-4 py-3 sm:px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Logo */}
          <a href="/" className="flex items-center gap-3 group" id="nav-logo">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-lg group-hover:shadow-primary-500/30 transition-shadow">
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
              <h1 className="text-lg font-bold tracking-tight">
                <span className="gradient-text">QueueWise</span>
                <span className="text-surface-200 font-medium ml-1">AI</span>
              </h1>
            </div>
          </a>

          {/* Navigation — will expand with more pages */}
          <nav className="hidden sm:flex items-center gap-1" id="nav-main">
            <a
              href="/"
              className="px-3 py-2 rounded-lg text-sm font-medium text-surface-200 hover:text-white hover:bg-white/5 transition-colors"
            >
              Home
            </a>
            {/* Future nav links */}
          </nav>

          {/* Status indicator */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs text-surface-200">
              <span className="w-2 h-2 rounded-full bg-success-400 animate-pulse" />
              <span className="hidden sm:inline">System Online</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="px-4 py-6 sm:px-6 text-center">
        <p className="text-xs text-surface-200/50">
          QueueWise AI — Smarter Queues. Less Waiting. Better Public Services.
        </p>
        <p className="text-xs text-surface-200/30 mt-1">
          SC-03 Public Service Queue Optimizer • Hackathon Prototype
        </p>
      </footer>
    </div>
  )
}
