import { expect, test, type Locator, type Page } from '@playwright/test'

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
    role: 'leader',
    person_id: null,
  },
}

const followUps = Array.from({ length: 12 }, (_, index) => ({
  id: 71 + index,
  person: {
    id: 31 + index,
    full_name: `Fictional Visitor ${index + 1}`,
    preferred_name: null,
    phone: `+61000000${String(index).padStart(3, '0')}`,
    email: null,
    wechat_id: null,
  },
  source: 'event_visit',
  engagement: 'possible',
  status: 'in_progress',
  assigned_to: 1,
  assigned_to_name: 'Alex Chen',
  due_at: `2099-08-${String(index + 1).padStart(2, '0')}`,
  closed_at: null,
  outcome: null,
  created_at: '2099-07-01T00:00:00Z',
  updated_at: '2099-07-01T00:00:00Z',
  attention: {
    overdue: false,
    due_today: false,
    stale: false,
    unassigned_too_long: false,
    no_action: false,
    escalated: false,
    postponement_count: 0,
    next_action: `Contact Fictional Visitor ${index + 1}`,
  },
}))

const churchEvent = {
  id: 21,
  group: 11,
  group_name: 'Friday Community',
  title: 'Fictional Community Lunch',
  description: 'A fictional community lunch.',
  starts_at: '2099-07-30T08:00:00Z',
  ends_at: '2099-07-30T10:00:00Z',
  location: 'Main Hall',
  capacity: 40,
  signup_opens: true,
  signup_closes_at: '2099-07-29T08:00:00Z',
  registration_open: true,
  places_available: true,
  my_registration: null,
  registered_count: 1,
  waitlisted_count: 0,
  public_registration_enabled: false,
  created_by: 'alex',
  created_at: '2099-07-01T00:00:00Z',
  updated_at: '2099-07-01T00:00:00Z',
}

const registration = {
  id: 51,
  person: {
    id: 31,
    full_name: 'Fictional Registered Visitor',
    preferred_name: null,
  },
  status: 'registered',
  note: '',
  registered_at: '2099-07-01T00:00:00Z',
  checked_in_at: null,
  checkin_method: null,
}

async function mockApi(page: Page, options?: { failRosterOnce?: boolean }) {
  let rosterRequests = 0
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname

    if (!path.startsWith('/api/')) {
      await route.continue()
      return
    }

    if (path === '/api/auth/session/') {
      await route.fulfill({ json: session })
      return
    }
    if (path === '/api/follow-ups/' && request.method() === 'GET') {
      await route.fulfill({ json: followUps })
      return
    }
    if (path === '/api/follow-ups/mine/') {
      await route.fulfill({ json: followUps.slice(0, 2) })
      return
    }
    if (path === '/api/follow-ups/workers/') {
      await route.fulfill({ json: [] })
      return
    }
    if (/\/api\/follow-ups\/\d+\/interactions\/$/.test(path)) {
      await route.fulfill({ json: [] })
      return
    }
    if (path === '/api/events/' && request.method() === 'GET') {
      await route.fulfill({ json: [churchEvent] })
      return
    }
    if (path === '/api/events/groups/') {
      await route.fulfill({ json: [{ id: 11, name: 'Friday Community' }] })
      return
    }
    if (path === '/api/people/') {
      await route.fulfill({ json: [] })
      return
    }
    if (path === '/api/events/21/registrations/') {
      rosterRequests += 1
      await new Promise((resolve) => setTimeout(resolve, 600))
      if (options?.failRosterOnce && rosterRequests === 1) {
        await route.fulfill({
          status: 503,
          json: { detail: 'Fictional temporary failure' },
        })
      } else {
        await route.fulfill({ json: [registration] })
      }
      return
    }
    await route.fulfill({ status: 404, json: { detail: 'Not mocked' } })
  })
}

