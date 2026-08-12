import { expect, test, type Page } from '@playwright/test'

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

const churchEvent = {
  id: 21,
  group: 11,
  group_name: 'Friday Community',
  title: 'Community Lunch',
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
  registered_count: 12,
  waitlisted_count: 0,
  created_by: 'alex',
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
}

const attentionFollowUp = {
  id: 71,
  person: {
    id: 31,
    full_name: 'Fictional Attention Visitor',
    preferred_name: null,
    phone: '+61000000000',
    email: null,
    wechat_id: null,
  },
  source: 'event_visit',
  engagement: 'possible',
  status: 'in_progress',
  assigned_to: 1,
  assigned_to_name: 'alex',
  due_at: '2026-08-10',
  closed_at: null,
  outcome: null,
  created_at: '2026-08-01T00:00:00Z',
  updated_at: '2026-08-01T00:00:00Z',
  attention: {
    overdue: true,
    due_today: false,
    stale: true,
    unassigned_too_long: false,
    no_action: false,
    escalated: true,
    postponement_count: 2,
    next_action: 'Escalate and agree the next action',
  },
}

async function mockApi(page: Page) {
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname

    if (!path.startsWith('/api/')) {
      await route.continue()
      return
    }

    if (path === '/api/auth/session/') {
      await route.fulfill({ json: session })
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
    if (path === '/api/follow-ups/workers/') {
      await route.fulfill({
        json: [{ id: 1, username: 'alex', name: 'Alex Chen' }],
      })
      return
    }
    if (path === '/api/follow-ups/71/interactions/') {
      await route.fulfill({ json: [] })
      return
    }
    if (path === '/api/follow-ups/71/' && request.method() === 'PATCH') {
      await route.fulfill({ json: attentionFollowUp })
      return
    }
    if (path === '/api/follow-ups/' && request.method() === 'GET') {
      await route.fulfill({ json: [attentionFollowUp] })
      return
    }
    if (path === '/api/events/21/registrations/') {
      await route.fulfill({ json: [] })
      return
    }
    if (path === '/api/events/21/' && request.method() === 'PATCH') {
      await route.fulfill({ json: churchEvent })
      return
    }
    if (path === '/api/events/' && request.method() === 'POST') {
      const body = request.postDataJSON() as Record<string, unknown>
      await route.fulfill({
        json: {
          ...churchEvent,
          ...body,
          id: 22,
          group_name: 'Friday Community',
        },
      })
      return
    }
    if (path === '/api/events/' && request.method() === 'GET') {
      await route.fulfill({ json: [churchEvent] })
      return
    }
    await route.fulfill({ status: 404, json: { detail: 'Not mocked' } })
  })
}

async function expectNoHorizontalOverflow(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true)
}

test.beforeEach(async ({ page }, testInfo) => {
  await page.emulateMedia({
    reducedMotion: testInfo.project.name.includes('reduced-motion')
      ? 'reduce'
      : 'no-preference',
  })
  await page.addInitScript(() => {
    const scrollCalls: ScrollIntoViewOptions[] = []
    ;(
      window as Window & { __editorScrollCalls: ScrollIntoViewOptions[] }
    ).__editorScrollCalls = scrollCalls
    Element.prototype.scrollIntoView = function (options) {
      scrollCalls.push(options as ScrollIntoViewOptions)
    }
  })
  await mockApi(page)
})

