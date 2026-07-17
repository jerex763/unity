import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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
    person_id: null,
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
      .mockResolvedValueOnce(jsonResponse([]))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderApp('/login')
    await user.type(await screen.findByLabelText('Username'), 'alex')
    await user.type(screen.getByLabelText('Password'), 'secret')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(
      await screen.findByRole('heading', { name: 'Welcome back, Alex' }),
    ).toBeVisible()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    expect(fetchMock.mock.calls[1]?.[0]).toBe('/api/auth/login/')
  })

  it('shows open assignments due first on the dashboard', async () => {
    const myFollowUps = [
      {
        id: 72,
        person: {
          id: 2,
          full_name: 'Noah Park',
          preferred_name: null,
          phone: null,
          email: 'noah@example.test',
        },
        source: 'walk_in',
        engagement: 'possible',
        status: 'assigned',
        assigned_to: 1,
        assigned_to_name: 'alex',
        due_at: '2026-07-19',
        closed_at: null,
        outcome: null,
        created_at: '2026-07-17T01:00:00Z',
        updated_at: '2026-07-17T01:00:00Z',
      },
      {
        id: 73,
        person: {
          id: 3,
          full_name: 'Ava Singh',
          preferred_name: null,
          phone: '+61000000003',
          email: null,
        },
        source: 'event_visit',
        engagement: 'likely',
        status: 'in_progress',
        assigned_to: 1,
        assigned_to_name: 'alex',
        due_at: null,
        closed_at: null,
        outcome: null,
        created_at: '2026-07-17T02:00:00Z',
        updated_at: '2026-07-17T02:00:00Z',
      },
    ]
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(session))
      .mockResolvedValueOnce(jsonResponse(myFollowUps))
    vi.stubGlobal('fetch', fetchMock)

    renderApp('/')

    expect(
      await screen.findByRole('region', { name: 'My follow-ups' }),
    ).toBeVisible()
    expect(await screen.findByText('Noah Park')).toBeVisible()
    expect(screen.getByText('Ava Singh')).toBeVisible()
    expect(screen.getByText('No due date')).toBeVisible()
    expect(fetchMock.mock.calls[1]?.[0]).toBe('/api/follow-ups/mine/')
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

describe('Person profile', () => {
  const profile = {
    id: 1,
    full_name: 'Mia Chen',
    preferred_name: 'Mimi',
    membership_status: 'newcomer',
    gender: 'unspecified',
    date_of_birth: null,
    email: 'mia@example.test',
    phone: '+61000000001',
    has_whatsapp: true,
    photo_url: null,
    home_country: 'AU',
    suburb: 'Burwood',
    occupation: 'Designer',
    university: 'USYD',
    course: null,
    interests: ['Community'],
    invited_by: 2,
    inviter: {
      id: 2,
      full_name: 'Noah Park',
      preferred_name: null,
      photo_url: null,
    },
    invitees: [],
    relationships: [
      {
        id: 41,
        kind: 'friend',
        person: {
          id: 3,
          full_name: 'Ava Singh',
          preferred_name: null,
          photo_url: null,
        },
        created_at: '2026-07-01T02:00:00Z',
      },
    ],
    notes: 'Met at a fictional welcome lunch.',
    groups: [
      {
        id: 11,
        name: 'Friday Community',
        role: 'member',
        joined_at: '2026-06-01',
      },
    ],
    events_attended: [
      {
        id: 21,
        title: 'Community Lunch',
        starts_at: '2026-07-12T02:00:00Z',
        location: 'Main Hall',
        checked_in_at: '2026-07-12T02:10:00Z',
      },
    ],
    follow_up_history: [
      {
        id: 31,
        source: 'event_visit',
        status: 'closed',
        assigned_to: 'alex',
        due_at: null,
        closed_at: '2026-07-14T02:00:00Z',
        outcome: 'Connected with Friday Community.',
      },
    ],
  }

  it('shows role-gated sections and saves overview edits', async () => {
    const updatedProfile = { ...profile, preferred_name: 'Mia' }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(session))
      .mockResolvedValueOnce(jsonResponse(profile))
      .mockResolvedValueOnce(
        jsonResponse([
          profile,
          {
            ...profile,
            id: 2,
            full_name: 'Noah Park',
            relationships: [],
          },
        ]),
      )
      .mockResolvedValueOnce(jsonResponse(updatedProfile))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderApp('/people/1')

    expect(
      await screen.findByRole('heading', { name: 'Mia Chen', level: 1 }),
    ).toBeVisible()
    expect(screen.getByText('Known as Mimi')).toBeVisible()

    await user.click(screen.getByRole('tab', { name: 'Relationships' }))
    expect(screen.getByText('Ava Singh')).toBeVisible()
    expect(screen.getAllByText('Noah Park')).not.toHaveLength(0)

    await user.click(screen.getByRole('tab', { name: 'Groups' }))
    expect(screen.getByText('Friday Community')).toBeVisible()

    await user.click(screen.getByRole('tab', { name: 'Events' }))
    expect(await screen.findByText('Community Lunch')).toBeVisible()

    await user.click(screen.getByRole('tab', { name: 'Follow-ups' }))
    expect(screen.getByText('Connected with Friday Community.')).toBeVisible()

    await user.click(screen.getByRole('tab', { name: 'Overview' }))
    await user.click(screen.getByRole('button', { name: 'Edit overview' }))
    const preferredName = screen.getByLabelText('Preferred name')
    await user.clear(preferredName)
    await user.type(preferredName, 'Mia')
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByText('Known as Mia')).toBeVisible()
    expect(fetchMock).toHaveBeenCalledTimes(4)
    expect(fetchMock.mock.calls[3]?.[0]).toBe('/api/people/1/')
    expect(fetchMock.mock.calls[3]?.[1]).toMatchObject({ method: 'PATCH' })
  })
})

