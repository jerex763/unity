import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

export function NotFoundPage() {
  const { t } = useTranslation()
  return (
    <main className="empty-state">
      <p className="eyebrow">404</p>
      <h1>{t('notFound.title')}</h1>
      <p>{t('notFound.body')}</p>
      <Link className="primary-button inline" to="/">
        {t('notFound.action')}
      </Link>
    </main>
  )
}
