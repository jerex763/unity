import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ApiError, apiRequest } from '../api/client'

type PublicEvent = {
  title: string
  description: string
  starts_at: string
  ends_at: string
  location: string
  registration_open: boolean
  privacy_notice: {
    version: string
    text: string
  }
}

type Confirmation = {
  accepted: true
  event_title: string
  cancellation_url: string
}

function eventDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'full',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function PublicRegistrationPage() {
  const { token = '' } = useParams()
  const [event, setEvent] = useState<PublicEvent | null>(null)
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null)
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [needsTransport, setNeedsTransport] = useState(false)
  const [consent, setConsent] = useState(false)
  const [contactError, setContactError] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    let active = true
    void apiRequest<PublicEvent>(`/public/events/${token}/`)
      .then((value) => {
        if (active) setEvent(value)
      })
      .catch(() => {
        if (active) setError('This registration link is unavailable.')
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [token])

  async function submit(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault()
    if (!event) return
    if (!email.trim() && !phone.trim()) {
      setContactError('Provide an email address or phone number.')
      return
    }
    setContactError('')
    setError('')
    setIsSubmitting(true)
    try {
      const value = await apiRequest<Confirmation>(`/public/events/${token}/`, {
        method: 'POST',
        body: JSON.stringify({
          full_name: fullName,
          email,
          phone,
          needs_transport: needsTransport,
          consent,
          notice_version: event.privacy_notice.version,
          website: '',
        }),
      })
      setConfirmation(value)
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.status === 429
          ? 'Too many attempts. Please wait and try again.'
          : 'We could not process the registration. Check the fields and try again.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return <main className="public-registration-page">Loading event…</main>
  }
  if (!event || error === 'This registration link is unavailable.') {
    return (
      <main className="public-registration-page">
        <section className="public-registration-card">
          <h1>Registration unavailable</h1>
          <p>This link may have expired or been withdrawn by the organiser.</p>
        </section>
      </main>
    )
  }
  if (confirmation) {
    return (
      <main className="public-registration-page">
        <section className="public-registration-card confirmation-card">
          <p className="eyebrow">Registration received</p>
          <h1>{confirmation.event_title}</h1>
          <p role="status">Your registration request has been accepted.</p>
          <p>Keep this private link if you may need to cancel.</p>
          <Link
            className="secondary-button public-cancel-link"
            to={new URL(confirmation.cancellation_url).pathname}
          >
            Cancel this registration
          </Link>
        </section>
      </main>
    )
  }

  return (
    <main className="public-registration-page">
      <section className="public-registration-card">
        <p className="eyebrow">Event registration</p>
        <h1>{event.title}</h1>
        <p className="public-event-time">{eventDate(event.starts_at)}</p>
        {event.location ? <p>{event.location}</p> : null}
        {event.description ? <p>{event.description}</p> : null}

        {!event.registration_open ? (
          <p className="form-error" role="alert">
            Registration is closed for this event.
          </p>
        ) : (
          <form className="public-registration-form" onSubmit={submit}>
            <p className="form-required-hint">
              Fields marked (required) must be completed. All others are
              optional.
            </p>
            <label>
              <span>
                Full name{' '}
                <strong className="required-marker">(required)</strong>
              </span>
              <input
                autoComplete="name"
                maxLength={200}
                onChange={(changeEvent) =>
                  setFullName(changeEvent.target.value)
                }
                required
                value={fullName}
              />
            </label>
            <fieldset>
              <legend>
                Contact <strong className="required-marker">(required)</strong>
              </legend>
              <p>Provide at least one. Each individual field is optional.</p>
              <label>
                <span>Email (optional)</span>
                <input
                  autoComplete="email"
                  onChange={(changeEvent) => {
                    setEmail(changeEvent.target.value)
                    setContactError('')
                  }}
                  type="email"
                  value={email}
                />
              </label>
              <label>
                <span>Phone (optional)</span>
                <input
                  autoComplete="tel"
                  maxLength={30}
                  onChange={(changeEvent) => {
                    setPhone(changeEvent.target.value)
                    setContactError('')
                  }}
                  type="tel"
                  value={phone}
                />
              </label>
              {contactError ? (
                <p className="field-error" role="alert">
                  {contactError}
                </p>
              ) : null}
            </fieldset>
            <label className="public-checkbox">
              <input
                checked={needsTransport}
                onChange={(changeEvent) =>
                  setNeedsTransport(changeEvent.target.checked)
                }
                type="checkbox"
              />
              <span>Request transport (optional)</span>
            </label>
            <section className="privacy-notice" aria-labelledby="privacy-title">
              <h2 id="privacy-title">Privacy notice</h2>
              <p>{event.privacy_notice.text}</p>
              <small>Version {event.privacy_notice.version}</small>
            </section>
            <label className="public-checkbox consent-checkbox">
              <input
                checked={consent}
                onChange={(changeEvent) =>
                  setConsent(changeEvent.target.checked)
                }
                required
                type="checkbox"
              />
              <span>
                I have read this notice and explicitly consent to this
                collection and use.{' '}
                <strong className="required-marker">(required)</strong>
              </span>
            </label>
            <input
              aria-hidden="true"
              className="honeypot"
              name="website"
              tabIndex={-1}
            />
            {error ? (
              <p className="form-error" role="alert">
                {error}
              </p>
            ) : null}
            <button
              className="primary-button"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? 'Submitting…' : 'Register'}
            </button>
          </form>
        )}
      </section>
    </main>
  )
}

export function PublicCancellationPage() {
  const { token = '' } = useParams()
  const [state, setState] = useState<'ready' | 'saving' | 'done' | 'error'>(
    'ready',
  )

  async function cancel() {
    setState('saving')
    try {
      await apiRequest(`/public/registrations/${token}/cancel/`, {
        method: 'POST',
      })
      setState('done')
    } catch {
      setState('error')
    }
  }

  return (
    <main className="public-registration-page">
      <section className="public-registration-card confirmation-card">
        <p className="eyebrow">Event registration</p>
        <h1>Cancel registration</h1>
        {state === 'done' ? (
          <p role="status">Your registration has been cancelled.</p>
        ) : (
          <>
            <p>
              This private link authorises cancellation. This action cannot be
              undone here.
            </p>
            {state === 'error' ? (
              <p className="form-error" role="alert">
                We could not process the cancellation. The link may already have
                been used.
              </p>
            ) : null}
            <button
              className="primary-button"
              disabled={state === 'saving'}
              onClick={() => void cancel()}
              type="button"
            >
              {state === 'saving' ? 'Cancelling…' : 'Cancel registration'}
            </button>
          </>
        )}
      </section>
    </main>
  )
}
