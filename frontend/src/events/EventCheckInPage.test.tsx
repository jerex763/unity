import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthContext } from '../auth/auth-context'
import '../i18n'
import { EventCheckInPage } from './EventCheckInPage'
import type { CheckInPerson, ChurchEvent, EventRegistration } from './types'

const session = {
  user: {
    id: 1,
    username: 'fictional-leader',
    first_name: 'Fictional',
    last_name: 'Leader',
  },
  membership: {
    church_id: 1,
    church_name: 'Fictional Church',
    role: 'leader' as const,
    person_id: null,
  },
}

const event: ChurchEvent = {
  id: 7,
  group: null,
  title: 'Fictional Community Lunch',
  description: '',
  starts_at: '2099-09-07T10:00:00Z',
  ends_at: '2099-09-07T12:00:00Z',
  location: 'Fictional Hall',
  capacity: null,
  signup_opens: true,
  signup_closes_at: null,
  registration_open: true,
  places_available: true,
  my_registration: null,
  public_registration_enabled: true,
  registered_count: 2,
  waitlisted_count: 0,
  created_by: 'fictional-admin',
  created_at: '2099-09-01T00:00:00Z',
  updated_at: '2099-09-01T00:00:00Z',
}

const registrations: EventRegistration[] = [
  {
    id: 101,
    person: { id: 11, full_name: 'Mia Chen', preferred_name: 'Mimi' },
    status: 'registered',
    note: '',
    registered_at: '2099-09-01T00:00:00Z',
    checked_in_at: null,
    checkin_method: null,
  },
  {
    id: 102,
    person: { id: 12, full_name: 'Noah Park', preferred_name: null },
    status: 'registered',
    note: '',
    registered_at: '2099-09-01T00:00:00Z',
    checked_in_at: null,
    checkin_method: null,
  },
]

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function deferred<Value>() {
  let resolve!: (value: Value) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<Value>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, reject, resolve }
}

function renderCheckIn() {
  return render(
    <MemoryRouter initialEntries={['/events/7/check-in']}>
      <AuthContext.Provider
        value={{
          isLoading: false,
          session,
          login: vi.fn(),
          logout: vi.fn(),
        }}
      >
        <Routes>
          <Route
            path="/events/:eventId/check-in"
            element={<EventCheckInPage />}
          />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  )
}

function baseFetch(
  handleRequest: (url: string, init?: RequestInit) => Promise<Response>,
) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/events/') return Promise.resolve(jsonResponse([event]))
    if (url === '/api/events/7/registrations/') {
      return Promise.resolve(jsonResponse(registrations))
    }
    return handleRequest(url, init)
  })
}