describe('Events', () => {
  const event = {
    id: 21,
    group: 11,
    group_name: 'Friday Community',
    title: 'Community Lunch',
    description: 'A fictional community lunch.',
    starts_at: '2026-07-25T02:00:00Z',
    ends_at: '2026-07-25T04:00:00Z',
    location: 'Main Hall',
    capacity: 40,
    signup_opens: true,
    signup_closes_at: '2026-07-25T01:00:00Z',
    registration_open: true,
    places_available: true,
    my_registration: null,
    registered_count: 12,
    waitlisted_count: 0,
    created_by: 'alex',
    created_at: '2026-07-01T00:00:00Z',
    updated_at: '2026-07-01T00:00:00Z',
  }

  it('lists events and supports duplicate and create workflows', async () => {
    const created = {
      ...event,
      id: 22,
      group: null,
      group_name: undefined,
      title: 'Welcome Dinner',
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(session))
      .mockResolvedValueOnce(jsonResponse([event]))
      .mockResolvedValueOnce(
        jsonResponse([{ id: 11, name: 'Friday Community' }]),
      )
      .mockResolvedValueOnce(
        jsonResponse([
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
            groups: [],
          },
        ]),
      )
      .mockResolvedValueOnce(
        jsonResponse([
          {
            id: 51,
            person: {
              id: 1,
              full_name: 'Mia Chen',
              preferred_name: 'Mimi',
            },
            status: 'registered',
            needs_transport: true,
            note: 'Pickup near station',
            registered_at: '2026-07-10T02:00:00Z',
            checked_in_at: null,
            checkin_method: null,
          },
        ]),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          id: 51,
          person: {
            id: 1,
            full_name: 'Mia Chen',
            preferred_name: 'Mimi',
          },
          status: 'registered',
          needs_transport: true,
          note: 'Pickup near station',
          registered_at: '2026-07-10T02:00:00Z',
          checked_in_at: '2026-07-25T02:01:00Z',
          checkin_method: 'manual',
        }),
      )
      .mockResolvedValueOnce(jsonResponse(created))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderApp('/events')

    expect(
      await screen.findByRole('heading', {
        name: 'Upcoming events',
        level: 1,
      }),
    ).toBeVisible()
    expect(await screen.findByText('Community Lunch')).toBeVisible()
    expect(screen.getByText('12 / 40 registered')).toBeVisible()

    await user.click(screen.getByRole('button', { name: 'Registration list' }))
    expect(await screen.findByText('Pickup near station')).toBeVisible()
    expect(screen.getByText(/Transport needed/)).toBeVisible()
    await user.type(screen.getByLabelText('Find attendee'), 'nobody')
    expect(screen.queryByText('Pickup near station')).not.toBeInTheDocument()
    await user.clear(screen.getByLabelText('Find attendee'))
    await user.click(screen.getByRole('button', { name: 'Check in' }))
    expect(await screen.findByText('Mia Chen is checked in.')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Add walk-in' }))
    expect(
      screen.getByRole('heading', { name: 'Quick-add walk-in', level: 4 }),
    ).toBeVisible()
    expect(screen.getByLabelText('Full name')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Add walk-in' }))
    await user.click(screen.getByRole('button', { name: 'Registration list' }))

    await user.click(screen.getByRole('button', { name: 'Duplicate' }))
    expect(screen.getByLabelText('Event title')).toHaveValue(
      'Community Lunch copy',
    )
    expect(screen.getByLabelText('Hosted by')).toHaveValue('11')
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    await user.click(screen.getByRole('button', { name: 'Edit' }))
    expect(
      screen.getByRole('heading', { name: 'Edit event', level: 2 }),
    ).toBeVisible()
    expect(screen.getByLabelText('Event title')).toHaveValue('Community Lunch')
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    await user.click(screen.getByRole('button', { name: 'Create event' }))
    fireEvent.change(screen.getByLabelText('Event title'), {
      target: { value: 'Welcome Dinner' },
    })
    fireEvent.change(screen.getByLabelText('Starts'), {
      target: { value: '2026-07-30T18:00' },
    })
    fireEvent.change(screen.getByLabelText('Ends'), {
      target: { value: '2026-07-30T20:00' },
    })
    await user.click(screen.getByRole('button', { name: 'Save event' }))

    expect(await screen.findByText('Welcome Dinner')).toBeVisible()
    expect(fetchMock.mock.calls[6]?.[0]).toBe('/api/events/')
    expect(fetchMock.mock.calls[6]?.[1]).toMatchObject({ method: 'POST' })
  })
})