test('event organizer interactions remain usable at the configured viewport', async ({
  page,
}, testInfo) => {
  const requests: Array<{ method: string; path: string }> = []
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (url.pathname.startsWith('/api/events/')) {
      requests.push({ method: request.method(), path: url.pathname })
    }
  })

  await page.goto('/events')
  await expect(
    page.getByRole('heading', { name: 'Upcoming events' }),
  ).toBeVisible()
  await expectNoHorizontalOverflow(page)

  const actions = page.locator('.event-actions').first()
  const actionButtons = actions.getByRole('button')
  await expect(actionButtons).toHaveCount(4)
  await expect(actions).toHaveCSS('flex-wrap', 'wrap')

  const boxes = await actionButtons.evaluateAll((buttons) =>
    buttons.map((button) => button.getBoundingClientRect().toJSON()),
  )
  expect(boxes.every((box) => box.height >= 44)).toBe(true)
  if (testInfo.project.name.startsWith('mobile-')) {
    expect(new Set(boxes.map((box) => Math.round(box.y))).size).toBeGreaterThan(
      1,
    )
  }

  const registrationToggle = page.getByRole('button', {
    name: 'Show registration list',
  })
  await expect(registrationToggle).toHaveAttribute('aria-expanded', 'false')
  await expect(registrationToggle).toHaveAttribute(
    'aria-controls',
    'event-21-registrations',
  )
  await registrationToggle.click()
  await expect(
    page.getByRole('button', { name: 'Hide registration list' }),
  ).toHaveAttribute('aria-expanded', 'true')
  await expect(page.locator('#event-21-registrations')).toBeVisible()
  await expectNoHorizontalOverflow(page)

  await page.getByRole('button', { name: 'Edit' }).click()
  const titleInput = page.getByLabel('Event title (required)')
  await expect(titleInput).toBeFocused()
  await expect(titleInput).toHaveValue('Community Lunch')
  await expect(page.getByRole('heading', { name: 'Edit event' })).toBeVisible()
  await expectNoHorizontalOverflow(page)
  await page.getByRole('button', { name: 'Save event' }).click()
  await expect(page.getByRole('heading', { name: 'Edit event' })).toBeHidden()

  await page.getByRole('button', { name: 'Duplicate' }).click()
  await expect(titleInput).toBeFocused()
  await expect(titleInput).toHaveValue('Community Lunch copy')
  await expect(
    page.getByText(
      'Review the copied details and dates before saving this new event.',
    ),
  ).toBeVisible()
  const scrollCalls = await page.evaluate(
    () =>
      (window as Window & { __editorScrollCalls: ScrollIntoViewOptions[] })
        .__editorScrollCalls,
  )
  const expectedBehavior = testInfo.project.name.includes('reduced-motion')
    ? 'auto'
    : 'smooth'
  expect(scrollCalls.at(-1)).toMatchObject({
    behavior: expectedBehavior,
    block: 'start',
  })
  await expectNoHorizontalOverflow(page)
  await page.getByRole('button', { name: 'Save event' }).click()

  await expect
    .poll(() =>
      requests.some(
        (request) =>
          request.method === 'PATCH' && request.path === '/api/events/21/',
      ),
    )
    .toBe(true)
  await expect
    .poll(() =>
      requests.some(
        (request) =>
          request.method === 'POST' && request.path === '/api/events/',
      ),
    )
    .toBe(true)
  await expectNoHorizontalOverflow(page)
})

test('follow-up attention and postponement stay usable at the configured viewport', async ({
  page,
}) => {
  let patchBody: Record<string, unknown> | undefined
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (
      url.pathname === '/api/follow-ups/71/' &&
      request.method() === 'PATCH'
    ) {
      patchBody = request.postDataJSON() as Record<string, unknown>
    }
  })

  await page.goto('/follow-ups')
  await expect(page.getByText('Fictional Attention Visitor')).toBeVisible()
  await expect(page.getByText('Escalated')).toBeVisible()
  await expect(page.getByText('Stale')).toBeVisible()
  await expect(
    page.getByText('Escalate and agree the next action'),
  ).toBeVisible()
  await expectNoHorizontalOverflow(page)

  await page.getByRole('button', { name: 'Update' }).click()
  await page.getByLabel('Due').fill('2026-08-14')
  await expect(
    page.getByRole('group', { name: 'Why is this moving later?' }),
  ).toBeVisible()
  await page
    .getByLabel('Operational reason')
    .selectOption('worker_availability')
  await expectNoHorizontalOverflow(page)
  await page.getByRole('button', { name: 'Save update' }).click()

  await expect
    .poll(() => patchBody?.postpone_reason)
    .toBe('worker_availability')
})