async function expectInViewport(locator: Locator) {
  const box = await locator.boundingBox()
  expect(box).not.toBeNull()
  const viewport = locator.page().viewportSize()
  expect(viewport).not.toBeNull()
  expect(box!.y).toBeGreaterThanOrEqual(0)
  expect(box!.y).toBeLessThan(viewport!.height)
  expect(box!.x).toBeGreaterThanOrEqual(0)
  expect(box!.x).toBeLessThan(viewport!.width)
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('follow-up selection is addressable and phone Back restores the queue draft and position', async ({
  page,
}, testInfo) => {
  await page.goto('/follow-ups')
  const firstDetail = page.getByRole('heading', {
    name: 'Fictional Visitor 1',
    level: 2,
  })

  if (testInfo.project.name.startsWith('mobile-')) {
    await expect(firstDetail).toBeHidden()
    await expect(page).toHaveURL(/\/follow-ups$/)
    await page.getByRole('button', { name: 'My follow-ups' }).click()
    await page.getByRole('button', { name: /Fictional Visitor 10/ }).click()
    await expect(page).toHaveURL(/\/follow-ups\?task=80$/)
    const detail = page.getByRole('heading', {
      name: 'Fictional Visitor 10',
      level: 2,
    })
    await expect(detail).toBeVisible()
    await expectInViewport(detail)
    const back = page.getByRole('button', { name: 'Back to queue' })
    await expectInViewport(back)
    const topbarBox = await page.locator('.topbar').boundingBox()
    const backBox = await back.boundingBox()
    expect(backBox!.y).toBeGreaterThanOrEqual(topbarBox!.y + topbarBox!.height)
    await page.getByLabel('Summary').fill('A preserved fictional draft')

    await page.goBack()
    await expect(page).toHaveURL(/\/follow-ups$/)
    await expect(
      page.getByRole('button', { name: 'My follow-ups' }),
    ).toHaveAttribute('aria-pressed', 'true')
    await expect
      .poll(() => page.evaluate(() => window.scrollY))
      .toBeGreaterThan(0)

    await page.getByRole('button', { name: /Fictional Visitor 10/ }).click()
    await expect(page.getByLabel('Summary')).toHaveValue(
      'A preserved fictional draft',
    )
  } else {
    await expect(firstDetail).toBeVisible()
    await page.getByRole('button', { name: /Fictional Visitor 10/ }).click()
    await expect(page).toHaveURL(/\/follow-ups\?task=80$/)
    await expect(
      page.getByRole('heading', {
        name: 'Fictional Visitor 10',
        level: 2,
      }),
    ).toBeVisible()
    await expect(page.locator('.follow-up-board')).toBeVisible()
  }
})

test('Dashboard opens the exact task and invalid task IDs never select another person', async ({
  page,
}) => {
  await page.goto('/')
  await page
    .getByRole('link', { name: 'Open Fictional Visitor 2 follow-up' })
    .click()
  await expect(page).toHaveURL(/\/follow-ups\?task=72$/)
  await expect(
    page.getByRole('heading', { name: 'Fictional Visitor 2', level: 2 }),
  ).toBeVisible()

  await page.goto('/follow-ups?task=999')
  await expect(
    page.getByRole('heading', { name: 'Follow-up unavailable' }),
  ).toBeVisible()
  await expect(
    page.getByRole('heading', { name: 'Fictional Visitor 1', level: 2 }),
  ).toBeHidden()
})

test('registration roster has a focused phone view and recoverable loading failure', async ({
  page,
}, testInfo) => {
  await page.unroute('**/api/**')
  await mockApi(page, { failRosterOnce: true })
  await page.goto('/events')

  await page.getByRole('button', { name: 'Show registrations (1)' }).click()
  const rosterTitle = page.getByRole('heading', {
    name: 'Registrations — Fictional Community Lunch',
  })
  await expect(rosterTitle).toBeVisible()
  await expect(page.getByText('Loading registrations…')).toBeVisible()
  await expectInViewport(rosterTitle)

  if (testInfo.project.name.startsWith('mobile-')) {
    const dialog = page.getByRole('dialog', {
      name: 'Registrations — Fictional Community Lunch',
    })
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText(/Main Hall/)).toBeVisible()
    await expect(rosterTitle).toBeFocused()
    await expect(page.locator('.topbar')).toHaveAttribute('inert', '')
  } else {
    await expect(page.getByRole('dialog')).toHaveCount(0)
    const roster = page.getByLabel('Registrations', { exact: true })
    await expect(roster).toContainText(
      'Registrations — Fictional Community Lunch',
    )
  }

  await expect(
    page.getByText('We could not load the registration list.'),
  ).toBeVisible()
  await expect(
    page.getByText('The event and its registrations are unchanged.'),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByText('Loading registrations…')).toBeVisible()
  await expect(page.getByText('Fictional Registered Visitor')).toBeVisible()

  if (testInfo.project.name.startsWith('mobile-')) {
    await page.getByRole('button', { name: 'Back to events' }).click()
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(
      page.getByRole('button', { name: 'Show registrations (1)' }),
    ).toBeFocused()
  }
})
