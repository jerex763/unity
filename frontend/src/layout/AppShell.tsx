import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'

const navItems = [
  { to: '/', label: 'nav.home', icon: '⌂', end: true },
  { to: '/people', label: 'nav.people', icon: '◉', end: false },
  { to: '/events', label: 'nav.events', icon: '◇', end: false },
  { to: '/follow-ups', label: 'nav.followUps', icon: '↗', end: false },
] as const

export function AppShell() {
  const { t } = useTranslation()
  const { session, logout } = useAuth()

  if (!session) return null

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink className="brand" to="/">
          <span className="brand-mark small" aria-hidden="true">
            U
          </span>
          <span>{t('appName')}</span>
        </NavLink>
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
              <span aria-hidden="true">{item.icon}</span>
              <span>{t(item.label)}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="page-content">
        <Outlet />
      </div>

      <nav className="bottom-nav" aria-label={t('shell.menu')}>
        {navItems.map((item) => (
          <NavLink
            className={({ isActive }) => (isActive ? 'active' : undefined)}
            end={item.end}
            key={item.to}
            to={item.to}
          >
            <span aria-hidden="true">{item.icon}</span>
            <small>{t(item.label)}</small>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
