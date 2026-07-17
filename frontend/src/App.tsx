import { Navigate, Route, Routes } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import { useAuth } from './auth/useAuth'
import { LoginPage } from './auth/LoginPage'
import { AppShell } from './layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { DirectoryPage } from './people/DirectoryPage'

function ProtectedShell() {
  const { t } = useTranslation()
  const { isLoading, session } = useAuth()
  if (isLoading) return <div className="loading-screen">{t('loading')}</div>
  if (!session) return <Navigate replace to="/login" />
  return <AppShell />
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="people" element={<DirectoryPage />} />
        <Route path="events" element={<Navigate replace to="/" />} />
        <Route path="follow-ups" element={<Navigate replace to="/" />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
