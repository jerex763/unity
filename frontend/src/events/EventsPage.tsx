import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { ApiError, apiRequest } from '../api/client'
import { useAuth } from '../auth/useAuth'
import type { DirectoryPerson } from '../people/types'
import type { ChurchEvent, EventGroupChoice, EventRegistration } from './types'

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

type EventFormErrors = Partial<Record<keyof EventForm, string>>

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

function RequiredMarker() {
  const { t } = useTranslation()
  return <strong className="required-marker">{t('forms.required')}</strong>
}

function apiFieldErrors(error: ApiError): EventFormErrors {
  const errors: EventFormErrors = {}
  const fields: Array<keyof EventForm> = [
    'title',
    'starts_at',
    'ends_at',
    'location',
    'capacity',
    'signup_closes_at',
    'group',
  ]
  for (const field of fields) {
    const value = error.payload[field]
    if (typeof value === 'string') errors[field] = value
    if (Array.isArray(value) && typeof value[0] === 'string') {
      errors[field] = value[0]
    }
  }
  return errors
}

export function EventsPage() {
  const { t } = useTranslation()
  const { session } = useAuth()
  const [events, setEvents] = useState<ChurchEvent[]>([])
  const [groups, setGroups] = useState<EventGroupChoice[]>([])
  const [people, setPeople] = useState<DirectoryPerson[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [form, setForm] = useState<EventForm | null>(null)
  const [fieldErrors, setFieldErrors] = useState<EventFormErrors>({})
  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [activeRoster, setActiveRoster] = useState<number | null>(null)
  const [rosters, setRosters] = useState<Record<number, EventRegistration[]>>(
    {},
  )
  const [registrationPerson, setRegistrationPerson] = useState('')
  const [needsTransport, setNeedsTransport] = useState(false)
  const [registrationNote, setRegistrationNote] = useState('')
  const [registrationError, setRegistrationError] = useState('')
  const [registrationNotice, setRegistrationNotice] = useState('')
  const [rosterSearch, setRosterSearch] = useState('')
  const [isSavingRegistration, setIsSavingRegistration] = useState(false)
  const [walkInEvent, setWalkInEvent] = useState<number | null>(null)
  const [walkInName, setWalkInName] = useState('')
  const [walkInPreferredName, setWalkInPreferredName] = useState('')
  const [walkInEmail, setWalkInEmail] = useState('')
  const [walkInPhone, setWalkInPhone] = useState('')
  const canEdit = session?.membership.role !== 'member'

  useEffect(() => {
    let active = true
    void Promise.all([
      apiRequest<ChurchEvent[]>('/events/'),
      apiRequest<EventGroupChoice[]>('/events/groups/'),
      apiRequest<DirectoryPerson[]>('/people/'),
    ])
      .then(([eventRows, groupRows, personRows]) => {
        if (!active) return
        setEvents(eventRows)
        setGroups(groupRows)
        setPeople(personRows)
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
    setFieldErrors((current) => {
      if (!current[key]) return current
      const next = { ...current }
      delete next[key]
      return next
    })
  }

  function openForm(nextForm: EventForm) {
    setSaveError('')
    setFieldErrors({})
    setForm(nextForm)
  }

  function closeForm() {
    setSaveError('')
    setFieldErrors({})
    setForm(null)
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!form) return
    setSaveError('')
    const errors: EventFormErrors = {}
    const startsAt = form.starts_at ? new Date(form.starts_at) : null
    const endsAt = form.ends_at ? new Date(form.ends_at) : null
    const signupClosesAt = form.signup_closes_at
      ? new Date(form.signup_closes_at)
      : null
    if (!form.title.trim()) errors.title = t('events.validation.titleRequired')
    if (!startsAt || Number.isNaN(startsAt.getTime())) {
      errors.starts_at = t('events.validation.startRequired')
    } else if (!form.id && startsAt.getTime() < Date.now()) {
      errors.starts_at = t('events.validation.startInPast')
    }
    if (!endsAt || Number.isNaN(endsAt.getTime())) {
      errors.ends_at = t('events.validation.endRequired')
    } else if (startsAt && endsAt.getTime() <= startsAt.getTime()) {
      errors.ends_at = t('events.validation.endBeforeStart')
    }
    if (
      signupClosesAt &&
      startsAt &&
      signupClosesAt.getTime() > startsAt.getTime()
    ) {
      errors.signup_closes_at = t('events.validation.signupAfterStart')
    }
    if (Object.keys(errors).length) {
      setFieldErrors(errors)
      setSaveError(t('events.validation.reviewFields'))
      return
    }
    setFieldErrors({})
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
      closeForm()
    } catch (error) {
      if (error instanceof ApiError) {
        const serverErrors = apiFieldErrors(error)
        if (Object.keys(serverErrors).length) {
          setFieldErrors(serverErrors)
          setSaveError(t('events.validation.reviewFields'))
        } else {
          setSaveError(error.payload.detail ?? t('events.saveError'))
        }
      } else {
        setSaveError(t('events.saveError'))
      }
    } finally {
      setIsSaving(false)
    }
  }

  async function openRegistrations(event: ChurchEvent) {
    if (activeRoster === event.id) {
      setActiveRoster(null)
      return
    }
    setRegistrationError('')
    setActiveRoster(event.id)
    try {
      const rows = await apiRequest<EventRegistration[]>(
        `/events/${event.id}/registrations/`,
      )
      setRosters((current) => ({ ...current, [event.id]: rows }))
    } catch {
      setRegistrationError(t('events.registrations.loadError'))
    }
  }

  async function addRegistration(
    event: FormEvent<HTMLFormElement>,
    churchEvent: ChurchEvent,
  ) {
    event.preventDefault()
    setRegistrationError('')
    setIsSavingRegistration(true)
    try {
      const registration = await apiRequest<EventRegistration>(
        `/events/${churchEvent.id}/registrations/`,
        {
          method: 'POST',
          body: JSON.stringify({
            ...(canEdit && registrationPerson
              ? { person: Number(registrationPerson) }
              : {}),
            needs_transport: needsTransport,
            note: registrationNote,
          }),
        },
      )
      setRosters((current) => ({
        ...current,
        [churchEvent.id]: [
          ...(current[churchEvent.id] ?? []).filter(
            (item) => item.id !== registration.id,
          ),
          registration,
        ],
      }))
      if (
        !canEdit ||
        registration.person.id === session?.membership.person_id
      ) {
        setEvents((current) =>
          current.map((item) =>
            item.id === churchEvent.id
              ? { ...item, my_registration: registration }
              : item,
          ),
        )
      }
      setEvents(await apiRequest<ChurchEvent[]>('/events/'))
      setRegistrationPerson('')
      setNeedsTransport(false)
      setRegistrationNote('')
    } catch {
      setRegistrationError(t('events.registrations.saveError'))
    } finally {
      setIsSavingRegistration(false)
    }
  }

  async function cancelRegistration(
    churchEvent: ChurchEvent,
    registration: EventRegistration,
  ) {
    setRegistrationError('')
    try {
      const cancelled = await apiRequest<EventRegistration>(
        `/events/${churchEvent.id}/registrations/${registration.id}/cancel/`,
        { method: 'POST' },
      )
      setRosters((current) => ({
        ...current,
        [churchEvent.id]: (current[churchEvent.id] ?? []).map((item) =>
          item.id === cancelled.id ? cancelled : item,
        ),
      }))
      if (churchEvent.my_registration?.id === cancelled.id) {
        setEvents((current) =>
          current.map((item) =>
            item.id === churchEvent.id
              ? { ...item, my_registration: cancelled }
              : item,
          ),
        )
      }
      setEvents(await apiRequest<ChurchEvent[]>('/events/'))
    } catch {
      setRegistrationError(t('events.registrations.cancelError'))
    }
  }

  async function setCheckIn(
    churchEvent: ChurchEvent,
    registration: EventRegistration,
    checkedIn: boolean,
  ) {
    setRegistrationError('')
    setRegistrationNotice('')
    try {
      const updated = await apiRequest<EventRegistration>(
        `/events/${churchEvent.id}/registrations/${registration.id}/check-in/`,
        {
          method: 'POST',
          body: JSON.stringify({ checked_in: checkedIn }),
        },
      )
      setRosters((current) => ({
        ...current,
        [churchEvent.id]: (current[churchEvent.id] ?? []).map((item) =>
          item.id === updated.id ? updated : item,
        ),
      }))
      setRegistrationNotice(
        checkedIn
          ? t('events.checkIn.success', {
              name: registration.person.full_name,
            })
          : t('events.checkIn.undoSuccess', {
              name: registration.person.full_name,
            }),
      )
    } catch {
      setRegistrationError(t('events.checkIn.error'))
    }
  }

  async function addWalkIn(
    formEvent: FormEvent<HTMLFormElement>,
    churchEvent: ChurchEvent,
  ) {
    formEvent.preventDefault()
    setRegistrationError('')
    setIsSavingRegistration(true)
    try {
      const registration = await apiRequest<EventRegistration>(
        `/events/${churchEvent.id}/walk-ins/`,
        {
          method: 'POST',
          body: JSON.stringify({
            full_name: walkInName,
            preferred_name: walkInPreferredName,
            email: walkInEmail,
            phone: walkInPhone,
            needs_transport: needsTransport,
            note: registrationNote,
          }),
        },
      )
      setRosters((current) => ({
        ...current,
        [churchEvent.id]: [
          ...(current[churchEvent.id] ?? []).filter(
            (item) => item.id !== registration.id,
          ),
          registration,
        ],
      }))
      const [eventRows, personRows] = await Promise.all([
        apiRequest<ChurchEvent[]>('/events/'),
        apiRequest<DirectoryPerson[]>('/people/'),
      ])
      setEvents(eventRows)
      setPeople(personRows)
      setWalkInEvent(null)
      setWalkInName('')
      setWalkInPreferredName('')
      setWalkInEmail('')
      setWalkInPhone('')
      setNeedsTransport(false)
      setRegistrationNote('')
    } catch {
      setRegistrationError(t('events.walkIn.saveError'))
    } finally {
      setIsSavingRegistration(false)
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
            onClick={() => openForm({ ...emptyForm })}
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
              onClick={closeForm}
              type="button"
            >
              {t('events.cancel')}
            </button>
          </div>
          <form className="event-form" noValidate onSubmit={save}>
            <p className="form-required-hint wide-field">
              {t('forms.requiredHint')}
            </p>
            <label className="wide-field">
              <span>
                {t('events.fields.title')} <RequiredMarker />
              </span>
              <input
                aria-describedby={
                  fieldErrors.title ? 'event-title-error' : undefined
                }
                aria-invalid={Boolean(fieldErrors.title)}
                onChange={(event) => update('title', event.target.value)}
                required
                value={form.title}
              />
              {fieldErrors.title ? (
                <small className="field-error" id="event-title-error">
                  {fieldErrors.title}
                </small>
              ) : null}
            </label>
            <label>
              <span>
                {t('events.fields.startsAt')} <RequiredMarker />
              </span>
              <input
                aria-describedby={
                  fieldErrors.starts_at
                    ? 'event-start-help event-start-error'
                    : 'event-start-help'
                }
                aria-invalid={Boolean(fieldErrors.starts_at)}
                min={
                  form.id ? undefined : localDateTime(new Date().toISOString())
                }
                onChange={(event) => update('starts_at', event.target.value)}
                required
                type="datetime-local"
                value={form.starts_at}
              />
              <small className="field-help" id="event-start-help">
                {t('events.dateSelectionHelp')}
              </small>
              {fieldErrors.starts_at ? (
                <small className="field-error" id="event-start-error">
                  {fieldErrors.starts_at}
                </small>
              ) : null}
            </label>
            <label>
              <span>
                {t('events.fields.endsAt')} <RequiredMarker />
              </span>
              <input
                aria-describedby={
                  fieldErrors.ends_at
                    ? 'event-end-help event-end-error'
                    : 'event-end-help'
                }
                aria-invalid={Boolean(fieldErrors.ends_at)}
                min={form.starts_at || undefined}
                onChange={(event) => update('ends_at', event.target.value)}
                required
                type="datetime-local"
                value={form.ends_at}
              />
              <small className="field-help" id="event-end-help">
                {t('events.dateSelectionHelp')}
              </small>
              {fieldErrors.ends_at ? (
                <small className="field-error" id="event-end-error">
                  {fieldErrors.ends_at}
                </small>
              ) : null}
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
                aria-describedby={
                  fieldErrors.capacity ? 'event-capacity-error' : undefined
                }
                aria-invalid={Boolean(fieldErrors.capacity)}
                min="1"
                onChange={(event) => update('capacity', event.target.value)}
                placeholder={t('events.unlimited')}
                type="number"
                value={form.capacity}
              />
              {fieldErrors.capacity ? (
                <small className="field-error" id="event-capacity-error">
                  {fieldErrors.capacity}
                </small>
              ) : null}
            </label>
            <label>
              <span>{t('events.fields.signupClosesAt')}</span>
              <input
                aria-describedby={
                  fieldErrors.signup_closes_at
                    ? 'event-signup-closes-error'
                    : undefined
                }
                aria-invalid={Boolean(fieldErrors.signup_closes_at)}
                max={form.starts_at || undefined}
                onChange={(event) =>
                  update('signup_closes_at', event.target.value)
                }
                type="datetime-local"
                value={form.signup_closes_at}
              />
              {fieldErrors.signup_closes_at ? (
                <small className="field-error" id="event-signup-closes-error">
                  {fieldErrors.signup_closes_at}
                </small>
              ) : null}
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
                    ? event.places_available
                      ? t('events.open')
                      : t('events.waitlistOpen')
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
                    onClick={() => openForm(formFromEvent(event))}
                    type="button"
                  >
                    {t('events.edit')}
                  </button>
                  <button
                    className="text-button"
                    onClick={() => openForm(formFromEvent(event, true))}
                    type="button"
                  >
                    {t('events.duplicate')}
                  </button>
                  <button
                    className="text-button"
                    onClick={() => void openRegistrations(event)}
                    type="button"
                  >
                    {t('events.registrations.manage')}
                  </button>
                </div>
              ) : (
                <div className="event-actions">
                  <button
                    className="secondary-button"
                    disabled={!event.registration_open}
                    onClick={() => void openRegistrations(event)}
                    type="button"
                  >
                    {event.my_registration &&
                    event.my_registration.status !== 'cancelled'
                      ? t('events.registrations.viewMine')
                      : event.places_available
                        ? t('events.registrations.signUp')
                        : t('events.registrations.joinWaitlist')}
                  </button>
                </div>
              )}

              {activeRoster === event.id ? (
                <section
                  className="registration-panel"
                  aria-label={t('events.registrations.title')}
                >
                  <h3>{t('events.registrations.title')}</h3>
                  {canEdit ? (
                    <label className="roster-search">
                      <span>{t('events.checkIn.search')}</span>
                      <input
                        onChange={(changeEvent) =>
                          setRosterSearch(changeEvent.target.value)
                        }
                        placeholder={t('events.checkIn.searchPlaceholder')}
                        type="search"
                        value={rosterSearch}
                      />
                    </label>
                  ) : null}
                  {(rosters[event.id] ?? []).length ? (
                    <div className="registration-list">
                      {(rosters[event.id] ?? [])
                        .filter((registration) =>
                          registration.person.full_name
                            .toLocaleLowerCase()
                            .includes(rosterSearch.trim().toLocaleLowerCase()),
                        )
                        .map((registration) => (
                          <article key={registration.id}>
                            <div>
                              <strong>{registration.person.full_name}</strong>
                              <span>
                                {t(
                                  `events.registrations.statuses.${registration.status}`,
                                )}
                                {registration.needs_transport
                                  ? ` · ${t('events.registrations.transport')}`
                                  : ''}
                              </span>
                              {registration.note ? (
                                <small>{registration.note}</small>
                              ) : null}
                            </div>
                            <div className="registration-actions">
                              {canEdit &&
                              registration.status !== 'cancelled' ? (
                                <button
                                  className="secondary-button"
                                  onClick={() =>
                                    void setCheckIn(
                                      event,
                                      registration,
                                      !registration.checked_in_at,
                                    )
                                  }
                                  type="button"
                                >
                                  {registration.checked_in_at
                                    ? t('events.checkIn.undo')
                                    : t('events.checkIn.mark')}
                                </button>
                              ) : null}
                              {registration.status !== 'cancelled' ? (
                                <button
                                  className="text-button"
                                  onClick={() =>
                                    void cancelRegistration(event, registration)
                                  }
                                  type="button"
                                >
                                  {t('events.registrations.cancel')}
                                </button>
                              ) : null}
                            </div>
                          </article>
                        ))}
                    </div>
                  ) : (
                    <p>{t('events.registrations.empty')}</p>
                  )}
                  {event.registration_open ? (
                    <form
                      className="registration-form"
                      onSubmit={(formEvent) =>
                        void addRegistration(formEvent, event)
                      }
                    >
                      {canEdit ? (
                        <>
                          <p className="form-required-hint">
                            {t('forms.requiredHint')}
                          </p>
                          <label>
                            <span>
                              {t('events.registrations.person')}{' '}
                              <RequiredMarker />
                            </span>
                            <select
                              onChange={(changeEvent) =>
                                setRegistrationPerson(changeEvent.target.value)
                              }
                              required
                              value={registrationPerson}
                            >
                              <option value="">
                                {t('events.registrations.choosePerson')}
                              </option>
                              {people.map((person) => (
                                <option key={person.id} value={person.id}>
                                  {person.full_name}
                                </option>
                              ))}
                            </select>
                          </label>
                        </>
                      ) : null}
                      <label className="event-checkbox">
                        <input
                          checked={needsTransport}
                          onChange={(changeEvent) =>
                            setNeedsTransport(changeEvent.target.checked)
                          }
                          type="checkbox"
                        />
                        <span>{t('events.registrations.needsTransport')}</span>
                      </label>
                      <label>
                        <span>{t('events.registrations.note')}</span>
                        <input
                          maxLength={200}
                          onChange={(changeEvent) =>
                            setRegistrationNote(changeEvent.target.value)
                          }
                          value={registrationNote}
                        />
                      </label>
                      <button
                        className="primary-button inline"
                        disabled={isSavingRegistration}
                        type="submit"
                      >
                        {isSavingRegistration
                          ? t('events.registrations.saving')
                          : event.places_available
                            ? t('events.registrations.confirm')
                            : t('events.registrations.confirmWaitlist')}
                      </button>
                    </form>
                  ) : null}
                  {canEdit && new Date(event.ends_at) > new Date() ? (
                    <>
                      <button
                        className="secondary-button walk-in-toggle"
                        onClick={() =>
                          setWalkInEvent((current) =>
                            current === event.id ? null : event.id,
                          )
                        }
                        type="button"
                      >
                        {t('events.walkIn.add')}
                      </button>
                      {walkInEvent === event.id ? (
                        <form
                          className="registration-form walk-in-form"
                          onSubmit={(formEvent) =>
                            void addWalkIn(formEvent, event)
                          }
                        >
                          <h4>{t('events.walkIn.title')}</h4>
                          <p className="form-required-hint">
                            {t('forms.requiredHint')}
                          </p>
                          <label>
                            <span>
                              {t('events.walkIn.fullName')} <RequiredMarker />
                            </span>
                            <input
                              onChange={(changeEvent) =>
                                setWalkInName(changeEvent.target.value)
                              }
                              required
                              value={walkInName}
                            />
                          </label>
                          <label>
                            <span>{t('events.walkIn.preferredName')}</span>
                            <input
                              onChange={(changeEvent) =>
                                setWalkInPreferredName(changeEvent.target.value)
                              }
                              value={walkInPreferredName}
                            />
                          </label>
                          <label>
                            <span>{t('events.walkIn.email')}</span>
                            <input
                              onChange={(changeEvent) =>
                                setWalkInEmail(changeEvent.target.value)
                              }
                              type="email"
                              value={walkInEmail}
                            />
                          </label>
                          <label>
                            <span>{t('events.walkIn.phone')}</span>
                            <input
                              onChange={(changeEvent) =>
                                setWalkInPhone(changeEvent.target.value)
                              }
                              type="tel"
                              value={walkInPhone}
                            />
                          </label>
                          <label className="event-checkbox">
                            <input
                              checked={needsTransport}
                              onChange={(changeEvent) =>
                                setNeedsTransport(changeEvent.target.checked)
                              }
                              type="checkbox"
                            />
                            <span>
                              {t('events.registrations.needsTransport')}
                            </span>
                          </label>
                          <label>
                            <span>{t('events.registrations.note')}</span>
                            <input
                              maxLength={200}
                              onChange={(changeEvent) =>
                                setRegistrationNote(changeEvent.target.value)
                              }
                              value={registrationNote}
                            />
                          </label>
                          <button
                            className="primary-button inline"
                            disabled={isSavingRegistration}
                            type="submit"
                          >
                            {isSavingRegistration
                              ? t('events.walkIn.saving')
                              : t('events.walkIn.confirm')}
                          </button>
                        </form>
                      ) : null}
                    </>
                  ) : null}
                  {registrationError ? (
                    <p className="form-error" role="alert">
                      {registrationError}
                    </p>
                  ) : null}
                  {registrationNotice ? (
                    <p className="form-success" role="status">
                      {registrationNotice}
                    </p>
                  ) : null}
                </section>
              ) : null}
            </div>
          </article>
        ))}
      </section>
    </main>
  )
}
