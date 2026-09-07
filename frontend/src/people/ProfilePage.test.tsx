import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  createMemoryRouter,
  RouterProvider,
  type RouteObject,
} from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import '../i18n'
import { AuthContext } from '../auth/auth-context'
import type { SessionPayload } from '../auth/types'
import type { ProfilePerson } from './types'
import { ProfilePage } from './ProfilePage'

const pastorSession: SessionPayload = {
  user: {
    id: 1,
    username: 'fictional-pastor',
    first_name: 'Fictional',
    last_name: 'Pastor',
  },
  membership: {
    church_id: 1,
    church_name: 'Fictional Church',
    role: 'pastor',
    person_id: null,
  },
}

const profile: ProfilePerson = {
  id: 1,
  full_name: 'Mia Chen',
  preferred_name: 'Mimi',
  membership_status: 'newcomer',
  gender: 'unspecified',
  date_of_birth: null,
  email: 'mia@example.test',
  phone: '+61000000001',
  wechat_id: 'mia_wechat',
  has_whatsapp: true,
  preferred_contact: 'whatsapp',
  photo_url: null,
  home_country: 'AU',
  suburb: 'Burwood',
  occupation: 'Designer',
  university: 'USYD',
  course: null,
  interests: [],
  invited_by: null,
  inviter: null,
  invitees: [],
  relationships: [],
  notes: 'Fictional notes.',
  faith_background: null,
  discipleship_stage: null,
  groups: [],
  events_attended: [],
  follow_up_history: [],
}

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

function renderProfile(path = '/people/1') {
  const routes: RouteObject[] = [
    { path: '/people/:personId', element: <ProfilePage /> },
  ]
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <AuthContext.Provider
      value={{
        isLoading: false,
        session: pastorSession,
        login: vi.fn(),
        logout: vi.fn(),
      }}
    >
      <RouterProvider router={router} />
    </AuthContext.Provider>,
  )
  return router
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('ProfilePage reliability', () => {
  it('offers retry after a transient profile failure and recovers', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({}, 503))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(profile))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderProfile()

    expect(
      await screen.findByRole('heading', {
        name: 'We could not load this profile',
      }),
    ).toBeVisible()
    expect(
      screen.getByText('Check your connection and try again.'),
    ).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Try again' }))

    expect(
      await screen.findByRole('heading', { name: 'Mia Chen', level: 1 }),
    ).toBeVisible()
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('uses the neutral inaccessible state for a missing profile', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse({}, 404))
        .mockResolvedValueOnce(jsonResponse([])),
    )

    renderProfile()

    expect(
      await screen.findByRole('heading', { name: 'Profile not available' }),
    ).toBeVisible()
    expect(
      screen.getByText(
        'This person may be outside your access or unavailable.',
      ),
    ).toBeVisible()
    expect(
      screen.queryByRole('button', { name: 'Try again' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/church/i)).not.toBeInTheDocument()
  })

  it('does not restore an old draft or apply an old save after navigation', async () => {
    const oldSave = deferred<Response>()
    const secondProfile = {
      ...profile,
      id: 2,
      full_name: 'Noah Park',
      preferred_name: null,
    }
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input)
      if (path === '/api/people/' && !init?.method) {
        return Promise.resolve(jsonResponse([]))
      }
      if (path === '/api/people/1/' && init?.method === 'PATCH') {
        return oldSave.promise
      }
      if (path === '/api/people/1/') {
        return Promise.resolve(jsonResponse(profile))
      }
      if (path === '/api/people/2/') {
        return Promise.resolve(jsonResponse(secondProfile))
      }
      throw new Error(`Unexpected request: ${path}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    const router = renderProfile()

    await user.click(await screen.findByRole('button', { name: 'Edit person' }))
    const fullName = screen.getByLabelText('Full name')
    await user.clear(fullName)
    await user.type(fullName, 'Unsaved draft name')
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    await act(async () => {
      await router.navigate('/people/2')
    })
    expect(
      await screen.findByRole('heading', { name: 'Noah Park', level: 1 }),
    ).toBeVisible()
    expect(
      screen.queryByDisplayValue('Unsaved draft name'),
    ).not.toBeInTheDocument()

    await act(async () => {
      oldSave.resolve(
        jsonResponse({ ...profile, full_name: 'Stale saved person' }),
      )
      await oldSave.promise
    })

    expect(
      screen.getByRole('heading', { name: 'Noah Park', level: 1 }),
    ).toBeVisible()
    expect(screen.queryByText('Stale saved person')).not.toBeInTheDocument()
  })

  it('blocks duplicate saves and cancel while pending, then keeps the draft on failure', async () => {
    const saveRequest = deferred<Response>()
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input)
      if (path === '/api/people/1/' && init?.method === 'PATCH') {
        return saveRequest.promise
      }
      if (path === '/api/people/1/') {
        return Promise.resolve(jsonResponse(profile))
      }
      if (path === '/api/people/') {
        return Promise.resolve(jsonResponse([]))
      }
      throw new Error(`Unexpected request: ${path}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderProfile()
    await user.click(await screen.findByRole('button', { name: 'Edit person' }))
    const preferredName = screen.getByLabelText('Preferred name')
    await user.clear(preferredName)
    await user.type(preferredName, 'Draft preferred name')
    const form = screen
      .getByRole('button', { name: 'Save changes' })
      .closest('form')
    expect(form).not.toBeNull()

    fireEvent.submit(form!)
    fireEvent.submit(form!)

    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(
      fetchMock.mock.calls.filter(
        ([path, init]) => path === '/api/people/1/' && init?.method === 'PATCH',
      ),
    ).toHaveLength(1)

    await act(async () => {
      saveRequest.reject(new Error('Temporary failure'))
      await saveRequest.promise.catch(() => undefined)
    })

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'We could not save these changes. Check the fields and retry.',
    )
    expect(screen.getByLabelText('Preferred name')).toHaveValue(
      'Draft preferred name',
    )
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeEnabled()
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: 'Save changes' }),
      ).toBeEnabled(),
    )
  })
})
