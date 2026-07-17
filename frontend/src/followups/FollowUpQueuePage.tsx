import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { apiRequest } from '../api/client'
import type { FollowUp, FollowUpStatus, WorkerChoice } from './types'

const statuses: FollowUpStatus[] = [
  'new',
  'assigned',
  'in_progress',
  'connected',
  'closed',
]

type EditFields = {
  status: FollowUpStatus
  engagement: FollowUp['engagement']
  assigned_to: string
  due_at: string
  outcome: string
}

function editFields(item: FollowUp): EditFields {
  return {
    status: item.status,
    engagement: item.engagement,
    assigned_to: item.assigned_to?.toString() ?? '',
    due_at: item.due_at ?? '',
    outcome: item.outcome ?? '',
  }
}

export function FollowUpQueuePage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<FollowUp[]>([])
  const [workers, setWorkers] = useState<WorkerChoice[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [editing, setEditing] = useState<FollowUp | null>(null)
  const [fields, setFields] = useState<EditFields | null>(null)
  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    let active = true
    void Promise.all([
      apiRequest<FollowUp[]>('/follow-ups/'),
      apiRequest<WorkerChoice[]>('/follow-ups/workers/'),
    ])
      .then(([followUps, workerRows]) => {
        if (!active) return
        setItems(followUps)
        setWorkers(workerRows)
      })
      .catch(() => {
        if (active) setLoadError(t('followUps.loadError'))
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [t])

  function beginEdit(item: FollowUp) {
    setEditing(item)
    setFields(editFields(item))
    setSaveError('')
  }

  function update<Key extends keyof EditFields>(
    key: Key,
    value: EditFields[Key],
  ) {
    setFields((current) => (current ? { ...current, [key]: value } : current))
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editing || !fields) return
    setIsSaving(true)
    setSaveError('')
    try {
      const updated = await apiRequest<FollowUp>(`/follow-ups/${editing.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({
          status: fields.status,
          engagement: fields.engagement,
          assigned_to: fields.assigned_to ? Number(fields.assigned_to) : null,
          due_at: fields.due_at || null,
          outcome: fields.outcome || null,
        }),
      })
      setItems((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      )
      setEditing(null)
      setFields(null)
    } catch {
      setSaveError(t('followUps.saveError'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <main className="follow-up-page">
      <section className="page-heading">
        <p className="eyebrow">{t('followUps.eyebrow')}</p>
        <h1>{t('followUps.title')}</h1>
        <p>{t('followUps.intro')}</p>
      </section>

      {isLoading ? (
        <p className="events-loading">{t('followUps.loading')}</p>
      ) : null}
      {loadError ? (
        <p className="form-error" role="alert">
          {loadError}
        </p>
      ) : null}

      <section className="follow-up-board" aria-label={t('followUps.board')}>
        {statuses.map((status) => {
          const columnItems = items.filter((item) => item.status === status)
          return (
            <section className="follow-up-column" key={status}>
              <header>
                <h2>{t(`followUps.statuses.${status}`)}</h2>
                <span>{columnItems.length}</span>
              </header>
              <div className="follow-up-card-list">
                {columnItems.map((item) => (
                  <article className="follow-up-card" key={item.id}>
                    <div className="follow-up-card-heading">
                      <h3>{item.person.full_name}</h3>
                      <span
                        className={`engagement-chip engagement-${item.engagement}`}
                      >
                        {t(`followUps.engagement.${item.engagement}`)}
                      </span>
                    </div>
                    <p>{t(`followUps.sources.${item.source}`)}</p>
                    <dl>
                      <div>
                        <dt>{t('followUps.assignee')}</dt>
                        <dd>
                          {item.assigned_to_name ?? t('followUps.unassigned')}
                        </dd>
                      </div>
                      <div>
                        <dt>{t('followUps.due')}</dt>
                        <dd>{item.due_at ?? t('followUps.notSet')}</dd>
                      </div>
                    </dl>
                    <div className="follow-up-actions">
                      {item.person.phone ? (
                        <a href={`tel:${item.person.phone}`}>
                          {t('followUps.call')}
                        </a>
                      ) : null}
                      <button
                        className="text-button"
                        onClick={() => beginEdit(item)}
                        type="button"
                      >
                        {t('followUps.update')}
                      </button>
                    </div>
                  </article>
                ))}
                {!columnItems.length ? (
                  <p className="follow-up-column-empty">
                    {t('followUps.emptyColumn')}
                  </p>
                ) : null}
              </div>
            </section>
          )
        })}
      </section>

      {editing && fields ? (
        <section
          className="follow-up-editor"
          aria-labelledby="follow-up-editor"
        >
          <div className="profile-panel-heading">
            <div>
              <p className="eyebrow">{t('followUps.editorEyebrow')}</p>
              <h2 id="follow-up-editor">
                {t('followUps.editorTitle', {
                  name: editing.person.full_name,
                })}
              </h2>
            </div>
            <button
              className="text-button"
              onClick={() => setEditing(null)}
              type="button"
            >
              {t('followUps.cancel')}
            </button>
          </div>
          <form className="follow-up-form" onSubmit={save}>
            <label>
              <span>{t('followUps.status')}</span>
              <select
                onChange={(event) =>
                  update('status', event.target.value as FollowUpStatus)
                }
                value={fields.status}
              >
                {statuses.map((status) => (
                  <option key={status} value={status}>
                    {t(`followUps.statuses.${status}`)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{t('followUps.engagementLabel')}</span>
              <select
                onChange={(event) =>
                  update(
                    'engagement',
                    event.target.value as FollowUp['engagement'],
                  )
                }
                value={fields.engagement}
              >
                {(['possible', 'probable', 'likely'] as const).map((value) => (
                  <option key={value} value={value}>
                    {t(`followUps.engagement.${value}`)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{t('followUps.assignee')}</span>
              <select
                onChange={(event) => update('assigned_to', event.target.value)}
                value={fields.assigned_to}
              >
                <option value="">{t('followUps.unassigned')}</option>
                {workers.map((worker) => (
                  <option key={worker.id} value={worker.id}>
                    {worker.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{t('followUps.due')}</span>
              <input
                onChange={(event) => update('due_at', event.target.value)}
                type="date"
                value={fields.due_at}
              />
            </label>
            <label className="wide-field">
              <span>{t('followUps.outcome')}</span>
              <textarea
                onChange={(event) => update('outcome', event.target.value)}
                rows={3}
                value={fields.outcome}
              />
            </label>
            {saveError ? (
              <p className="form-error wide-field" role="alert">
                {saveError}
              </p>
            ) : null}
            <div className="event-form-actions wide-field">
              <button
                className="primary-button inline"
                disabled={isSaving}
                type="submit"
              >
                {isSaving ? t('followUps.saving') : t('followUps.save')}
              </button>
            </div>
          </form>
        </section>
      ) : null}
    </main>
  )
}
