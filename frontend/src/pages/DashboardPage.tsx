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
  const name = session?.user.first_name.trim() || ''
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

  function dueLabel(item: FollowUp) {
    if (!item.due_at) return t('dashboard.noDueDate')
    if (item.attention?.overdue) return t('dashboard.overdue')
    if (item.attention?.due_today) return t('dashboard.dueToday')
    return t('dashboard.dueDate', {
      date: new Intl.DateTimeFormat('en-AU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        timeZone: 'UTC',
      }).format(new Date(`${item.due_at}T00:00:00Z`)),
    })
  }

  return (
    <main>
      <section className="page-heading">
        <p className="eyebrow">{t('dashboard.eyebrow')}</p>
        <h1>
          {name
            ? t('dashboard.greeting', { name })
            : t('dashboard.greetingWithoutName')}
        </h1>
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
                const isOverdue = Boolean(item.attention?.overdue)
                return (
                  <article className="my-follow-up-row" key={item.id}>
                    <div>
                      <h3>{item.person.full_name}</h3>
                      <p>
                        {t(`followUps.sources.${item.source}`)} ·{' '}
                        {t(`followUps.statuses.${item.status}`)}
                      </p>
                      {item.attention ? (
                        <>
                          <div className="follow-up-attention">
                            {(
                              [
                                'escalated',
                                'overdue',
                                'due_today',
                                'stale',
                                'unassigned_too_long',
                                'no_action',
                              ] as const
                            ).map((flag) =>
                              item.attention?.[flag] ? (
                                <span
                                  className={`attention-chip attention-${flag}`}
                                  key={flag}
                                >
                                  {t(`followUps.attention.${flag}`)}
                                </span>
                              ) : null,
                            )}
                          </div>
                          <p>
                            <strong>
                              {t('followUps.attention.nextAction')}:
                            </strong>{' '}
                            {item.attention.next_action}
                          </p>
                        </>
                      ) : null}
                    </div>
                    <span
                      className={isOverdue ? 'due-chip overdue' : 'due-chip'}
                    >
                      {dueLabel(item)}
                    </span>
                    <div className="my-follow-up-actions">
                      {item.person.phone ? (
                        <a
                          className="secondary-button dashboard-follow-up-action"
                          href={`tel:${item.person.phone}`}
                        >
                          {t('followUps.call')}
                        </a>
                      ) : null}
                      <Link
                        className="primary-button dashboard-follow-up-action"
                        to="/follow-ups"
                      >
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
