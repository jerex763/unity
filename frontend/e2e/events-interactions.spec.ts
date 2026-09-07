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

const registration = {
  id: 51,
  person: {
    id: 31,
    full_name: 'Fictional Registered Visitor',
    preferred_name: null,
  },
  status: 'registered',
  note: '',
  registered_at: '2026-08-01T00:00:00Z',
  checked_in_at: null,
  checkin_method: null,
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
      await route.fulfill({ json: [registration] })
      return
    }
    if (path === '/api/events/21/registrations/51/check-in/') {
      const checkedIn = Boolean(
        (request.postDataJSON() as { checked_in: boolean }).checked_in,
      )
      await route.fulfill({
        json: {
          ...registration,
          checked_in_at: checkedIn ? '2026-08-15T01:00:00Z' : null,
          checkin_method: checkedIn ? 'manual' : null,
        },
      })
      return
    }
    if (path === '/api/events/21/check-in/people/') {
      await route.fulfill({
        json: [
          {
            id: 41,
            full_name: 'Duplicate Existing Person',
            preferred_name: 'First',
            membership_status: 'regular',
            current_registration_status: null,
            contact_hint: 'Phone · ending 0101',
          },
          {
            id: 42,
            full_name: 'Duplicate Existing Person',
            preferred_name: 'Second',
            membership_status: 'member',
            current_registration_status: 'waitlisted',
            contact_hint: 'Email · s***@e***.test',
          },
        ],
      })
      return
    }
    if (path === '/api/events/21/walk-ins/') {
      const body = request.postDataJSON() as {
        person?: number
        full_name?: string
      }
      await route.fulfill({
        status: 201,
        json: {
          ...registration,
          id: 52,
          person: {
            id: body.person ?? 32,
            full_name: body.person
              ? 'Duplicate Existing Person'
              : (body.full_name ?? 'Fictional Walk-in'),
            preferred_name: null,
          },
          status: body.person ? 'registered' : 'walk_in',
          checked_in_at: '2026-08-15T01:05:00Z',
          checkin_method: 'manual',
        },
      })
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
    name: 'Show registrations (12)',
  })
  await expect(registrationToggle).toHaveAttribute('aria-expanded', 'false')
  await expect(registrationToggle).toHaveAttribute(
    'aria-controls',
    'event-21-registrations',
  )
  await registrationToggle.click()
  await expect(page.locator('.registration-toggle').first()).toHaveAttribute(
    'aria-expanded',
    'true',
  )
  await expect(page.locator('#event-21-registrations')).toBeVisible()
  await expectNoHorizontalOverflow(page)

  if (testInfo.project.name.startsWith('mobile-')) {
    await page.getByRole('button', { name: 'Back to events' }).click()
    await expect(registrationToggle).toBeFocused()
  }

  const editButton = page.getByRole('button', { name: 'Edit' })
  await editButton.click()
  const eventDialog = page.getByRole('dialog', { name: 'Edit event' })
  const titleInput = page.getByLabel('Event title (required)')
  await expect(titleInput).toBeFocused()
  await expect(page.locator('.topbar')).toHaveAttribute('inert', '')
  await expect(titleInput).toHaveValue('Community Lunch')
  await expect(page.getByRole('heading', { name: 'Edit event' })).toBeVisible()
  await expectNoHorizontalOverflow(page)
  const eventClose = eventDialog.locator('.dialog-close')
  const eventSave = eventDialog.getByRole('button', { name: 'Save event' })
  await eventClose.focus()
  await page.keyboard.press('Shift+Tab')
  await expect(eventSave).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(eventClose).toBeFocused()
  await page.getByRole('button', { name: 'Save event' }).click()
  await expect(page.getByRole('heading', { name: 'Edit event' })).toBeHidden()
  await expect(editButton).toBeFocused()

  const duplicateButton = page.getByRole('button', { name: 'Duplicate' })
  await duplicateButton.click()
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
  await page.keyboard.press('Escape')
  await expect(
    page.getByRole('heading', { name: 'Duplicate event' }),
  ).toBeHidden()
  await expect(duplicateButton).toBeFocused()
  await duplicateButton.click()
  await expect(titleInput).toBeFocused()
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
  await expect(page.getByText('Escalated')).toBeVisible()
  await expect(page.getByText('Stale')).toBeVisible()
  await page.locator('.follow-up-card').first().click()
  await expect(
    page.getByRole('heading', {
      name: 'Fictional Attention Visitor',
      level: 2,
    }),
  ).toBeVisible()
  await expect(
    page.locator('.follow-up-editor').getByText('10/08/2026').first(),
  ).toBeVisible()
  await expect(
    page
      .locator('.follow-up-editor')
      .getByText(/Escalate and agree the next action/)
      .first(),
  ).toBeVisible()
  await expectNoHorizontalOverflow(page)

  const updateButton = page.getByRole('button', { name: 'Update' })
  await updateButton.click()
  const updateDialog = page.getByRole('dialog', {
    name: 'Update Fictional Attention Visitor',
  })
  await expect(updateDialog).toBeVisible()
  const updateHeading = updateDialog.getByRole('heading', {
    name: 'Update Fictional Attention Visitor',
    level: 2,
  })
  await expect(updateHeading).toBeFocused()
  await expect(page.locator('.topbar')).toHaveAttribute('inert', '')
  const updateClose = updateDialog.locator('.dialog-close')
  const updateSubmit = updateDialog.getByRole('button', {
    name: 'Save update',
  })
  await updateClose.focus()
  await page.keyboard.press('Shift+Tab')
  await expect(updateSubmit).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(updateClose).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(updateDialog).toBeHidden()
  await expect(updateButton).toBeFocused()
  await updateButton.click()
  await expect(updateHeading).toBeFocused()
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
  await expect(page.getByText('Follow-up updated.')).toBeVisible()
  await expect(
    page.getByRole('heading', {
      name: 'Fictional Attention Visitor',
      level: 2,
    }),
  ).toBeFocused()
})

