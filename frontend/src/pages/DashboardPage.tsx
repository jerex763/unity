import { useTranslation } from 'react-i18next'

import { useAuth } from '../auth/useAuth'

const cards = [
  {
    title: 'dashboard.directoryTitle',
    body: 'dashboard.directoryBody',
    icon: 'P',
  },
  { title: 'dashboard.eventsTitle', body: 'dashboard.eventsBody', icon: 'E' },
  {
    title: 'dashboard.followUpsTitle',
    body: 'dashboard.followUpsBody',
    icon: 'F',
  },
] as const

export function DashboardPage() {
  const { t } = useTranslation()
  const { session } = useAuth()
  const name = session?.user.first_name || session?.user.username || ''

  return (
    <main>
      <section className="page-heading">
        <p className="eyebrow">{t('dashboard.eyebrow')}</p>
        <h1>{t('dashboard.greeting', { name })}</h1>
        <p>{t('dashboard.intro')}</p>
      </section>

      <section
        className="dashboard-grid"
        aria-label={t('dashboard.comingSoon')}
      >
        {cards.map((card) => (
          <article className="dashboard-card" key={card.title}>
            <span className="card-icon" aria-hidden="true">
              {card.icon}
            </span>
            <div>
              <h2>{t(card.title)}</h2>
              <p>{t(card.body)}</p>
              <span className="chip">{t('dashboard.comingSoon')}</span>
            </div>
          </article>
        ))}
      </section>
    </main>
  )
}