describe('Follow-up queue', () => {
  const followUp = {
    id: 71,
    person: {
      id: 1,
      full_name: 'Mia Chen',
      preferred_name: 'Mimi',
      phone: '+61000000001',
      email: 'mia@example.test',
    },
    source: 'event_visit',
    engagement: 'possible',
    status: 'new',
    assigned_to: null,
    assigned_to_name: null,
    due_at: '2026-07-20',
    closed_at: null,
    outcome: null,
    created_at: '2026-07-17T01:00:00Z',
    updated_at: '2026-07-17T01:00:00Z',
  }

  it('shows the pipeline and moves a follow-up after an update', async () => {
    const updated = {
      ...followUp,
      status: 'connected',
      engagement: 'likely',
      assigned_to: 1,
      assigned_to_name: 'alex',
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(session))
      .mockResolvedValueOnce(jsonResponse([followUp]))
      .mockResolvedValueOnce(
        jsonResponse([{ id: 1, username: 'alex', name: 'Alex Chen' }]),
      )
      .mockResolvedValueOnce(
        jsonResponse([
          {
            id: 81,
            kind: 'call',
            occurred_at: '2026-07-17T02:00:00Z',
            summary: 'Fictional welcome call',
            visibility: 'staff',
            author: 'alex',
            created_at: '2026-07-17T02:00:00Z',
          },
        ]),
      )
      .mockResolvedValueOnce(jsonResponse(updated))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderApp('/follow-ups')

    expect(
      await screen.findByRole('heading', {
        name: 'Follow-up queue',
        level: 1,
      }),
    ).toBeVisible()
    expect(await screen.findByText('Mia Chen')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Update' }))
    expect(await screen.findByText('Fictional welcome call')).toBeVisible()
    await user.selectOptions(screen.getByLabelText('Stage'), 'connected')
    await user.selectOptions(screen.getByLabelText('Engagement'), 'likely')
    await user.selectOptions(screen.getByLabelText('Assigned to'), '1')
    await user.click(screen.getByRole('button', { name: 'Save update' }))

    expect(await screen.findByText('Likely')).toBeVisible()
    expect(fetchMock.mock.calls[4]?.[0]).toBe('/api/follow-ups/71/')
    expect(fetchMock.mock.calls[4]?.[1]).toMatchObject({ method: 'PATCH' })
  })
})