test('event-day check-in is separate, searchable, and supports walk-ins', async ({
  page,
}) => {
  const walkInBodies: Record<string, unknown>[] = []
  page.on('request', (request) => {
    if (new URL(request.url()).pathname === '/api/events/21/walk-ins/') {
      walkInBodies.push(request.postDataJSON() as Record<string, unknown>)
    }
  })
  await page.goto('/events/21/check-in')
  await expect(
    page.getByRole('heading', { name: 'Community Lunch' }),
  ).toBeVisible()
  await expect(
    page.getByText('Fictional Registered Visitor', { exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'To check in' }),
  ).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('button', { name: 'All' })).toBeVisible()
  await page.getByLabel('Find attendee').fill('nobody')
  await expect(page.getByRole('button', { name: 'All' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.getByText('No attendees match this view.')).toBeVisible()
  await page.getByLabel('Find attendee').fill('')
  await page.getByRole('button', { name: 'To check in' }).click()
  const registeredVisitor = page
    .getByRole('region', { name: 'Attendees' })
    .locator('article')
    .filter({ hasText: 'Fictional Registered Visitor' })
  await expect(registeredVisitor).toContainText('Registered · Not checked in')
  await registeredVisitor.getByRole('button', { name: 'Check in' }).click()
  await expect(
    page.getByText('Fictional Registered Visitor is checked in.'),
  ).toBeVisible()
  await expect(registeredVisitor).toHaveCount(0)
  await page.getByLabel('Find attendee').fill('Fictional Registered Visitor')
  await expect(page.getByRole('button', { name: 'All' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(
    page
      .getByRole('region', { name: 'Attendees' })
      .locator('article')
      .filter({ hasText: 'Fictional Registered Visitor' }),
  ).toContainText('Registered · Checked in')
  await page.getByLabel('Find attendee').fill('')
  await page.getByRole('button', { name: 'Checked in' }).click()
  await expect(
    page.getByText('Fictional Registered Visitor', { exact: true }),
  ).toBeVisible()

  const addWalkInButton = page.getByRole('button', { name: 'Add walk-in' })
  await addWalkInButton.click()
  const walkInDialog = page.getByRole('dialog', { name: 'Add walk-in' })
  const existingSearch = page.getByLabel('Find existing person')
  await expect(existingSearch).toBeFocused()
  await expect(
    page.getByRole('radio', { name: /^Existing person/ }),
  ).toBeChecked()
  await expect(
    page.getByRole('radio', { name: /^New visitor/ }),
  ).not.toBeChecked()
  await expect(page.locator('.topbar')).toHaveAttribute('inert', '')
  const walkInClose = walkInDialog.locator('.dialog-close')
  const walkInSubmit = walkInDialog.getByRole('button', {
    name: 'Check in selected person',
  })
  await walkInClose.focus()
  await page.keyboard.press('Shift+Tab')
  await expect(walkInSubmit).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(walkInClose).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(walkInDialog).toBeHidden()
  await expect(addWalkInButton).toBeFocused()
  await addWalkInButton.click()
  await expect(existingSearch).toBeFocused()
  await existingSearch.fill('Duplicate')
  const duplicateChoices = walkInDialog.getByRole('radio', {
    name: /Duplicate Existing Person/,
  })
  await expect(duplicateChoices).toHaveCount(2)
  await duplicateChoices.first().check()
  await page.getByRole('radio', { name: /^New visitor/ }).check()
  await page.getByRole('radio', { name: /^Existing person/ }).check()
  await expect(duplicateChoices).toHaveCount(2)
  await walkInSubmit.click()
  await expect(
    walkInDialog.getByText('Search for and select an existing person.'),
  ).toBeVisible()
  expect(walkInBodies).toHaveLength(0)
  await duplicateChoices.nth(1).check()
  await walkInSubmit.click()
  await expect(
    page.getByText('Duplicate Existing Person was checked in.'),
  ).toBeVisible()
  await expect.poll(() => walkInBodies[0]).toEqual({ person: 42, note: '' })

  await addWalkInButton.click()
  await page.getByRole('radio', { name: /^New visitor/ }).check()
  const walkInName = page.getByLabel('Full name (required)')
  await walkInName.fill('Fictional Walk-in')
  const walkInPhone = page.getByRole('textbox', {
    name: 'Phone',
    exact: true,
  })
  const walkInPreference = page.getByLabel('Preferred contact')
  await walkInPhone.fill('+61 400 000 099')
  await walkInPreference.selectOption('phone')
  await walkInPhone.fill('')
  await expect(walkInPreference).toHaveValue('')
  await walkInPhone.fill('+61 400 000 099')
  await expect(page.getByLabel('This phone number uses WhatsApp')).toBeEnabled()
  await page.getByLabel('This phone number uses WhatsApp').check()
  await walkInPreference.selectOption('whatsapp')
  await page.getByLabel('This phone number uses WhatsApp').uncheck()
  await expect(walkInPreference).toHaveValue('')
  await page.getByRole('button', { name: 'Add visitor and check in' }).click()
  await expect(
    page.getByText('Fictional Walk-in was added and checked in.'),
  ).toBeVisible()
  expect(walkInBodies[1]).toMatchObject({
    full_name: 'Fictional Walk-in',
    phone: '+61 400 000 099',
  })
  await expectNoHorizontalOverflow(page)
})

test('shell contains SVG navigation and handles missing names without username leakage', async ({
  page,
}) => {
  await page.route('**/api/auth/session/', (route) =>
    route.fulfill({
      json: {
        ...session,
        user: {
          ...session.user,
          first_name: '',
          username:
            'technical-account-name-that-must-not-appear-in-the-greeting-at-any-width',
        },
        membership: {
          ...session.membership,
          church_name:
            'A very long fictional church name used to verify shell wrapping behaviour',
        },
      },
    }),
  )
  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: 'Welcome back', exact: true }),
  ).toBeVisible()
  await expect(page.getByText(/technical-account-name/)).toHaveCount(0)
  await expect(page.locator('.bottom-nav svg')).toHaveCount(4)
  const isMobile = (page.viewportSize()?.width ?? 0) < 768
  const visibleContext = page.locator(
    isMobile ? '.mobile-account-context' : '.account-context',
  )
  await expect(visibleContext).toContainText(
    'A very long fictional church name used to verify shell wrapping behaviour',
  )
  await expect(visibleContext).toContainText('leader')
  if (isMobile) {
    const role = page.locator('.mobile-account-role')
    await expect(role).toBeVisible()
    const [roleBox, topbarBox] = await Promise.all([
      role.boundingBox(),
      page.locator('.topbar').boundingBox(),
    ])
    expect(roleBox).not.toBeNull()
    expect(topbarBox).not.toBeNull()
    expect(roleBox!.x + roleBox!.width).toBeLessThanOrEqual(
      topbarBox!.x + topbarBox!.width,
    )
  }
  await expectNoHorizontalOverflow(page)
})
