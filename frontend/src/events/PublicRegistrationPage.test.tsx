import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'

import { PublicRegistrationPage } from './PublicRegistrationPage'

const publicEvent = {
  title: 'Fictional Community Lunch',
  description: 'A fictional public event.',
  starts_at: '2099-08-20T08:00:00Z',
  ends_at: '2099-08-20T10:00:00Z',
  location: 'Fictional Hall',
  registration_open: true,
  privacy_notice: {
    version: '2026-08-contact-methods-v1',
    text: 'A fictional privacy notice for test data.',
  },
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

it('clearly labels minimal required and optional visitor fields', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(publicEvent)))

  render(
    <MemoryRouter initialEntries={['/register/fictional-token']}>
      <Routes>
        <Route path="/register/:token" element={<PublicRegistrationPage />} />
      </Routes>
    </MemoryRouter>,
  )

  expect(
    await screen.findByRole('heading', { name: 'Fictional Community Lunch' }),
  ).toBeVisible()
  expect(screen.getByLabelText(/Full name.*required/)).toBeRequired()
  expect(screen.getByLabelText('Email (optional)')).not.toBeRequired()
  expect(screen.getByLabelText('Phone (optional)')).not.toBeRequired()
  expect(screen.getByLabelText('WeChat ID (optional)')).not.toBeRequired()
  expect(
    screen.getByLabelText('This phone number uses WhatsApp'),
  ).toBeDisabled()
  expect(screen.queryByText(/transport/i)).not.toBeInTheDocument()
  expect(
    screen.getByText('A fictional privacy notice for test data.'),
  ).toBeVisible()
  expect(screen.getByText('Version 2026-08-contact-methods-v1')).toBeVisible()
  expect(screen.getByLabelText(/explicitly consent/)).toBeRequired()
  expect(screen.queryByText(/roster|directory/i)).not.toBeInTheDocument()
})

it('submits consent version and confirms without exposing a roster', async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(jsonResponse(publicEvent))
    .mockResolvedValueOnce(
      jsonResponse(
        {
          accepted: true,
          event_title: publicEvent.title,
          cancellation_url:
            'http://test.local/registration/cancel/fictional-cancel-token',
        },
        201,
      ),
    )
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()

  render(
    <MemoryRouter initialEntries={['/register/fictional-token']}>
      <Routes>
        <Route path="/register/:token" element={<PublicRegistrationPage />} />
      </Routes>
    </MemoryRouter>,
  )
  await user.type(
    await screen.findByLabelText(/Full name/),
    'Fictional Visitor',
  )
  await user.type(
    screen.getByLabelText('Email (optional)'),
    'visitor@example.test',
  )
  await user.click(screen.getByLabelText(/explicitly consent/))
  await user.click(screen.getByRole('button', { name: 'Register' }))

  expect(
    await screen.findByText('Your registration request has been accepted.'),
  ).toBeVisible()
  expect(
    screen.getByRole('link', { name: 'Cancel this registration' }),
  ).toHaveAttribute('href', '/registration/cancel/fictional-cancel-token')
  expect(screen.queryByText(/other attendees/i)).not.toBeInTheDocument()
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toMatchObject({
    full_name: 'Fictional Visitor',
    has_whatsapp: false,
    wechat_id: '',
    consent: true,
    notice_version: '2026-08-contact-methods-v1',
  })
})

it('clears a preferred channel when its contact method becomes unavailable', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(publicEvent)))
  const user = userEvent.setup()

  render(
    <MemoryRouter initialEntries={['/register/fictional-token']}>
      <Routes>
        <Route path="/register/:token" element={<PublicRegistrationPage />} />
      </Routes>
    </MemoryRouter>,
  )

  await screen.findByRole('heading', { name: 'Fictional Community Lunch' })
  const preference = screen.getByLabelText('Preferred contact (optional)')
  const email = screen.getByLabelText('Email (optional)')
  const phone = screen.getByLabelText('Phone (optional)')
  const wechat = screen.getByLabelText('WeChat ID (optional)')
  const whatsapp = screen.getByLabelText('This phone number uses WhatsApp')

  await user.type(email, 'visitor@example.test')
  await user.selectOptions(preference, 'email')
  await user.clear(email)
  expect(preference).toHaveValue('')

  await user.type(wechat, 'fictional_wechat')
  await user.selectOptions(preference, 'wechat')
  await user.clear(wechat)
  expect(preference).toHaveValue('')

  await user.type(phone, '+61 400 000 099')
  await user.selectOptions(preference, 'phone')
  await user.clear(phone)
  expect(preference).toHaveValue('')

  await user.type(phone, '+61 400 000 099')
  await user.click(whatsapp)
  await user.selectOptions(preference, 'whatsapp')
  await user.click(whatsapp)
  expect(preference).toHaveValue('')
})

it('offers retry for a temporary event load failure without calling the link invalid', async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(jsonResponse({}, 503))
    .mockResolvedValueOnce(jsonResponse(publicEvent))
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()

  render(
    <MemoryRouter initialEntries={['/register/fictional-token']}>
      <Routes>
        <Route path="/register/:token" element={<PublicRegistrationPage />} />
      </Routes>
    </MemoryRouter>,
  )

  expect(
    await screen.findByRole('heading', {
      name: 'Registration is temporarily unavailable',
    }),
  ).toBeVisible()
  expect(screen.queryByText(/expired|withdrawn/i)).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Try again' }))

  expect(
    await screen.findByRole('heading', { name: 'Fictional Community Lunch' }),
  ).toBeVisible()
  expect(fetchMock).toHaveBeenCalledTimes(2)
})

it('keeps an invalid or expired event link in the inaccessible state', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, 404)))

  render(
    <MemoryRouter initialEntries={['/register/fictional-token']}>
      <Routes>
        <Route path="/register/:token" element={<PublicRegistrationPage />} />
      </Routes>
    </MemoryRouter>,
  )

  expect(
    await screen.findByRole('heading', { name: 'Registration unavailable' }),
  ).toBeVisible()
  expect(
    screen.getByText(
      'This link may have expired or been withdrawn by the organiser.',
    ),
  ).toBeVisible()
  expect(
    screen.queryByRole('button', { name: 'Try again' }),
  ).not.toBeInTheDocument()
})