function checkedIn(registration: EventRegistration) {
  return {
    ...registration,
    checked_in_at: '2099-09-07T10:05:00Z',
    checkin_method: 'manual' as const,
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('event check-in request reliability', () => {
  it('submits a row once while leaving unrelated registrations operable', async () => {
    const miaRequest = deferred<Response>()
    const noahRequest = deferred<Response>()
    const fetchMock = baseFetch((url) => {
      if (url.includes('/registrations/101/check-in/'))
        return miaRequest.promise
      if (url.includes('/registrations/102/check-in/'))
        return noahRequest.promise
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    renderCheckIn()
    await screen.findByRole('heading', { name: event.title })
    fireEvent.click(screen.getByRole('button', { name: 'All' }))
    const miaRow = screen.getByText('Mia Chen').closest('article')
    const noahRow = screen.getByText('Noah Park').closest('article')
    expect(miaRow).not.toBeNull()
    expect(noahRow).not.toBeNull()
    const miaButton = within(miaRow as HTMLElement).getByRole('button', {
      name: 'Check in',
    })

    act(() => {
      fireEvent.click(miaButton)
      fireEvent.click(miaButton)
    })

    expect(
      within(miaRow as HTMLElement).getByRole('button', {
        name: 'Checking in…',
      }),
    ).toBeDisabled()
    const noahButton = within(noahRow as HTMLElement).getByRole('button', {
      name: 'Check in',
    })
    expect(noahButton).toBeEnabled()
    fireEvent.click(noahButton)

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.filter(([url]) =>
          String(url).includes('/registrations/101/check-in/'),
        ),
      ).toHaveLength(1)
      expect(
        fetchMock.mock.calls.filter(([url]) =>
          String(url).includes('/registrations/102/check-in/'),
        ),
      ).toHaveLength(1)
    })

    await act(async () => {
      miaRequest.resolve(jsonResponse(checkedIn(registrations[0])))
      await miaRequest.promise
    })
    expect(
      within(miaRow as HTMLElement).getByRole('button', {
        name: 'Undo check-in',
      }),
    ).toBeEnabled()
    expect(
      within(noahRow as HTMLElement).getByRole('button', {
        name: 'Checking in…',
      }),
    ).toBeDisabled()

    await act(async () => {
      noahRequest.resolve(jsonResponse(checkedIn(registrations[1])))
      await noahRequest.promise
    })
  })

  it('re-enables a failed registration check-in for retry', async () => {
    const firstRequest = deferred<Response>()
    const retryRequest = deferred<Response>()
    let attempt = 0
    const fetchMock = baseFetch((url) => {
      if (url.includes('/registrations/101/check-in/')) {
        attempt += 1
        return attempt === 1 ? firstRequest.promise : retryRequest.promise
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    renderCheckIn()
    await screen.findByRole('heading', { name: event.title })
    const miaRow = screen
      .getByText('Mia Chen')
      .closest('article') as HTMLElement
    fireEvent.click(within(miaRow).getByRole('button', { name: 'Check in' }))

    await act(async () => {
      firstRequest.reject(new Error('Fictional network failure'))
      await firstRequest.promise.catch(() => undefined)
    })

    expect(
      await screen.findByText('We could not update attendance. Retry.'),
    ).toBeVisible()
    const retryButton = within(miaRow).getByRole('button', {
      name: 'Check in',
    })
    expect(retryButton).toBeEnabled()
    fireEvent.click(retryButton)
    expect(attempt).toBe(2)

    await act(async () => {
      retryRequest.resolve(jsonResponse(checkedIn(registrations[0])))
      await retryRequest.promise
    })
    expect(await screen.findByText('Mia Chen is checked in.')).toBeVisible()
  })

  it('guards walk-in submission and preserves fields after failure', async () => {
    const firstRequest = deferred<Response>()
    const retryRequest = deferred<Response>()
    let attempt = 0
    const walkInRegistration: EventRegistration = {
      ...checkedIn(registrations[0]),
      id: 201,
      status: 'walk_in',
      person: {
        id: 21,
        full_name: 'Fictional Visitor',
        preferred_name: null,
      },
    }
    const fetchMock = baseFetch((url) => {
      if (url === '/api/events/7/walk-ins/') {
        attempt += 1
        return attempt === 1 ? firstRequest.promise : retryRequest.promise
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderCheckIn()
    await screen.findByRole('heading', { name: event.title })
    await user.click(screen.getByRole('button', { name: 'Add walk-in' }))
    const dialog = screen.getByRole('dialog', { name: 'Add walk-in' })
    await user.click(within(dialog).getByRole('radio', { name: /New visitor/ }))
    const fullName = within(dialog).getByLabelText('Full name (required)')
    const email = within(dialog).getByLabelText('Email')
    const note = within(dialog).getByLabelText('Note')
    await user.type(fullName, 'Fictional Visitor')
    await user.type(email, 'visitor@example.test')
    await user.type(note, 'Keep this fictional note')
    const form = within(dialog)
      .getByRole('button', { name: 'Add visitor and check in' })
      .closest('form') as HTMLFormElement

    act(() => {
      fireEvent.submit(form)
      fireEvent.submit(form)
    })

    expect(attempt).toBe(1)
    expect(
      within(dialog).getByRole('button', { name: 'Adding…' }),
    ).toBeDisabled()
    expect(fullName).toBeDisabled()
    expect(email).toBeDisabled()
    expect(
      within(dialog).getByRole('radio', { name: /Existing person/ }),
    ).toBeDisabled()
    for (const cancel of within(dialog).getAllByRole('button', {
      name: 'Cancel',
    })) {
      expect(cancel).toBeDisabled()
    }

    await act(async () => {
      firstRequest.reject(new Error('Fictional network failure'))
      await firstRequest.promise.catch(() => undefined)
    })

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      'We could not add this walk-in. Check the details and retry.',
    )
    expect(fullName).toHaveValue('Fictional Visitor')
    expect(email).toHaveValue('visitor@example.test')
    expect(note).toHaveValue('Keep this fictional note')
    expect(fullName).toBeEnabled()
    await user.click(
      within(dialog).getByRole('button', {
        name: 'Add visitor and check in',
      }),
    )
    expect(attempt).toBe(2)

    await act(async () => {
      retryRequest.resolve(jsonResponse(walkInRegistration, 201))
      await retryRequest.promise
    })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(
      await screen.findByText('Fictional Visitor was added and checked in.'),
    ).toBeVisible()
  })

  it('does not carry a stale lookup spinner or error into a reopened dialog', async () => {
    const staleLookup = deferred<Response>()
    const freshLookup = deferred<Response>()
    let lookupAttempt = 0
    const person: CheckInPerson = {
      id: 31,
      full_name: 'Noah Example',
      preferred_name: null,
      membership_status: 'member',
      current_registration_status: null,
      contact_hint: 'n***@example.test',
    }
    const fetchMock = baseFetch((url) => {
      if (url.includes('/check-in/people/')) {
        lookupAttempt += 1
        return lookupAttempt === 1 ? staleLookup.promise : freshLookup.promise
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderCheckIn()
    await screen.findByRole('heading', { name: event.title })
    await user.click(screen.getByRole('button', { name: 'Add walk-in' }))
    let dialog = screen.getByRole('dialog', { name: 'Add walk-in' })
    await user.type(within(dialog).getByLabelText('Find existing person'), 'Mi')
    expect(await within(dialog).findByText('Searching…')).toBeVisible()
    await user.click(
      within(dialog).getAllByRole('button', { name: 'Cancel' })[0],
    )

    await user.click(screen.getByRole('button', { name: 'Add walk-in' }))
    dialog = screen.getByRole('dialog', { name: 'Add walk-in' })
    expect(within(dialog).queryByText('Searching…')).not.toBeInTheDocument()
    await act(async () => {
      staleLookup.reject(new Error('Stale fictional lookup failure'))
      await staleLookup.promise.catch(() => undefined)
    })
    expect(
      within(dialog).queryByText('We could not search people. Retry.'),
    ).not.toBeInTheDocument()

    await user.type(
      within(dialog).getByLabelText('Find existing person'),
      'Noah',
    )
    expect(await within(dialog).findByText('Searching…')).toBeVisible()
    await act(async () => {
      freshLookup.resolve(jsonResponse([person]))
      await freshLookup.promise
    })
    expect(await within(dialog).findByText('Noah Example')).toBeVisible()
  })

  it('ignores a prior event response and unlocks the same registration id for the new event', async () => {
    const oldEventRequest = deferred<Response>()
    const newEventRequest = deferred<Response>()
    const nextRosterRequest = deferred<Response>()
    const nextEvent = { ...event, id: 8, title: 'Fictional Evening Gathering' }
    const nextRegistration: EventRegistration = {
      ...registrations[0],
      person: {
        id: 41,
        full_name: 'Ava Example',
        preferred_name: null,
      },
    }
    const fetchMock = vi.fn(
      (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
        const url = String(input)
        if (url === '/api/events/') {
          return Promise.resolve(jsonResponse([event, nextEvent]))
        }
        if (url === '/api/events/7/registrations/') {
          return Promise.resolve(jsonResponse([registrations[0]]))
        }
        if (url === '/api/events/8/registrations/') {
          return nextRosterRequest.promise
        }
        if (
          init?.method === 'POST' &&
          url === '/api/events/7/registrations/101/check-in/'
        ) {
          return oldEventRequest.promise
        }
        if (
          init?.method === 'POST' &&
          url === '/api/events/8/registrations/101/check-in/'
        ) {
          return newEventRequest.promise
        }
        throw new Error(`Unexpected request: ${url}`)
      },
    )
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(
      <MemoryRouter initialEntries={['/events/7/check-in']}>
        <AuthContext.Provider
          value={{
            isLoading: false,
            session,
            login: vi.fn(),
            logout: vi.fn(),
          }}
        >
          <Link to="/events/8/check-in">Next fictional event</Link>
          <Routes>
            <Route
              path="/events/:eventId/check-in"
              element={<EventCheckInPage />}
            />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>,
    )

    await screen.findByRole('heading', { name: event.title })
    fireEvent.click(screen.getByRole('button', { name: 'Check in' }))
    await user.click(screen.getByRole('link', { name: 'Next fictional event' }))
    expect(screen.queryByText(event.title)).not.toBeInTheDocument()
    expect(screen.queryByText('Mia Chen')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Check in' }),
    ).not.toBeInTheDocument()
    expect(screen.getByText('Loading check-in…')).toBeVisible()

    await act(async () => {
      nextRosterRequest.resolve(jsonResponse([nextRegistration]))
      await nextRosterRequest.promise
    })
    await screen.findByRole('heading', { name: nextEvent.title })
    const nextRow = screen.getByText('Ava Example').closest('article')
    expect(nextRow).not.toBeNull()
    const nextButton = within(nextRow as HTMLElement).getByRole('button', {
      name: 'Check in',
    })
    expect(nextButton).toBeEnabled()
    fireEvent.click(nextButton)

    await act(async () => {
      oldEventRequest.resolve(jsonResponse(checkedIn(registrations[0])))
      await oldEventRequest.promise
    })
    expect(
      screen.queryByText('Mia Chen is checked in.'),
    ).not.toBeInTheDocument()
    expect(
      within(nextRow as HTMLElement).getByText(/Not checked in/),
    ).toBeVisible()

    await act(async () => {
      newEventRequest.resolve(jsonResponse(checkedIn(nextRegistration)))
      await newEventRequest.promise
    })
    expect(await screen.findByText('Ava Example is checked in.')).toBeVisible()
  })

  it('does not restore stale walk-in pending state after leaving and returning', async () => {
    const walkInRequest = deferred<Response>()
    const nextEvent = { ...event, id: 8, title: 'Fictional Evening Gathering' }
    const fetchMock = vi.fn((input: RequestInfo | URL): Promise<Response> => {
      const url = String(input)
      if (url === '/api/events/') {
        return Promise.resolve(jsonResponse([event, nextEvent]))
      }
      if (url === '/api/events/7/registrations/') {
        return Promise.resolve(jsonResponse(registrations))
      }
      if (url === '/api/events/8/registrations/') {
        return Promise.resolve(jsonResponse([]))
      }
      if (url === '/api/events/7/walk-ins/') return walkInRequest.promise
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(
      <MemoryRouter initialEntries={['/events/7/check-in']}>
        <AuthContext.Provider
          value={{
            isLoading: false,
            session,
            login: vi.fn(),
            logout: vi.fn(),
          }}
        >
          <Link to="/events/8/check-in">Next fictional event</Link>
          <Link to="/events/7/check-in">Previous fictional event</Link>
          <Routes>
            <Route
              path="/events/:eventId/check-in"
              element={<EventCheckInPage />}
            />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>,
    )

    await screen.findByRole('heading', { name: event.title })
    await user.click(screen.getByRole('button', { name: 'Add walk-in' }))
    const dialog = screen.getByRole('dialog', { name: 'Add walk-in' })
    await user.click(within(dialog).getByRole('radio', { name: /New visitor/ }))
    await user.type(
      within(dialog).getByLabelText('Full name (required)'),
      'Fictional Visitor',
    )
    await user.type(
      within(dialog).getByLabelText('Email'),
      'visitor@example.test',
    )
    fireEvent.submit(
      within(dialog)
        .getByRole('button', { name: 'Add visitor and check in' })
        .closest('form') as HTMLFormElement,
    )
    expect(
      within(dialog).getByRole('button', { name: 'Adding…' }),
    ).toBeDisabled()

    fireEvent.click(screen.getByRole('link', { name: 'Next fictional event' }))
    await screen.findByRole('heading', { name: nextEvent.title })
    await act(async () => {
      walkInRequest.resolve(jsonResponse(checkedIn(registrations[0]), 201))
      await walkInRequest.promise
    })
    await user.click(
      screen.getByRole('link', { name: 'Previous fictional event' }),
    )
    await screen.findByRole('heading', { name: event.title })
    await user.click(screen.getByRole('button', { name: 'Add walk-in' }))
    const reopenedDialog = screen.getByRole('dialog', { name: 'Add walk-in' })
    expect(
      within(reopenedDialog).getByRole('radio', { name: /Existing person/ }),
    ).toBeEnabled()
    expect(
      within(reopenedDialog).getByRole('button', {
        name: 'Check in selected person',
      }),
    ).toBeEnabled()
  })
})
