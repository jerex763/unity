import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useParams } from 'react-router-dom'

import { ApiError, apiRequest } from '../api/client'
import { useModalDialog } from '../accessibility/useModalDialog'
import { useAuth } from '../auth/useAuth'
import type { CheckInPerson, ChurchEvent, EventRegistration } from './types'

type RosterFilter = 'to_check_in' | 'all' | 'checked_in' | 'walk_ins'
type WalkInMode = 'existing' | 'new'

export function EventCheckInPage() {
  const { eventId = '' } = useParams()
  return <EventCheckInContent eventId={eventId} key={eventId} />
}

function EventCheckInContent({ eventId }: { eventId: string }) {
  const { t } = useTranslation()
  const { session } = useAuth()
  const [event, setEvent] = useState<ChurchEvent | null>(null)
  const [registrations, setRegistrations] = useState<EventRegistration[]>([])
  const [filter, setFilter] = useState<RosterFilter>('to_check_in')
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [pendingRegistrationIds, setPendingRegistrationIds] = useState<
    Set<string>
  >(new Set())
  const [walkInOpen, setWalkInOpen] = useState(false)
  const [walkInEventId, setWalkInEventId] = useState<string | null>(null)
  const [addingWalkInEventId, setAddingWalkInEventId] = useState<string | null>(
    null,
  )
  const [walkInMode, setWalkInMode] = useState<WalkInMode>('existing')
  const [personSearch, setPersonSearch] = useState('')
  const [personResults, setPersonResults] = useState<CheckInPerson[]>([])
  const [selectedPerson, setSelectedPerson] = useState<number | null>(null)
  const [isSearchingPeople, setIsSearchingPeople] = useState(false)
  const [fullName, setFullName] = useState('')
  const [preferredName, setPreferredName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [wechatId, setWechatId] = useState('')
  const [hasWhatsapp, setHasWhatsapp] = useState(false)
  const [preferredContact, setPreferredContact] = useState('')
  const [note, setNote] = useState('')
  const [contactError, setContactError] = useState('')
  const personSearchInputRef = useRef<HTMLInputElement>(null)
  const personSearchGenerationRef = useRef(0)
  const checkInRequestsRef = useRef(new Map<string, symbol>())
  const walkInRequestRef = useRef<symbol | null>(null)
  const walkInRequestEventIdRef = useRef<string | null>(null)
  const walkInGenerationRef = useRef(0)
  const currentEventIdRef = useRef(eventId)
  const isAddingWalkIn = addingWalkInEventId === eventId
  const walkInVisible = walkInOpen && walkInEventId === eventId
  const walkInDialogRef = useModalDialog<HTMLElement>(
    walkInVisible,
    closeWalkIn,
    personSearchInputRef,
  )

  function closeWalkIn() {
    if (walkInRequestRef.current && walkInRequestEventIdRef.current === eventId)
      return
    walkInGenerationRef.current += 1
    personSearchGenerationRef.current += 1
    setIsSearchingPeople(false)
    setWalkInOpen(false)
    setWalkInEventId(null)
  }

  function openWalkIn() {
    if (walkInRequestRef.current && walkInRequestEventIdRef.current === eventId)
      return
    walkInGenerationRef.current += 1
    personSearchGenerationRef.current += 1
    setWalkInMode('existing')
    setPersonSearch('')
    setPersonResults([])
    setSelectedPerson(null)
    setIsSearchingPeople(false)
    setContactError('')
    setWalkInEventId(eventId)
    setWalkInOpen(true)
  }

  useEffect(() => {
    let active = true
    void Promise.all([
      apiRequest<ChurchEvent[]>('/events/'),
      apiRequest<EventRegistration[]>(`/events/${eventId}/registrations/`),
    ])
      .then(([events, rows]) => {
        if (!active) return
        setEvent(events.find((item) => String(item.id) === eventId) ?? null)
        setRegistrations(rows)
      })
      .catch(() => active && setError('We could not load this check-in list.'))
      .finally(() => active && setIsLoading(false))
    return () => {
      active = false
    }
  }, [eventId])

  useEffect(() => {
    const generation = ++personSearchGenerationRef.current
    const query = personSearch.trim()
    if (!walkInVisible || walkInMode !== 'existing' || query.length < 2) {
      return
    }
    let active = true
    const timer = window.setTimeout(() => {
      if (!active || generation !== personSearchGenerationRef.current) return
      setIsSearchingPeople(true)
      void apiRequest<CheckInPerson[]>(
        `/events/${eventId}/check-in/people/?q=${encodeURIComponent(query)}`,
      )
        .then((people) => {
          if (active && generation === personSearchGenerationRef.current) {
            setPersonResults(people)
          }
        })
        .catch(() => {
          if (active && generation === personSearchGenerationRef.current) {
            setPersonResults([])
            setContactError(t('events.walkIn.searchError'))
          }
        })
        .finally(() => {
          if (active && generation === personSearchGenerationRef.current) {
            setIsSearchingPeople(false)
          }
        })
    }, 200)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [eventId, personSearch, t, walkInMode, walkInVisible])

  const visible = useMemo(() => {
    const query = search.trim().toLocaleLowerCase()
    return registrations.filter((registration) => {
      if (registration.status === 'cancelled') return false
      const matchesSearch = registration.person.full_name
        .toLocaleLowerCase()
        .includes(query)
      const matchesFilter =
        filter === 'all'
          ? true
          : filter === 'checked_in'
            ? Boolean(registration.checked_in_at)
            : filter === 'walk_ins'
              ? registration.status === 'walk_in'
              : !registration.checked_in_at
      return matchesSearch && matchesFilter
    })
  }, [filter, registrations, search])

  if (
    session &&
    !['admin', 'pastor', 'leader'].includes(session.membership.role)
  )
    return <Navigate replace to="/events" />

  async function setCheckedIn(
    registration: EventRegistration,
    checkedIn: boolean,
  ) {
    const registrationKey = `${eventId}:${registration.id}`
    if (checkInRequestsRef.current.has(registrationKey)) return
    const request = Symbol()
    const requestEventId = eventId
    checkInRequestsRef.current.set(registrationKey, request)
    setPendingRegistrationIds((current) => {
      const next = new Set(current)
      next.add(registrationKey)
      return next
    })
    setError('')
    setNotice('')
    try {
      const updated = await apiRequest<EventRegistration>(
        `/events/${eventId}/registrations/${registration.id}/check-in/`,
        {
          method: 'POST',
          body: JSON.stringify({ checked_in: checkedIn }),
        },
      )
      if (
        currentEventIdRef.current !== requestEventId ||
        checkInRequestsRef.current.get(registrationKey) !== request
      )
        return
      setRegistrations((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      )
      setNotice(
        checkedIn
          ? `${registration.person.full_name} is checked in.`
          : `${registration.person.full_name}'s check-in was removed.`,
      )
    } catch {
      if (
        currentEventIdRef.current === requestEventId &&
        checkInRequestsRef.current.get(registrationKey) === request
      ) {
        setError('We could not update attendance. Retry.')
      }
    } finally {
      if (checkInRequestsRef.current.get(registrationKey) === request) {
        checkInRequestsRef.current.delete(registrationKey)
        setPendingRegistrationIds((current) => {
          const next = new Set(current)
          next.delete(registrationKey)
          return next
        })
      }
    }
  }

  async function addWalkIn(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault()
    if (walkInRequestRef.current && walkInRequestEventIdRef.current === eventId)
      return
    setError('')
    setContactError('')
    const selectedPersonIsCurrent =
      selectedPerson !== null &&
      personResults.some((person) => person.id === selectedPerson)
    if (walkInMode === 'existing' && !selectedPersonIsCurrent) {
      setContactError(t('events.walkIn.selectError'))
      return
    }
    if (
      walkInMode === 'new' &&
      ![email, phone, wechatId].some((value) => value.trim())
    ) {
      setContactError(
        'Provide at least one contact method: email, phone, or WeChat ID.',
      )
      return
    }
    const request = Symbol()
    const requestEventId = eventId
    const requestGeneration = walkInGenerationRef.current
    const submittedMode = walkInMode
    walkInRequestRef.current = request
    walkInRequestEventIdRef.current = requestEventId
    setAddingWalkInEventId(requestEventId)
    try {
      const registration = await apiRequest<EventRegistration>(
        `/events/${eventId}/walk-ins/`,
        {
          method: 'POST',
          body: JSON.stringify(
            walkInMode === 'existing'
              ? { person: selectedPerson, note }
              : {
                  full_name: fullName,
                  preferred_name: preferredName,
                  email,
                  phone,
                  wechat_id: wechatId,
                  has_whatsapp: hasWhatsapp,
                  preferred_contact: preferredContact,
                  note,
                },
          ),
        },
      )
      if (
        walkInRequestRef.current !== request ||
        currentEventIdRef.current !== requestEventId ||
        walkInGenerationRef.current !== requestGeneration
      )
        return
      setRegistrations((current) => [
        ...current.filter((item) => item.id !== registration.id),
        registration,
      ])
      walkInRequestRef.current = null
      walkInRequestEventIdRef.current = null
      setAddingWalkInEventId(null)
      closeWalkIn()
      setFullName('')
      setPreferredName('')
      setEmail('')
      setPhone('')
      setWechatId('')
      setHasWhatsapp(false)
      setPreferredContact('')
      setNote('')
      setPersonSearch('')
      setPersonResults([])
      setSelectedPerson(null)
      setFilter(registration.status === 'walk_in' ? 'walk_ins' : 'checked_in')
      setNotice(
        submittedMode === 'existing'
          ? `${registration.person.full_name} was checked in.`
          : `${registration.person.full_name} was added and checked in.`,
      )
    } catch (requestError) {
      const payload =
        requestError instanceof ApiError ? requestError.payload : {}
      const contact = payload.contact ?? payload.detail
      if (
        walkInRequestRef.current === request &&
        currentEventIdRef.current === requestEventId &&
        walkInGenerationRef.current === requestGeneration
      ) {
        setContactError(
          typeof contact === 'string'
            ? contact
            : Array.isArray(contact) && typeof contact[0] === 'string'
              ? contact[0]
              : t('events.walkIn.saveError'),
        )
      }
    } finally {
      if (walkInRequestRef.current === request) {
        walkInRequestRef.current = null
        walkInRequestEventIdRef.current = null
        if (
          currentEventIdRef.current === requestEventId &&
          walkInGenerationRef.current === requestGeneration
        ) {
          setAddingWalkInEventId(null)
        }
      }
    }
  }

  return (
    <main className="check-in-page">
      <Link className="text-button back-link" to="/events">
        ← Back to events
      </Link>
      <section className="page-heading check-in-heading">
        <div>
          <p className="eyebrow">Event day</p>
          <h1>{event?.title ?? 'Check-in'}</h1>
          <p>Find each arrival and record attendance.</p>
        </div>
        <button
          className="primary-button inline"
          onClick={openWalkIn}
          type="button"
        >
          Add walk-in
        </button>
      </section>

      <label className="roster-search">
        <span>Find attendee</span>
        <input
          onChange={(changeEvent) => {
            setSearch(changeEvent.target.value)
            if (changeEvent.target.value.trim()) setFilter('all')
          }}
          placeholder="Search the registration list…"
          type="search"
          value={search}
        />
      </label>
      <div
        className="check-in-filters"
        role="group"
        aria-label="Check-in list filter"
      >
        {(
          [
            ['to_check_in', 'To check in'],
            ['all', 'All'],
            ['checked_in', 'Checked in'],
            ['walk_ins', 'Walk-ins'],
          ] as const
        ).map(([value, label]) => (
          <button
            aria-pressed={filter === value}
            className={filter === value ? 'active' : undefined}
            key={value}
            onClick={() => setFilter(value)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      {isLoading ? <p>Loading check-in…</p> : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p className="form-success" role="status">
          {notice}
        </p>
      ) : null}
      {!isLoading ? (
        <section className="check-in-list" aria-label="Attendees">
          {visible.map((registration) => {
            const registrationKey = `${eventId}:${registration.id}`
            const isPending = pendingRegistrationIds.has(registrationKey)
            return (
              <article key={registration.id}>
                <div>
                  <strong>{registration.person.full_name}</strong>
                  <span>
                    {registration.status === 'walk_in'
                      ? 'Walk-in'
                      : registration.status === 'waitlisted'
                        ? 'Waitlisted'
                        : 'Registered'}{' '}
                    ·{' '}
                    {registration.checked_in_at
                      ? 'Checked in'
                      : 'Not checked in'}
                  </span>
                </div>
                <button
                  className={
                    registration.checked_in_at
                      ? 'secondary-button'
                      : 'primary-button'
                  }
                  onClick={() =>
                    void setCheckedIn(registration, !registration.checked_in_at)
                  }
                  disabled={isPending}
                  type="button"
                >
                  {isPending
                    ? registration.checked_in_at
                      ? 'Removing…'
                      : 'Checking in…'
                    : registration.checked_in_at
                      ? 'Undo check-in'
                      : 'Check in'}
                </button>
              </article>
            )
          })}
          {!visible.length ? <p>No attendees match this view.</p> : null}
        </section>
      ) : null}

      {walkInVisible ? (
        <div className="dialog-backdrop">
          <section
            aria-labelledby="walk-in-title"
            aria-modal="true"
            className="event-editor"
            ref={walkInDialogRef}
            role="dialog"
            tabIndex={-1}
          >
            <div className="profile-panel-heading">
              <div>
                <p className="eyebrow">Event day</p>
                <h2 id="walk-in-title">Add walk-in</h2>
              </div>
              <button
                aria-label="Cancel"
                className="dialog-close"
                disabled={isAddingWalkIn}
                onClick={closeWalkIn}
                type="button"
              >
                ×
              </button>
            </div>
            <form
              className="event-form"
              onSubmit={(formEvent) => void addWalkIn(formEvent)}
            >
              <fieldset
                className="walk-in-path wide-field"
                disabled={isAddingWalkIn}
              >
                <legend>{t('events.walkIn.choosePath')}</legend>
                <label>
                  <input
                    checked={walkInMode === 'existing'}
                    name="walk-in-path"
                    onChange={() => {
                      if (
                        walkInRequestRef.current &&
                        walkInRequestEventIdRef.current === eventId
                      )
                        return
                      personSearchGenerationRef.current += 1
                      setWalkInMode('existing')
                      setPersonResults([])
                      setIsSearchingPeople(false)
                      setSelectedPerson(null)
                      setContactError('')
                    }}
                    type="radio"
                  />
                  <span>
                    <strong>{t('events.walkIn.existing')}</strong>
                    {t('events.walkIn.existingHelp')}
                  </span>
                </label>
                <label>
                  <input
                    checked={walkInMode === 'new'}
                    name="walk-in-path"
                    onChange={() => {
                      if (
                        walkInRequestRef.current &&
                        walkInRequestEventIdRef.current === eventId
                      )
                        return
                      personSearchGenerationRef.current += 1
                      setWalkInMode('new')
                      setPersonResults([])
                      setIsSearchingPeople(false)
                      setSelectedPerson(null)
                      setContactError('')
                    }}
                    type="radio"
                  />
                  <span>
                    <strong>{t('events.walkIn.newVisitor')}</strong>
                    {t('events.walkIn.newHelp')}
                  </span>
                </label>
              </fieldset>

              {walkInMode === 'existing' ? (
                <div className="existing-person-picker wide-field">
                  <label>
                    <span>{t('events.walkIn.findExisting')}</span>
                    <input
                      disabled={isAddingWalkIn}
                      ref={personSearchInputRef}
                      onChange={(changeEvent) => {
                        if (
                          walkInRequestRef.current &&
                          walkInRequestEventIdRef.current === eventId
                        )
                          return
                        personSearchGenerationRef.current += 1
                        setPersonSearch(changeEvent.target.value)
                        setPersonResults([])
                        setIsSearchingPeople(false)
                        setSelectedPerson(null)
                        setContactError('')
                      }}
                      placeholder={t('events.walkIn.searchPlaceholder')}
                      type="search"
                      value={personSearch}
                    />
                  </label>
                  <p className="form-required-hint">
                    {t('events.walkIn.maskedHint')}
                  </p>
                  <div aria-live="polite" className="existing-person-results">
                    {isSearchingPeople ? (
                      <p>{t('events.walkIn.searching')}</p>
                    ) : null}
                    {!isSearchingPeople && personSearch.trim().length >= 2
                      ? personResults.map((person) => (
                          <label key={person.id}>
                            <input
                              checked={selectedPerson === person.id}
                              disabled={isAddingWalkIn}
                              name="existing-person"
                              onChange={() => {
                                if (
                                  walkInRequestRef.current &&
                                  walkInRequestEventIdRef.current === eventId
                                )
                                  return
                                setSelectedPerson(person.id)
                                setContactError('')
                              }}
                              type="radio"
                            />
                            <span>
                              <strong>{person.full_name}</strong>
                              <small>
                                {[
                                  person.preferred_name
                                    ? `Known as ${person.preferred_name}`
                                    : null,
                                  person.contact_hint,
                                  `Directory status: ${person.membership_status}`,
                                  person.current_registration_status
                                    ? `Event status: ${person.current_registration_status.replace('_', ' ')}`
                                    : t('events.walkIn.notRegistered'),
                                ]
                                  .filter(Boolean)
                                  .join(' · ')}
                              </small>
                            </span>
                          </label>
                        ))
                      : null}
                    {!isSearchingPeople &&
                    personSearch.trim().length >= 2 &&
                    personResults.length === 0 ? (
                      <p>{t('events.walkIn.noMatches')}</p>
                    ) : null}
                  </div>
                </div>
              ) : (
                <>
                  <p className="form-required-hint wide-field">
                    Full name and at least one contact method are required.
                  </p>
                  <label>
                    <span>Full name (required)</span>
                    <input
                      disabled={isAddingWalkIn}
                      required
                      value={fullName}
                      onChange={(changeEvent) =>
                        setFullName(changeEvent.target.value)
                      }
                    />
                  </label>
                  <label>
                    <span>Preferred name</span>
                    <input
                      disabled={isAddingWalkIn}
                      value={preferredName}
                      onChange={(changeEvent) =>
                        setPreferredName(changeEvent.target.value)
                      }
                    />
                  </label>
                  <label>
                    <span>Email</span>
                    <input
                      disabled={isAddingWalkIn}
                      type="email"
                      value={email}
                      onChange={(changeEvent) => {
                        setEmail(changeEvent.target.value)
                        if (!changeEvent.target.value.trim()) {
                          setPreferredContact((current) =>
                            current === 'email' ? '' : current,
                          )
                        }
                        setContactError('')
                      }}
                    />
                  </label>
                  <label>
                    <span>Phone</span>
                    <input
                      disabled={isAddingWalkIn}
                      type="tel"
                      value={phone}
                      onChange={(changeEvent) => {
                        setPhone(changeEvent.target.value)
                        if (!changeEvent.target.value.trim()) {
                          setHasWhatsapp(false)
                          setPreferredContact((current) =>
                            current === 'phone' || current === 'whatsapp'
                              ? ''
                              : current,
                          )
                        }
                        setContactError('')
                      }}
                    />
                  </label>
                  <label className="event-checkbox">
                    <input
                      checked={hasWhatsapp}
                      disabled={isAddingWalkIn || !phone.trim()}
                      onChange={(changeEvent) => {
                        setHasWhatsapp(changeEvent.target.checked)
                        if (!changeEvent.target.checked) {
                          setPreferredContact((current) =>
                            current === 'whatsapp' ? '' : current,
                          )
                        }
                      }}
                      type="checkbox"
                    />
                    <span>This phone number uses WhatsApp</span>
                  </label>
                  <label>
                    <span>WeChat ID</span>
                    <input
                      disabled={isAddingWalkIn}
                      value={wechatId}
                      onChange={(changeEvent) => {
                        setWechatId(changeEvent.target.value)
                        if (!changeEvent.target.value.trim()) {
                          setPreferredContact((current) =>
                            current === 'wechat' ? '' : current,
                          )
                        }
                        setContactError('')
                      }}
                    />
                  </label>
                  <label>
                    <span>Preferred contact</span>
                    <select
                      disabled={isAddingWalkIn}
                      value={preferredContact}
                      onChange={(changeEvent) =>
                        setPreferredContact(changeEvent.target.value)
                      }
                    >
                      <option value="">No preference</option>
                      {hasWhatsapp && phone.trim() ? (
                        <option value="whatsapp">WhatsApp</option>
                      ) : null}
                      {wechatId.trim() ? (
                        <option value="wechat">WeChat</option>
                      ) : null}
                      {phone.trim() ? (
                        <option value="phone">Phone</option>
                      ) : null}
                      {email.trim() ? (
                        <option value="email">Email</option>
                      ) : null}
                    </select>
                  </label>
                </>
              )}
              <label>
                <span>Note</span>
                <input
                  disabled={isAddingWalkIn}
                  maxLength={200}
                  value={note}
                  onChange={(changeEvent) => setNote(changeEvent.target.value)}
                />
              </label>
              {contactError ? (
                <p className="form-error wide-field" role="alert">
                  {contactError}
                </p>
              ) : null}
              <div className="event-form-actions wide-field">
                <button
                  className="secondary-button"
                  disabled={isAddingWalkIn}
                  onClick={closeWalkIn}
                  type="button"
                >
                  Cancel
                </button>
                <button
                  className="primary-button inline"
                  disabled={isAddingWalkIn}
                  type="submit"
                >
                  {isAddingWalkIn
                    ? t('events.walkIn.saving')
                    : walkInMode === 'existing'
                      ? t('events.walkIn.existingConfirm')
                      : t('events.walkIn.newConfirm')}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </main>
  )
}
