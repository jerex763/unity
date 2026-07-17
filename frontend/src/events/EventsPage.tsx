import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { apiRequest } from '../api/client'
import { useAuth } from '../auth/useAuth'
import type { ChurchEvent, EventGroupChoice } from './types'

type EventForm = {
  id: number | null
  title: string
  description: string
  starts_at: string
  ends_at: string
  location: string
  capacity: string
  signup_opens: boolean
  signup_closes_at: string
  group: string
}

const emptyForm: EventForm = {
  id: null,
  title: '',
  description: '',
  starts_at: '',
  ends_at: '',
  location: '',
  capacity: '',
  signup_opens: true,
  signup_closes_at: '',
  group: '',
}

function localDateTime(value: string | null) {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function formFromEvent(event: ChurchEvent, duplicate = false): EventForm {
  return {
    id: duplicate ? null : event.id,
    title: duplicate ? `${event.title} copy` : event.title,
    description: event.description,
    starts_at: localDateTime(event.starts_at),
    ends_at: localDateTime(event.ends_at),
    location: event.location,
    capacity: event.capacity?.toString() ?? '',
    signup_opens: event.signup_opens,
    signup_closes_at: localDateTime(event.signup_closes_at),
    group: event.group?.toString() ?? '',
  }
}

function dateLabel(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

export function EventsPage() {
  const { t } = useTranslation()
  const { session } = useAuth()
  const [events, setEvents] = useState<ChurchEvent[]>([])
  const [groups, setGroups] = useState<EventGroupChoice[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [form, setForm] = useState<EventForm | null>(null)
  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const canEdit = session?.membership.role !== 'member'

  useEffect(() => {
    let active = true
    void Promise.all([
      apiRequest<ChurchEvent[]>('/events/'),
      apiRequest<EventGroupChoice[]>('/events/groups/'),
    ])
      .then(([eventRows, groupRows]) => {
        if (!active) return
        setEvents(eventRows)
        setGroups(groupRows)
      })
      .catch(() => {
        if (active) setLoadError(t('events.loadError'))
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [t])

  function update<Key extends keyof EventForm>(
    key: Key,
    value: EventForm[Key],
  ) {
    setForm((current) => (current ? { ...current, [key]: value } : current))
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!form) return
    setSaveError('')
    setIsSaving(true)
    try {
      const saved = await apiRequest<ChurchEvent>(
        form.id ? `/events/${form.id}/` : '/events/',
        {
          method: form.id ? 'PATCH' : 'POST',
          body: JSON.stringify({
            title: form.title,
            description: form.description,
            starts_at: new Date(form.starts_at).toISOString(),
            ends_at: new Date(form.ends_at).toISOString(),
            location: form.location,
            capacity: form.capacity ? Number(form.capacity) : null,
            signup_opens: form.signup_opens,
            signup_closes_at: form.signup_closes_at
              ? new Date(form.signup_closes_at).toISOString()
              : null,
            group: form.group ? Number(form.group) : null,
          }),
        },
      )
      setEvents((current) =>
        [...current.filter((item) => item.id !== saved.id), saved].sort(
          (first, second) =>
            new Date(first.starts_at).getTime() -
            new Date(second.starts_at).getTime(),
        ),
      )
      setForm(null)
    } catch {
      setSaveError(t('events.saveError'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <main className="events-page">
      <section className="page-heading events-heading">
        <div>
          <p className="eyebrow">{t('events.eyebrow')}</p>
          <h1>{t('events.title')}</h1>
          <p>{t('events.intro')}</p>
        </div>
        {canEdit ? (
          <button
            className="primary-button inline"
            onClick={() => setForm({ ...emptyForm })}
            type="button"
          >
            {t('events.create')}
          </button>
        ) : null}
      </section>

      {form ? (
        <section className="event-editor" aria-labelledby="event-editor-title">
          <div className="profile-panel-heading">
            <div>
              <p className="eyebrow">
                {form.id ? t('events.editEyebrow') : t('events.createEyebrow')}
              </p>
              <h2 id="event-editor-title">
                {form.id ? t('events.editTitle') : t('events.createTitle')}
              </h2>
            </div>
            <button
              className="text-button"
              onClick={() => setForm(null)}
              type="button"
            >
              {t('events.cancel')}
            </button>
          </div>
          <form className="event-form" onSubmit={save}>
            <label className="wide-field">
              <span>{t('events.fields.title')}</span>
              <input
                onChange={(event) => update('title', event.target.value)}
                required
                value={form.title}
              />
            </label>
            <label>
              <span>{t('events.fields.startsAt')}</span>
              <input
                onChange={(event) => update('starts_at', event.target.value)}
                required
                type="datetime-local"
                value={form.starts_at}
              />
            </label>
            <label>
              <span>{t('events.fields.endsAt')}</span>
              <input
                onChange={(event) => update('ends_at', event.target.value)}
                required
                type="datetime-local"
                value={form.ends_at}
              />
            </label>
            <label>
              <span>{t('events.fields.group')}</span>
              <select
                onChange={(event) => update('group', event.target.value)}
                value={form.group}
              >
                <option value="">{t('events.churchWide')}</option>
                {groups.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{t('events.fields.location')}</span>
              <input
                onChange={(event) => update('location', event.target.value)}
                value={form.location}
              />
            </label>
            <label>
              <span>{t('events.fields.capacity')}</span>
              <input
                min="1"
                onChange={(event) => update('capacity', event.target.value)}
                placeholder={t('events.unlimited')}
                type="number"
                value={form.capacity}
              />
            </label>
            <label>
              <span>{t('events.fields.signupClosesAt')}</span>
              <input
                onChange={(event) =>
                  update('signup_closes_at', event.target.value)
                }
                type="datetime-local"
                value={form.signup_closes_at}
              />
            </label>
            <label className="event-checkbox wide-field">
              <input
                checked={form.signup_opens}
                onChange={(event) =>
                  update('signup_opens', event.target.checked)
                }
                type="checkbox"
              />
              <span>{t('events.fields.signupOpen')}</span>
            </label>
            <label className="wide-field">
              <span>{t('events.fields.description')}</span>
              <textarea
                onChange={(event) => update('description', event.target.value)}
                rows={3}
                value={form.description}
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
                {isSaving ? t('events.saving') : t('events.save')}
              </button>
            </div>
          </form>
        </section>
      ) : null}

      {isLoading ? (
        <p className="events-loading">{t('events.loading')}</p>
      ) : null}
      {loadError ? (
        <p className="form-error" role="alert">
          {loadError}
        </p>
      ) : null}
      {!isLoading && !loadError && !events.length ? (
        <section className="empty-state">
          <p className="eyebrow">{t('events.emptyEyebrow')}</p>
          <h2>{t('events.emptyTitle')}</h2>
          <p>{t('events.emptyBody')}</p>
        </section>
      ) : null}

      <section className="event-list" aria-label={t('events.listLabel')}>
        {events.map((event) => (
          <article className="event-card" key={event.id}>
            <time className="event-date" dateTime={event.starts_at}>
              <strong>
                {new Intl.DateTimeFormat(undefined, { day: 'numeric' }).format(
                  new Date(event.starts_at),
                )}
              </strong>
              {new Intl.DateTimeFormat(undefined, { month: 'short' }).format(
                new Date(event.starts_at),
              )}
            </time>
            <div className="event-card-body">
              <div className="event-card-title">
                <div>
                  <span className="event-scope">
                    {event.group_name ?? t('events.churchWide')}
                  </span>
                  <h2>{event.title}</h2>
                </div>
                <span
                  className={`status-chip ${
                    event.registration_open
                      ? 'event-registration-open'
                      : 'event-registration-closed'
                  }`}
                >
                  {event.registration_open
                    ? t('events.open')
                    : t('events.closed')}
                </span>
              </div>
              <p>
                {dateLabel(event.starts_at)}
                {event.location ? ` · ${event.location}` : ''}
              </p>
              <p>
                {t('events.registrationCount', {
                  count: event.registered_count,
                  capacity: event.capacity ?? t('events.unlimited'),
                })}
                {event.waitlisted_count
                  ? ` · ${t('events.waitlisted', {
                      count: event.waitlisted_count,
                    })}`
                  : ''}
              </p>
              {canEdit ? (
                <div className="event-actions">
                  <button
                    className="secondary-button"
                    onClick={() => setForm(formFromEvent(event))}
                    type="button"
                  >
                    {t('events.edit')}
                  </button>
                  <button
                    className="text-button"
                    onClick={() => setForm(formFromEvent(event, true))}
                    type="button"
                  >
                    {t('events.duplicate')}
                  </button>
                </div>
              ) : null}
            </div>
          </article>
        ))}
      </section>
    </main>
  )
}
