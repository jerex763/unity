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

const person = {
  id: 1,
  full_name: 'Fictional Mia Chen',
  preferred_name: 'Mimi',
  membership_status: 'newcomer',
  gender: 'unspecified',
  date_of_birth: null,
  email: 'fictional.mia@example.test',
  phone: '+61 400 000 001',
  wechat_id: 'fictional_mimi_wechat',
  has_whatsapp: true,
  photo_url: null,
  home_country: null,
  suburb: 'Fictional Suburb',
  occupation: null,
  university: null,
  course: null,
  interests: [],
  invited_by: null,
  inviter: null,
  invitees: [],
  relationships: [],
  notes: '',
  groups: [],
  events_attended: [],
  follow_up_history: [],
}

async function mockApi(page: Page) {
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (!path.startsWith('/api/')) {
      await route.continue()
      return
    }
    if (path === '/api/auth/session/') {
      await route.fulfill({ json: session })
      return
    }
    if (path === '/api/people/') {
      await route.fulfill({ json: [person] })
      return
    }
    if (path === '/api/people/1/') {
      await route.fulfill({ json: person })
      return
    }
    if (path === '/api/follow-ups/') {
      await route.fulfill({
        json: [
          {
            id: 71,
            person,
            source: 'event_visit',
            engagement: 'possible',
            status: 'new',
            assigned_to: null,
            assigned_to_name: null,
            due_at: null,
            closed_at: null,
            outcome: null,
            created_at: '2026-08-13T00:00:00Z',
            updated_at: '2026-08-13T00:00:00Z',
          },
        ],
      })
      return
    }
    if (path === '/api/follow-ups/workers/') {
      await route.fulfill({ json: [] })
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

async function expectContactOrderAndTargets(page: Page) {
  const actions = page.getByRole('group', {
    name: 'Contact actions for Mimi',
  })
  await expect(actions).toBeVisible()
  await expect
    .poll(() =>
      actions
        .locator(':scope > [data-contact-channel]')
        .evaluateAll((elements) =>
          elements.map((element) =>
            element.getAttribute('data-contact-channel'),
          ),
        ),
    )
    .toEqual(['whatsapp', 'wechat', 'call', 'email'])
  await expect(
    actions.getByRole('link', { name: 'Open WhatsApp for Mimi' }),
  ).toHaveAttribute('href', 'https://wa.me/61400000001')
  const controls = actions.locator('a, button')
  const boxes = await controls.evaluateAll((elements) =>
    elements.map((element) => element.getBoundingClientRect().toJSON()),
  )
  expect(boxes.length).toBeGreaterThan(0)
  expect(boxes.every((box) => box.height >= 44)).toBe(true)
  await expectNoHorizontalOverflow(page)
}

test.beforeEach(async ({ context, page }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await mockApi(page)
})

test('contact handoffs remain ordered and usable across all surfaces at the configured viewport', async ({
  page,
}) => {
  await page.goto('/people')
  await expectContactOrderAndTargets(page)

  const openEmail = page.getByRole('link', {
    name: 'Open email app for Mimi',
  })
  const copyEmail = page.getByRole('button', {
    name: 'Copy email address for Mimi',
  })
  await expect(openEmail).toHaveAttribute(
    'href',
    'mailto:fictional.mia@example.test',
  )
  await expect(copyEmail).toBeVisible()
  await expect(
    page.getByRole('textbox', { name: 'Email address for Mimi' }),
  ).toHaveValue('fictional.mia@example.test')
  expect((await openEmail.boundingBox())?.height).toBeGreaterThanOrEqual(44)
  expect((await copyEmail.boundingBox())?.height).toBeGreaterThanOrEqual(44)
  await copyEmail.click()
  await expect(page.getByRole('status')).toHaveText('Copied.')
  await expectNoHorizontalOverflow(page)

  await page
    .getByRole('link', { name: 'View Fictional Mia Chen profile' })
    .click()
  await expect(
    page.getByRole('heading', { name: 'Fictional Mia Chen', level: 1 }),
  ).toBeVisible()
  await expectContactOrderAndTargets(page)
  const profileOpenEmail = page.getByRole('link', {
    name: 'Open email app for Mimi',
  })
  const profileCopyEmail = page.getByRole('button', {
    name: 'Copy email address for Mimi',
  })
  await expect(profileOpenEmail).toBeVisible()
  await expect(profileCopyEmail).toBeVisible()
  expect((await profileOpenEmail.boundingBox())?.height).toBeGreaterThanOrEqual(
    44,
  )
  expect((await profileCopyEmail.boundingBox())?.height).toBeGreaterThanOrEqual(
    44,
  )
  await expectNoHorizontalOverflow(page)

  await page.goto('/follow-ups')
  await expect(
    page.getByRole('heading', { name: 'Follow-up queue', level: 1 }),
  ).toBeVisible()
  await expectContactOrderAndTargets(page)
})

test('profile save returns to a visible updated summary at the configured viewport', async ({
  page,
}) => {
  await page.route('**/api/auth/session/', (route) =>
    route.fulfill({
      json: {
        ...session,
        membership: { ...session.membership, role: 'pastor' },
      },
    }),
  )

  await page.goto('/people/1')
  await page.getByRole('button', { name: 'Edit person' }).click()
  const fullNameInput = page.getByLabel('Full name')
  await expect(fullNameInput).toBeVisible()
  await expect
    .poll(async () => {
      const [inputBox, topbarBox] = await Promise.all([
        fullNameInput.boundingBox(),
        page.locator('.topbar').boundingBox(),
      ])
      return Boolean(
        inputBox && topbarBox && inputBox.y >= topbarBox.y + topbarBox.height,
      )
    })
    .toBe(true)
  await page.getByRole('button', { name: 'Save changes' }).click()

  const heading = page.getByRole('heading', {
    name: 'Fictional Mia Chen',
    level: 1,
  })
  const notice = page.getByRole('status')
  await expect(heading).toBeFocused()
  await expect(notice).toHaveText('Person updated.')

  const [headingBox, noticeBox, topbarBox] = await Promise.all([
    heading.boundingBox(),
    notice.boundingBox(),
    page.locator('.topbar').boundingBox(),
  ])
  expect(headingBox).not.toBeNull()
  expect(noticeBox).not.toBeNull()
  expect(topbarBox).not.toBeNull()
  expect(headingBox!.y).toBeGreaterThanOrEqual(topbarBox!.y + topbarBox!.height)
  expect(noticeBox!.y + noticeBox!.height).toBeLessThanOrEqual(
    page.viewportSize()!.height,
  )
  await expectNoHorizontalOverflow(page)
})
