import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from './App'
import { AuthProvider } from './auth/AuthContext'
import './i18n'

const session = {
  user: {
    id: 1,
    username: 'alex',
    first_name: 'Alex',
    last_name: 'Chen',
  },
  membership: {
    church_id: 1,
    church_name: 'Unity Church',
    role: 'leader' as const,
  },
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function renderApp(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('App authentication flow', () => {
  it('redirects signed-out visitors to the login form', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, 403)))

    renderApp()

    expect(
      await screen.findByRole('heading', { name: 'Sign in' }),
    ).toBeVisible()
  })

  it('signs in and shows the authenticated dashboard', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({}, 403))
      .mockResolvedValueOnce(jsonResponse(session))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderApp('/login')
    await user.type(await screen.findByLabelText('Username'), 'alex')
    await user.type(screen.getByLabelText('Password'), 'secret')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(
      await screen.findByRole('heading', { name: 'Welcome back, Alex' }),
    ).toBeVisible()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(fetchMock.mock.calls[1]?.[0]).toBe('/api/auth/login/')
  })
})

describe('People directory', () => {
  const people = [
    {
      id: 1,
      full_name: 'Mia Chen',
      preferred_name: 'Mimi',
      membership_status: 'newcomer',
      email: 'mia@example.test',
      phone: '+61000000001',
      photo_url: null,
      suburb: 'Burwood',
      university: 'USYD',
      groups: [{ id: 11, name: 'Friday Community' }],
    },
    {
      id: 2,
      full_name: 'Noah Park',
      preferred_name: null,
      membership_status: 'member',
      email: null,
      phone: '+61000000002',
      photo_url: null,
      suburb: 'Rhodes',
      university: 'UTS',
      groups: [{ id: 12, name: 'Sunday Team' }],
    },
    {
      id: 3,
      full_name: 'Ava Singh',
      preferred_name: null,
      membership_status: 'regular',
      email: 'ava@example.test',
      phone: null,
      photo_url: null,
      suburb: null,
      university: 'USYD',
      groups: [{ id: 11, name: 'Friday Community' }],
    },
  ]

  it('searches and filters the visible church directory', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(session))
        .mockResolvedValueOnce(jsonResponse(people)),
    )
    const user = userEvent.setup()

    renderApp('/people')

    expect(
      await screen.findByRole('heading', { name: 'People directory' }),
    ).toBeVisible()
    expect(await screen.findByText('Mia Chen')).toBeVisible()
    expect(screen.getByText('Noah Park')).toBeVisible()
    expect(screen.getByText('Ava Singh')).toBeVisible()

    await user.type(screen.getByLabelText('Search people by name'), 'mimi')
    expect(screen.getByText('Mia Chen')).toBeVisible()
    expect(screen.queryByText('Noah Park')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    await user.selectOptions(screen.getByLabelText('Status'), 'member')
    expect(screen.getByText('Noah Park')).toBeVisible()
    expect(screen.queryByText('Mia Chen')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    await user.selectOptions(
      screen.getByLabelText('Group'),
      screen.getByRole('option', { name: 'Friday Community' }),
    )
    expect(screen.getByText('Mia Chen')).toBeVisible()
    expect(screen.getByText('Ava Singh')).toBeVisible()
    expect(screen.queryByText('Noah Park')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    await user.selectOptions(screen.getByLabelText('University'), 'UTS')
    expect(screen.getByText('Noah Park')).toBeVisible()
    expect(screen.queryByText('Ava Singh')).not.toBeInTheDocument()
  })

  it('shows a recoverable empty result state', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(session))
        .mockResolvedValueOnce(jsonResponse(people)),
    )
    const user = userEvent.setup()

    renderApp('/people')
    await user.type(
      await screen.findByLabelText('Search people by name'),
      'nobody here',
    )

    expect(
      screen.getByRole('heading', {
        name: 'No people match these filters',
      }),
    ).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(await screen.findByText('Mia Chen')).toBeVisible()
  })
})
