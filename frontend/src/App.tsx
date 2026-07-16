import { Navigate, Route, Routes } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import { useAuth } from './auth/useAuth'
import { LoginPage } from './auth/LoginPage'
import { AppShell } from './layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { NotFoundPage } from './pages/NotFoundPage'

function ProtectedShell() {
  const { t } = useTranslation()
  const { isLoading, session } = useAuth()
  if (isLoading) return <div className="loading-screen">{t('loading')}</div>
  if (!session) return <Navigate replace to="/login" />
  return <AppShell />
}

function PlaceholderRoute() {
  return <Navigate replace to="/" />
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="people" element={<PlaceholderRoute />} />
        <Route path="events" element={<PlaceholderRoute />} />
        <Route path="follow-ups" element={<PlaceholderRoute />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
