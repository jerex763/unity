import { useEffect, useRef, useState, type FormEvent } from 'react'
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

type ConfirmationState = {
  token: string
  value: Confirmation
}

type PublicEventState =
  | { status: 'loading'; event: null; token: string }
  | { status: 'ready'; event: PublicEvent; token: string }
  | { status: 'inaccessible' | 'transient'; event: null; token: string }

function eventDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'full',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function PublicRegistrationPage() {
  const { token = '' } = useParams()
  const [eventState, setEventState] = useState<PublicEventState>({
    status: 'loading',
    event: null,
    token,
  })
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [confirmationState, setConfirmationState] =
    useState<ConfirmationState | null>(null)
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [hasWhatsapp, setHasWhatsapp] = useState(false)
  const [wechatId, setWechatId] = useState('')
  const [preferredContact, setPreferredContact] = useState('')
  const [consent, setConsent] = useState(false)
  const [contactError, setContactError] = useState('')
  const [errorState, setErrorState] = useState<{
    message: string
    token: string
  } | null>(null)
  const [submittingToken, setSubmittingToken] = useState<string | null>(null)
  const loadedTokenRef = useRef<string | null>(null)

  useEffect(() => {
    let active = true
    void apiRequest<PublicEvent>(`/public/events/${token}/`)
      .then((value) => {
        if (!active) return
        if (loadedTokenRef.current !== token) {
          loadedTokenRef.current = token
          setConfirmationState(null)
          setFullName('')
          setEmail('')
          setPhone('')
          setHasWhatsapp(false)
          setWechatId('')
          setPreferredContact('')
          setConsent(false)
          setContactError('')
          setErrorState(null)
          setSubmittingToken(null)
        }
        setEventState({ status: 'ready', event: value, token })
      })
      .catch((requestError: unknown) => {
        if (!active) return
        const isNonRetryableClientError =
          requestError instanceof ApiError &&
          requestError.status >= 400 &&
          requestError.status < 500 &&
          ![408, 429].includes(requestError.status)
        setEventState({
          status: isNonRetryableClientError ? 'inaccessible' : 'transient',
          event: null,
          token,
        })
      })
    return () => {
      active = false
    }
  }, [loadAttempt, token])

  const currentEventState =
    eventState.token === token
      ? eventState
      : ({ status: 'loading', event: null, token } satisfies PublicEventState)
  const event = currentEventState.event
  const confirmation =
    confirmationState?.token === token ? confirmationState.value : null
  const error = errorState?.token === token ? errorState.message : ''
  const isSubmitting = submittingToken === token

  async function submit(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault()
    if (!event) return
    if (![email, phone, wechatId].some((value) => value.trim())) {
      setContactError(
        'Provide at least one contact method: email, phone, or WeChat ID.',
      )
      return
    }
    setContactError('')
    setErrorState(null)
    const submissionToken = token
    setSubmittingToken(submissionToken)
    try {
      const value = await apiRequest<Confirmation>(`/public/events/${token}/`, {
        method: 'POST',
        body: JSON.stringify({
          full_name: fullName,
          email,
          phone,
          has_whatsapp: hasWhatsapp,
          wechat_id: wechatId,
          preferred_contact: preferredContact,
          consent,
          notice_version: event.privacy_notice.version,
          website: '',
        }),
      })
      setConfirmationState({ token: submissionToken, value })
    } catch (requestError) {
      setErrorState({
        token: submissionToken,
        message:
          requestError instanceof ApiError && requestError.status === 429
            ? 'Too many attempts. Please wait and try again.'
            : 'We could not process the registration. Check the fields and try again.',
      })
    } finally {
      setSubmittingToken((current) =>
        current === submissionToken ? null : current,
      )
    }
  }

  if (currentEventState.status === 'loading') {
    return <main className="public-registration-page">Loading event…</main>
  }
  if (currentEventState.status === 'transient') {
    return (
      <main className="public-registration-page">
        <section className="public-registration-card">
          <h1>Registration is temporarily unavailable</h1>
          <p>Check your connection and try loading this event again.</p>
          <button
            className="primary-button"
            onClick={() => {
              setEventState({ status: 'loading', event: null, token })
              setLoadAttempt((attempt) => attempt + 1)
            }}
            type="button"
          >
            Try again
          </button>
        </section>
      </main>
    )
  }
  if (currentEventState.status === 'inaccessible' || !event) {
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
              Your full name and at least one contact method are required.
              Individual contact fields are optional.
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
                    if (!changeEvent.target.value.trim()) {
                      setPreferredContact((current) =>
                        current === 'email' ? '' : current,
                      )
                    }
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
                  type="tel"
                  value={phone}
                />
              </label>
              <label className="public-checkbox">
                <input
                  checked={hasWhatsapp}
                  disabled={!phone.trim()}
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
                <span>WeChat ID (optional)</span>
                <input
                  autoComplete="off"
                  maxLength={100}
                  onChange={(changeEvent) => {
                    setWechatId(changeEvent.target.value)
                    if (!changeEvent.target.value.trim()) {
                      setPreferredContact((current) =>
                        current === 'wechat' ? '' : current,
                      )
                    }
                    setContactError('')
                  }}
                  value={wechatId}
                />
              </label>
              <label>
                <span>Preferred contact (optional)</span>
                <select
                  onChange={(changeEvent) =>
                    setPreferredContact(changeEvent.target.value)
                  }
                  value={preferredContact}
                >
                  <option value="">No preference</option>
                  {hasWhatsapp && phone.trim() ? (
                    <option value="whatsapp">WhatsApp</option>
                  ) : null}
                  {wechatId.trim() ? (
                    <option value="wechat">WeChat</option>
                  ) : null}
                  {phone.trim() ? <option value="phone">Phone</option> : null}
                  {email.trim() ? <option value="email">Email</option> : null}
                </select>
              </label>
              {contactError ? (
                <p className="field-error" role="alert">
                  {contactError}
                </p>
              ) : null}
            </fieldset>
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
