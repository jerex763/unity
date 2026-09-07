import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'
import { DirectoryViewStateProvider } from '../people/DirectoryViewStateProvider'

const navItems = [
  { to: '/', label: 'nav.home', icon: 'home', end: true },
  { to: '/people', label: 'nav.people', icon: 'people', end: false },
  { to: '/events', label: 'nav.events', icon: 'calendar', end: false },
  { to: '/follow-ups', label: 'nav.followUps', icon: 'followup', end: false },
] as const

function NavIcon({ name }: { name: (typeof navItems)[number]['icon'] }) {
  const common = {
    fill: 'none',
    height: 24,
    stroke: 'currentColor',
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    strokeWidth: 1.8,
    viewBox: '0 0 24 24',
    width: 24,
  }
  if (name === 'home') {
    return (
      <svg {...common}>
        <path d="m3 10 9-7 9 7v10H7V12h10v8" />
      </svg>
    )
  }
  if (name === 'people') {
    return (
      <svg {...common}>
        <circle cx="9" cy="8" r="3" />
        <path d="M3.5 20v-2a5.5 5.5 0 0 1 11 0v2M16 5.5a3 3 0 0 1 0 5.8M17 14a5 5 0 0 1 3.5 4.8V20" />
      </svg>
    )
  }
  if (name === 'calendar') {
    return (
      <svg {...common}>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M8 3v4M16 3v4M3 10h18" />
      </svg>
    )
  }
  return (
    <svg {...common}>
      <path d="M5 19h14M7 16l4-4 3 2 4-6M16 8h2v2" />
    </svg>
  )
}

export function AppShell() {
  const { t } = useTranslation()
  const { session, logout } = useAuth()

  if (!session) return null

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-context">
          <NavLink className="brand" to="/">
            <span className="brand-mark small" aria-hidden="true">
              U
            </span>
            <span>{t('appName')}</span>
          </NavLink>
          <span
            aria-label={t('shell.churchAndRole', {
              role: session.membership.role,
              church: session.membership.church_name,
            })}
            className="mobile-account-context"
          >
            <span aria-hidden="true" className="mobile-account-church">
              {session.membership.church_name}
            </span>
            <span aria-hidden="true">·</span>
            <span aria-hidden="true" className="mobile-account-role">
              {session.membership.role}
            </span>
          </span>
        </div>
        <div className="account-block">
          <span className="account-context">
            {t('shell.roleAtChurch', {
              role: session.membership.role,
              church: session.membership.church_name,
            })}
          </span>
          <button
            className="text-button"
            onClick={() => void logout()}
            type="button"
          >
            {t('shell.signOut')}
          </button>
        </div>
      </header>

      <aside className="sidebar" aria-label={t('shell.menu')}>
        <nav>
          {navItems.map((item) => (
            <NavLink
              className={({ isActive }) =>
                isActive ? 'nav-link active' : 'nav-link'
              }
              end={item.end}
              key={item.to}
              to={item.to}
            >
              <span aria-hidden="true" className="nav-icon">
                <NavIcon name={item.icon} />
              </span>
              <span>{t(item.label)}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="page-content">
        <DirectoryViewStateProvider
          key={`${session.user.id}:${session.membership.church_id}:${session.membership.role}`}
        >
          <Outlet />
        </DirectoryViewStateProvider>
      </div>

      <nav className="bottom-nav" aria-label={t('shell.menu')}>
        {navItems.map((item) => (
          <NavLink
            className={({ isActive }) => (isActive ? 'active' : undefined)}
            end={item.end}
            key={item.to}
            to={item.to}
          >
            <span aria-hidden="true" className="nav-icon">
              <NavIcon name={item.icon} />
            </span>
            <small>{t(item.label)}</small>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
