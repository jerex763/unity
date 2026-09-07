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
  email: 'fictional.mia.international.student.long-address@example.test',
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

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('contact disclosure preserves complete readable values', async ({
  page,
}) => {
  await page.goto('/people')
  const row = page.locator('.person-row').first()
  const disclosure = row.locator('details')
  await expect(disclosure).not.toHaveAttribute('open')
  await expect(
    row.getByRole('link', { name: 'Open WhatsApp for Mimi' }),
  ).toBeHidden()
  await disclosure.locator('summary').click()
  await expect(
    row.getByRole('link', { name: 'Open WhatsApp for Mimi' }),
  ).toBeVisible()
  async function fullValues() {
    await expect
      .poll(() =>
        page
          .locator(
            'details[open] textarea.contact-value-copy, .profile-contact-actions textarea.contact-value-copy',
          )
          .evaluateAll(
            (elements) =>
              elements.length > 0 &&
              elements.every(
                (el) =>
                  el.clientWidth > 0 && el.scrollHeight <= el.clientHeight + 1,
              ),
          ),
      )
      .toBe(true)
    await expect
      .poll(() =>
        page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      )
      .toBe(true)
  }
  await fullValues()
  await row.locator('.person-card-link').click()
  await expect(page.locator('.profile-hero')).toBeVisible()
  await fullValues()
})

test('profile return restores search and focus without persisting search', async ({
  page,
}) => {
  await page.goto('/people')
  await page.getByRole('searchbox').fill('Mimi')
  await expect(page.locator('.person-row')).toHaveCount(1)
  await page.locator('.person-card-link').click()
  await expect(page.locator('.profile-hero')).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('searchbox')).toHaveValue('Mimi')
  await expect(page.locator('#directory-person-1')).toBeFocused()
  await expect(page).toHaveURL(/\/people$/)
  const stores = await page.evaluate(() => [
    JSON.stringify(localStorage),
    JSON.stringify(sessionStorage),
  ])
  expect(stores.join(' ')).not.toContain('Mimi')
})

test('returning restores the selected row in a longer directory', async ({
  page,
}) => {
  await page.route('**/api/people/', (route) =>
    route.fulfill({
      json: [
        ...Array.from({ length: 15 }, (_, index) => ({
          ...person,
          id: index + 100,
          full_name: `Fictional visitor ${index + 1}`,
        })),
        person,
      ],
    }),
  )
  await page.goto('/people')
  const selected = page.locator('#directory-person-1')
  await selected.scrollIntoViewIfNeeded()
  const initialScroll = await page.evaluate(() => scrollY)
  expect(initialScroll).toBeGreaterThan(100)
  await selected.click()
  await expect(page.locator('.profile-identity h1')).toBeInViewport()
  await page.getByRole('link', { name: /Back to directory/ }).click()
  await expect(selected).toBeFocused()
  await expect(selected).toBeInViewport()
  await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(100)
})
