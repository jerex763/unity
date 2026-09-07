import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { ApiError, apiRequest } from '../api/client'
import { useModalDialog } from '../accessibility/useModalDialog'
import { useAuth } from '../auth/useAuth'
import type { DirectoryPerson } from '../people/types'
import {
  validateEventForm,
  type EventFormValidationError,
  type EventFormValidationField,
} from './eventFormValidation'
import type { ChurchEvent, EventGroupChoice, EventRegistration } from './types'
import '../styles/task-navigation.css'
import { usePublicLinks } from './usePublicLinks'
import { PublicLinkResult } from './PublicLinkResult'

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
type EventFormMode = 'create' | 'edit' | 'duplicate'

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

function usePhoneLayout() {
  const [isPhone, setIsPhone] = useState(() =>
    typeof window.matchMedia === 'function'
      ? window.matchMedia('(max-width: 47.999rem)').matches
      : false,
  )

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const query = window.matchMedia('(max-width: 47.999rem)')
    const updateLayout = () => setIsPhone(query.matches)
    if (typeof query.addEventListener !== 'function') return
    query.addEventListener('change', updateLayout)
    return () => query.removeEventListener('change', updateLayout)
  }, [])

  return isPhone
}

export function EventsPage() {
  const { session } = useAuth()
  return (
    <EventsPageContent
      key={`${session?.user.id}:${session?.membership.church_id}:${session?.membership.role}`}
    />
  )
}

