import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../auth/auth-context'
import type { SessionPayload } from '../auth/types'
import '../i18n'
import { EventsPage } from './EventsPage'

const session: SessionPayload = {
  user: {
    id: 1,
    username: 'fictional',
    first_name: 'Fictional',
    last_name: 'Leader',
  },
  membership: {
    church_id: 1,
    church_name: 'Fictional Church',
    role: 'leader',
    person_id: null,
  },
}
const event = {
  id: 21,
  group: null,
  title: 'Fictional Lunch',
  description: '',
  starts_at: '2099-07-30T08:00:00Z',
  ends_at: '2099-07-30T10:00:00Z',
  location: '',
  capacity: null,
  signup_opens: true,
  signup_closes_at: null,
  registration_open: true,
  places_available: true,
  my_registration: null,
  public_registration_enabled: true,
  registered_count: 0,
  waitlisted_count: 0,
}
const url = 'https://example.invalid/register/fictional-token'
function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status })
}
function mock(link: () => Promise<Response>, overrides = {}) {
  const fetcher = vi.fn((path: string, init?: RequestInit) => {
    void init
    if (path.endsWith('/public-link/')) return link()
    return Promise.resolve(
      json(path === '/api/events/' ? [{ ...event, ...overrides }] : []),
    )
  })
  vi.stubGlobal('fetch', fetcher)
  return fetcher
}
function tree(value = session) {
  return (
    <AuthContext.Provider
      value={{
        session: value,
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
      }}
    >
      <MemoryRouter>
        <EventsPage />
      </MemoryRouter>
    </AuthContext.Provider>
  )
}
async function ready() {
  await screen.findByRole('heading', { name: 'Fictional Lunch' })
}
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('public link recovery', () => {
  it('retrieves only on explicit actions, including a remount, with no rotation', async () => {
    const fetcher = mock(async () => json({ url }))
    const view = render(tree())
    await ready()
    expect(
      fetcher.mock.calls.filter(([path]) => path.endsWith('/public-link/')),
    ).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Show link' }))
    expect(await screen.findByLabelText('Public registration URL')).toHaveValue(
      url,
    )
    view.unmount()
    render(tree())
    await ready()
    expect(
      screen.queryByLabelText('Public registration URL'),
    ).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show link' }))
    expect(await screen.findByLabelText('Public registration URL')).toHaveValue(
      url,
    )
    const calls = fetcher.mock.calls.filter(([path]) =>
      path.endsWith('/public-link/'),
    )
    expect(calls).toHaveLength(2)
    expect(
      calls.every(
        ([, init]) => init?.method === 'GET' && init.cache === 'no-store',
      ),
    ).toBe(true)
  })
  it('explains legacy links without automatically replacing them', async () => {
    const fetcher = mock(async () => json({ code: 'legacy_link' }, 409))
    render(tree())
    await ready()
    fireEvent.click(screen.getByRole('button', { name: 'Show link' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This older link cannot be displayed again',
    )
    expect(
      fetcher.mock.calls.filter(([path]) => path.endsWith('/public-link/')),
    ).toHaveLength(1)
    expect(
      screen.queryByLabelText('Public registration URL'),
    ).not.toBeInTheDocument()
  })
  it('retries temporary failure and reveals selectable URL after clipboard denial', async () => {
    let attempts = 0
    mock(async () =>
      ++attempts === 1
        ? json({ code: 'recovery_unavailable' }, 503)
        : json({ url }),
    )
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockRejectedValue(new Error('Denied')) },
    })
    render(tree())
    await ready()
    fireEvent.click(screen.getByRole('button', { name: 'Copy link' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Retry' }))
    const input = (await screen.findByLabelText(
      'Public registration URL',
    )) as HTMLInputElement
    expect(input).toHaveValue(url)
    fireEvent.focus(input)
    expect(input.selectionEnd).toBe(url.length)
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Select and copy the link manually',
    )
    expect(attempts).toBe(2)
  })
  it('deduplicates immediately and disables every link action while pending', async () => {
    let resolve!: (response: Response) => void
    const fetcher = mock(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    render(tree())
    await ready()
    const show = screen.getByRole('button', { name: 'Show link' })
    act(() => {
      fireEvent.click(show)
      fireEvent.click(show)
    })
    for (const name of [
      'Show link',
      'Copy link',
      'Revoke link',
      'Replace public link…',
    ])
      expect(screen.getByRole('button', { name })).toBeDisabled()
    expect(
      fetcher.mock.calls.filter(([path]) => path.endsWith('/public-link/')),
    ).toHaveLength(1)
    await act(async () => {
      resolve(json({ url }))
    })
    expect(await screen.findByLabelText('Public registration URL')).toHaveValue(
      url,
    )
  })
  it('discards late URL on identity change and does not expose controls to members', async () => {
    let resolve!: (response: Response) => void
    mock(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const view = render(tree())
    await ready()
    fireEvent.click(screen.getByRole('button', { name: 'Show link' }))
    view.rerender(
      tree({
        ...session,
        membership: { ...session.membership, role: 'member' },
      }),
    )
    await ready()
    await act(async () => {
      resolve(json({ url }))
    })
    expect(
      screen.queryByLabelText('Public registration URL'),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', {
        name: /public link|Copy link|Show link|Revoke link/,
      }),
    ).not.toBeInTheDocument()
  })
  it('does not copy a delayed response after switching church', async () => {
    let resolve!: (response: Response) => void
    mock(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    const view = render(tree())
    await ready()
    fireEvent.click(screen.getByRole('button', { name: 'Copy link' }))
    view.rerender(
      tree({ ...session, membership: { ...session.membership, church_id: 2 } }),
    )
    await ready()
    await act(async () => {
      resolve(json({ url }))
    })
    expect(writeText).not.toHaveBeenCalled()
    expect(
      screen.queryByLabelText('Public registration URL'),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copy link' })).toBeEnabled()
  })
  it('fetches fresh on copy after showing and hides stale URL on failed fetch', async () => {
    let attempts = 0
    mock(async () =>
      ++attempts === 1 ? json({ url }) : json({ code: 'not_found' }, 404),
    )
    render(tree())
    await ready()
    fireEvent.click(screen.getByRole('button', { name: 'Show link' }))
    await screen.findByLabelText('Public registration URL')
    fireEvent.click(screen.getByRole('button', { name: 'Copy link' }))
    await screen.findByRole('alert')
    expect(
      screen.queryByLabelText('Public registration URL'),
    ).not.toBeInTheDocument()
    expect(attempts).toBe(2)
  })
  it('keeps closed registration unavailable without GET', async () => {
    const fetcher = mock(async () => json({ url }), {
      registration_open: false,
    })
    render(tree())
    await ready()
    expect(
      screen.getByText(
        'Registration is closed. The link cannot accept new registrations.',
      ),
    ).toBeVisible()
    expect(screen.getByRole('button', { name: 'Show link' })).toBeDisabled()
    expect(
      fetcher.mock.calls.filter(([path]) => path.endsWith('/public-link/')),
    ).toHaveLength(0)
  })
  it('can create and revoke without retaining raw creation URL', async () => {
    const fetcher = mock(async () => json({ url }), {
      public_registration_enabled: false,
    })
    render(tree())
    await ready()
    fireEvent.click(screen.getByRole('button', { name: 'Create public link' }))
    await screen.findByRole('button', { name: 'Show link' })
    expect(
      screen.queryByLabelText('Public registration URL'),
    ).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Revoke link' }))
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: 'Create public link' }),
      ).toBeEnabled(),
    )
    expect(
      fetcher.mock.calls
        .filter(([path]) => path.endsWith('/public-link/'))
        .map(([, init]) => init?.method),
    ).toEqual(['POST', 'DELETE'])
  })
})
