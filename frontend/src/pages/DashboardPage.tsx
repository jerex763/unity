import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { apiRequest } from '../api/client'
import { useAuth } from '../auth/useAuth'
import type { FollowUp } from '../followups/types'

const cards = [
  {
    title: 'dashboard.directoryTitle',
    body: 'dashboard.directoryBody',
    icon: 'P',
    to: '/people',
  },
  {
    title: 'dashboard.eventsTitle',
    body: 'dashboard.eventsBody',
    icon: 'E',
    to: '/events',
  },
  {
    title: 'dashboard.followUpsTitle',
    body: 'dashboard.followUpsBody',
    icon: 'F',
    to: '/follow-ups',
  },
] as const

export function DashboardPage() {
  const { t } = useTranslation()
  const { session } = useAuth()
  const name = session?.user.first_name || session?.user.username || ''
  const canWorkFollowUps = session?.membership.role !== 'member'
  const [followUps, setFollowUps] = useState<FollowUp[]>([])
  const [followUpsError, setFollowUpsError] = useState('')
  const [isLoadingFollowUps, setIsLoadingFollowUps] = useState(canWorkFollowUps)

  useEffect(() => {
    if (!canWorkFollowUps) return
    let active = true
    void apiRequest<FollowUp[]>('/follow-ups/mine/')
      .then((items) => {
        if (active) setFollowUps(items)
      })
      .catch(() => {
        if (active) setFollowUpsError(t('dashboard.myFollowUpsError'))
      })
      .finally(() => {
        if (active) setIsLoadingFollowUps(false)
      })
    return () => {
      active = false
    }
  }, [canWorkFollowUps, t])

  const today = new Date().toLocaleDateString('en-CA')

  function dueLabel(dueAt: string | null) {
    if (!dueAt) return t('dashboard.noDueDate')
    if (dueAt < today) return t('dashboard.overdue')
    if (dueAt === today) return t('dashboard.dueToday')
    return t('dashboard.dueDate', {
      date: new Intl.DateTimeFormat(undefined, {
        day: 'numeric',
        month: 'short',
      }).format(new Date(`${dueAt}T12:00:00`)),
    })
  }

  return (
    <main>
      <section className="page-heading">
        <p className="eyebrow">{t('dashboard.eyebrow')}</p>
        <h1>{t('dashboard.greeting', { name })}</h1>
        <p>{t('dashboard.intro')}</p>
      </section>

      {canWorkFollowUps ? (
        <section
          className="my-follow-ups"
          aria-labelledby="my-follow-ups-title"
        >
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">{t('dashboard.myFollowUpsEyebrow')}</p>
              <h2 id="my-follow-ups-title">{t('dashboard.followUpsTitle')}</h2>
            </div>
            <Link className="card-link" to="/follow-ups">
              {t('dashboard.openFollowUps')}
            </Link>
          </div>
          {isLoadingFollowUps ? <p>{t('dashboard.loadingFollowUps')}</p> : null}
          {followUpsError ? (
            <p className="form-error" role="alert">
              {followUpsError}
            </p>
          ) : null}
          {!isLoadingFollowUps && !followUpsError && !followUps.length ? (
            <div className="my-follow-ups-empty">
              <strong>{t('dashboard.myFollowUpsEmptyTitle')}</strong>
              <p>{t('dashboard.myFollowUpsEmptyBody')}</p>
            </div>
          ) : null}
          {followUps.length ? (
            <div className="my-follow-up-list">
              {followUps.map((item) => {
                const isOverdue = Boolean(item.due_at && item.due_at < today)
                return (
                  <article className="my-follow-up-row" key={item.id}>
                    <div>
                      <h3>{item.person.full_name}</h3>
                      <p>
                        {t(`followUps.sources.${item.source}`)} ·{' '}
                        {t(`followUps.statuses.${item.status}`)}
                      </p>
                    </div>
                    <span
                      className={isOverdue ? 'due-chip overdue' : 'due-chip'}
                    >
                      {dueLabel(item.due_at)}
                    </span>
                    <div className="my-follow-up-actions">
                      {item.person.phone ? (
                        <a href={`tel:${item.person.phone}`}>
                          {t('followUps.call')}
                        </a>
                      ) : null}
                      <Link to="/follow-ups">
                        {t('dashboard.openFollowUp', {
                          name: item.person.full_name,
                        })}
                      </Link>
                    </div>
                  </article>
                )
              })}
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="dashboard-grid" aria-label={t('dashboard.shortcuts')}>
        {cards.map((card) => (
          <article className="dashboard-card" key={card.title}>
            <span className="card-icon" aria-hidden="true">
              {card.icon}
            </span>
            <div>
              <h2>{t(card.title)}</h2>
              <p>{t(card.body)}</p>
              {card.to ? (
                <Link className="card-link" to={card.to}>
                  {card.to === '/events'
                    ? t('dashboard.openEvents')
                    : card.to === '/follow-ups'
                      ? t('dashboard.openFollowUps')
                      : t('dashboard.openDirectory')}
                </Link>
              ) : (
                <span className="chip">{t('dashboard.comingSoon')}</span>
              )}
            </div>
          </article>
        ))}
      </section>
    </main>
  )
}