function EventsPageContent() {
  const { t } = useTranslation()
  const { session } = useAuth()
  const isPhone = usePhoneLayout()
  const [events, setEvents] = useState<ChurchEvent[]>([])
  const [groups, setGroups] = useState<EventGroupChoice[]>([])
  const [people, setPeople] = useState<DirectoryPerson[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [form, setForm] = useState<EventForm | null>(null)
  const [formMode, setFormMode] = useState<EventFormMode | null>(null)
  const [formOpenRequest, setFormOpenRequest] = useState(0)
  const [fieldErrors, setFieldErrors] = useState<EventFormErrors>({})
  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [activeRoster, setActiveRoster] = useState<number | null>(null)
  const [isRosterLoading, setIsRosterLoading] = useState(false)
  const [rosterLoadError, setRosterLoadError] = useState('')
  const [rosters, setRosters] = useState<Record<number, EventRegistration[]>>(
    {},
  )
  const [registrationPerson, setRegistrationPerson] = useState('')
  const [registrationNote, setRegistrationNote] = useState('')
  const [registrationError, setRegistrationError] = useState('')
  const [isSavingRegistration, setIsSavingRegistration] = useState(false)
  const publicLinks = usePublicLinks((id, enabled) =>
    setEvents((current) =>
      current.map((item) =>
        item.id === id
          ? { ...item, public_registration_enabled: enabled }
          : item,
      ),
    ),
  )
  const titleInputRef = useRef<HTMLInputElement>(null)
  const rosterTitleRef = useRef<HTMLHeadingElement>(null)
  const rosterRequestGeneration = useRef(0)
  const canEdit = session?.membership.role !== 'member'
  const canCheckIn = ['admin', 'pastor', 'leader'].includes(
    session?.membership.role ?? '',
  )
  const editorRef = useModalDialog<HTMLElement>(
    Boolean(formMode),
    closeForm,
    titleInputRef,
  )
  const rosterDialogRef = useModalDialog<HTMLElement>(
    isPhone && activeRoster !== null,
    closeRoster,
    rosterTitleRef,
  )

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

  useEffect(() => {
    if (!formMode || formOpenRequest === 0) return
    const prefersReducedMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    editorRef.current?.scrollIntoView?.({
      behavior: prefersReducedMotion ? 'auto' : 'smooth',
      block: 'start',
    })
  }, [editorRef, formOpenRequest, formMode])

  function openForm(nextForm: EventForm, mode: EventFormMode) {
    if (nextForm.id) publicLinks.hide(nextForm.id)
    setSaveError('')
    setFieldErrors({})
    setFormMode(mode)
    setForm(nextForm)
    setFormOpenRequest((current) => current + 1)
  }

  function closeForm() {
    setSaveError('')
    setFieldErrors({})
    setForm(null)
    setFormMode(null)
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!form) return
    setSaveError('')
    const errors: EventFormErrors = {}
    const validationErrors = validateEventForm(form)
    for (const [field, error] of Object.entries(validationErrors) as Array<
      [EventFormValidationField, EventFormValidationError]
    >) {
      errors[field] = t(`events.validation.${error}`)
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

  function closeRoster() {
    rosterRequestGeneration.current += 1
    setActiveRoster(null)
    setIsRosterLoading(false)
    setRosterLoadError('')
    setRegistrationError('')
  }

  async function loadRegistrations(event: ChurchEvent) {
    const generation = ++rosterRequestGeneration.current
    setRegistrationError('')
    setRosterLoadError('')
    setIsRosterLoading(true)
    setActiveRoster(event.id)
    try {
      const rows = await apiRequest<EventRegistration[]>(
        `/events/${event.id}/registrations/`,
      )
      if (generation !== rosterRequestGeneration.current) return
      setRosters((current) => ({ ...current, [event.id]: rows }))
    } catch {
      if (generation !== rosterRequestGeneration.current) return
      setRosterLoadError(t('events.registrations.loadError'))
    } finally {
      if (generation === rosterRequestGeneration.current) {
        setIsRosterLoading(false)
      }
    }
  }

  async function openRegistrations(event: ChurchEvent) {
    if (activeRoster === event.id) {
      closeRoster()
      return
    }
    await loadRegistrations(event)
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
            onClick={() => openForm({ ...emptyForm }, 'create')}
            type="button"
          >
            {t('events.create')}
          </button>
        ) : null}
      </section>

      {form && formMode ? (
        <div className="dialog-backdrop">
          <section
            aria-labelledby="event-editor-title"
            aria-modal="true"
            className="event-editor"
            ref={editorRef}
            role="dialog"
            tabIndex={-1}
          >
            <div className="profile-panel-heading">
              <div>
                <p className="eyebrow">{t(`events.${formMode}Eyebrow`)}</p>
                <h2 id="event-editor-title">{t(`events.${formMode}Title`)}</h2>
                {formMode === 'duplicate' ? (
                  <p className="event-form-mode-help">
                    {t('events.duplicateHelp')}
                  </p>
                ) : null}
              </div>
              <button
                aria-label={t('events.cancel')}
                className="dialog-close"
                onClick={closeForm}
                type="button"
              >
                <span aria-hidden="true">×</span>
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
                  ref={titleInputRef}
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
                    form.id
                      ? undefined
                      : localDateTime(new Date().toISOString())
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
                  onChange={(event) =>
                    update('description', event.target.value)
                  }
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
                  className="secondary-button"
                  disabled={isSaving}
                  onClick={closeForm}
                  type="button"
                >
                  {t('events.cancel')}
                </button>
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
        </div>
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
                    className="primary-button event-action-primary"
                    disabled={publicLinks.pending.has(event.id)}
                    onClick={() => openForm(formFromEvent(event), 'edit')}
                    type="button"
                  >
                    {t('events.edit')}
                  </button>
                  {canCheckIn ? (
                    <Link
                      className="secondary-button check-in-link"
                      to={`/events/${event.id}/check-in`}
                    >
                      {t('events.checkIn.open')}
                    </Link>
                  ) : null}
                  <button
                    className="secondary-button"
                    onClick={() =>
                      openForm(formFromEvent(event, true), 'duplicate')
                    }
                    type="button"
                  >
                    {t('events.duplicate')}
                  </button>
                  <button
                    aria-controls={`event-${event.id}-registrations`}
                    aria-expanded={activeRoster === event.id}
                    aria-label={
                      activeRoster === event.id
                        ? t('events.registrations.hideCount', {
                            count:
                              event.registered_count + event.waitlisted_count,
                          })
                        : t('events.registrations.showCount', {
                            count:
                              event.registered_count + event.waitlisted_count,
                          })
                    }
                    className="secondary-button registration-toggle"
                    onClick={() => void openRegistrations(event)}
                    type="button"
                  >
                    <span>
                      {t('events.registrations.manageCount', {
                        count: event.registered_count + event.waitlisted_count,
                      })}
                    </span>
                    <span
                      className="registration-toggle-icon"
                      aria-hidden="true"
                    >
                      ▾
                    </span>
                  </button>
                  <button
                    className="secondary-button"
                    disabled={
                      !event.registration_open ||
                      publicLinks.pending.has(event.id)
                    }
                    onClick={() => void publicLinks.act(event, 'create')}
                    type="button"
                  >
                    {event.public_registration_enabled
                      ? t('events.publicLink.replace')
                      : t('events.publicLink.create')}
                  </button>
                </div>
              ) : (
                <div className="event-actions">
                  <button
                    aria-controls={`event-${event.id}-registrations`}
                    aria-expanded={activeRoster === event.id}
                    className="secondary-button registration-toggle"
                    disabled={!event.registration_open}
                    onClick={() => void openRegistrations(event)}
                    type="button"
                  >
                    <span>
                      {activeRoster === event.id
                        ? t('events.registrations.hideDetails')
                        : event.my_registration &&
                            event.my_registration.status !== 'cancelled'
                          ? t('events.registrations.viewMine')
                          : event.places_available
                            ? t('events.registrations.signUp')
                            : t('events.registrations.joinWaitlist')}
                    </span>
                    <span
                      className="registration-toggle-icon"
                      aria-hidden="true"
                    >
                      ▾
                    </span>
                  </button>
                </div>
              )}

              {canCheckIn && event.public_registration_enabled ? (
                <section
                  className="public-link-panel"
                  aria-label={t('events.publicLink.title')}
                  aria-busy={publicLinks.pending.has(event.id)}
                >
                  <p>
                    {t(
                      event.registration_open
                        ? 'events.publicLink.privateHint'
                        : 'events.publicLink.closed',
                    )}
                  </p>
                  <div>
                    <button
                      className="secondary-button"
                      disabled={
                        !event.registration_open ||
                        publicLinks.pending.has(event.id)
                      }
                      onClick={() =>
                        publicLinks.urls[event.id]
                          ? publicLinks.hide(event.id)
                          : void publicLinks.act(event, 'show')
                      }
                      type="button"
                    >
                      {t(
                        publicLinks.urls[event.id]
                          ? 'events.publicLink.hide'
                          : 'events.publicLink.show',
                      )}
                    </button>
                    <button
                      className="secondary-button"
                      disabled={
                        !event.registration_open ||
                        publicLinks.pending.has(event.id)
                      }
                      onClick={() => void publicLinks.act(event, 'copy')}
                      type="button"
                    >
                      {t('events.publicLink.copy')}
                    </button>
                    <button
                      className="text-button"
                      disabled={publicLinks.pending.has(event.id)}
                      onClick={() => void publicLinks.act(event, 'revoke')}
                      type="button"
                    >
                      {t('events.publicLink.revoke')}
                    </button>
                  </div>
                </section>
              ) : null}
              {publicLinks.pending.has(event.id) ? (
                <p role="status">{t('events.publicLink.pending')}</p>
              ) : null}
              {!publicLinks.pending.has(event.id) ? (
                <PublicLinkResult
                  url={
                    event.registration_open
                      ? publicLinks.urls[event.id]
                      : undefined
                  }
                  error={publicLinks.feedback[event.id]?.error}
                  notice={publicLinks.feedback[event.id]?.notice}
                  retry={
                    publicLinks.feedback[event.id]?.retry
                      ? () =>
                          void publicLinks.act(
                            event,
                            publicLinks.feedback[event.id].retry!,
                          )
                      : undefined
                  }
                />
              ) : null}

              {activeRoster === event.id ? (
                <div
                  className={
                    isPhone
                      ? 'dialog-backdrop roster-dialog-backdrop'
                      : undefined
                  }
                >
                  <section
                    aria-busy={isRosterLoading}
                    aria-label={
                      isPhone ? undefined : t('events.registrations.title')
                    }
                    aria-labelledby={
                      isPhone
                        ? `event-${event.id}-registrations-title`
                        : undefined
                    }
                    aria-modal={isPhone || undefined}
                    className={`registration-panel${isPhone ? ' event-editor roster-dialog' : ''}`}
                    id={`event-${event.id}-registrations`}
                    ref={isPhone ? rosterDialogRef : undefined}
                    role={isPhone ? 'dialog' : undefined}
                    tabIndex={isPhone ? -1 : undefined}
                  >
                    <button
                      className="text-button roster-back-button"
                      onClick={closeRoster}
                      type="button"
                    >
                      ←{' '}
                      {t('events.registrations.backToEvents', {
                        defaultValue: 'Back to events',
                      })}
                    </button>
                    <h3
                      id={`event-${event.id}-registrations-title`}
                      ref={isPhone ? rosterTitleRef : undefined}
                      tabIndex={isPhone ? -1 : undefined}
                    >
                      {t('events.registrations.titleForEvent', {
                        defaultValue: 'Registrations — {{eventTitle}}',
                        eventTitle: event.title,
                      })}
                    </h3>
                    <p className="roster-dialog-context">
                      {dateLabel(event.starts_at)}
                      {event.location ? ` · ${event.location}` : ''}
                    </p>
                    {isRosterLoading ? (
                      <div className="roster-load-state" role="status">
                        <p>
                          {t('events.registrations.loading', {
                            defaultValue: 'Loading registrations…',
                          })}
                        </p>
                      </div>
                    ) : null}
                    {!isRosterLoading && rosterLoadError ? (
                      <div
                        className="roster-load-state roster-load-error"
                        role="alert"
                      >
                        <p>{rosterLoadError}</p>
                        <p>
                          {t('events.registrations.loadErrorContext', {
                            defaultValue:
                              'The event and its registrations are unchanged.',
                          })}
                        </p>
                        <button
                          className="secondary-button"
                          onClick={() => void loadRegistrations(event)}
                          type="button"
                        >
                          {t('events.registrations.retry', {
                            defaultValue: 'Try again',
                          })}
                        </button>
                      </div>
                    ) : null}
                    {!isRosterLoading && !rosterLoadError ? (
                      <>
                        {(rosters[event.id] ?? []).length ? (
                          <div className="registration-list">
                            {(rosters[event.id] ?? []).map((registration) => (
                              <article key={registration.id}>
                                <div>
                                  <strong>
                                    {registration.person.full_name}
                                  </strong>
                                  <span>
                                    {t(
                                      `events.registrations.statuses.${registration.status}`,
                                    )}
                                  </span>
                                  {registration.note ? (
                                    <small>{registration.note}</small>
                                  ) : null}
                                </div>
                                <div className="registration-actions">
                                  {registration.status !== 'cancelled' ? (
                                    <button
                                      className="text-button"
                                      onClick={() =>
                                        void cancelRegistration(
                                          event,
                                          registration,
                                        )
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
                                      setRegistrationPerson(
                                        changeEvent.target.value,
                                      )
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
                        {registrationError ? (
                          <p className="form-error" role="alert">
                            {registrationError}
                          </p>
                        ) : null}
                      </>
                    ) : null}
                  </section>
                </div>
              ) : null}
            </div>
          </article>
        ))}
      </section>
    </main>
  )
}
