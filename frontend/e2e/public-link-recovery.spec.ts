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
  public_registration_enabled: true,
  registered_count: 12,
  waitlisted_count: 0,
  created_by: 'alex',
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
}

const publicUrl = 'https://example.invalid/register/fictional-recovery-token'
async function fixtures(page: Page, legacy = false) {
  const requests: string[] = []
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (!path.startsWith('/api/')) {
      await route.continue()
      return
    }
    let body: unknown = []
    let status = 200
    if (path.endsWith('/auth/session/')) body = session
    else if (path.endsWith('/public-link/')) {
      requests.push(route.request().method())
      status = legacy ? 409 : 200
      body = legacy ? { code: 'legacy_link' } : { url: publicUrl }
    } else if (path === '/api/events/') body = [churchEvent]
    else if (path === '/api/people/filter-options/')
      body = { groups: [], universities: [], membership_statuses: [] }
    await route.fulfill({ status, json: body })
  })
  return requests
}

test('public link survives reload without rotation and has manual copy fallback', async ({
  page,
}) => {
  const requests = await fixtures(page)
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: () => Promise.reject(new Error('Clipboard denied')) },
    })
  })
  await page.goto('/events')
  await page.getByRole('button', { name: 'Show link', exact: true }).click()
  await expect(page.getByLabel('Public registration URL')).toHaveValue(
    publicUrl,
  )
  await page.reload()
  await expect(
    page.getByRole('button', { name: 'Copy link', exact: true }),
  ).toBeVisible()
  await expect(page.getByLabel('Public registration URL')).toHaveCount(0)
  await page.getByRole('button', { name: 'Copy link', exact: true }).click()
  const input = page.getByLabel('Public registration URL')
  await expect(input).toHaveValue(publicUrl)
  await expect(page.getByRole('alert')).toContainText(
    'Select and copy the link manually',
  )
  await expect(input).toBeFocused()
  await expectResponseClearOfNavigation(page)
  await input.focus()
  expect(
    await input.evaluate((element: HTMLInputElement) => element.selectionEnd),
  ).toBe(publicUrl.length)
  expect(requests).toEqual(['GET', 'GET'])
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true)
  expect(
    await page.evaluate(
      () => JSON.stringify(localStorage) + JSON.stringify(sessionStorage),
    ),
  ).not.toContain('fictional-recovery-token')
})

test('legacy public link explains recovery limitation without replacing it', async ({
  page,
}) => {
  const requests = await fixtures(page, true)
  await page.goto('/events')
  await page.getByRole('button', { name: 'Show link', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText(
    'This older link cannot be displayed again',
  )
  await expect(
    page.getByRole('button', { name: 'Replace public link…', exact: true }),
  ).toBeEnabled()
  await expect(page.getByLabel('Public registration URL')).toHaveCount(0)
  await expectResponseClearOfNavigation(page)
  expect(requests).toEqual(['GET'])
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true)
})

async function expectResponseClearOfNavigation(page: Page) {
  const result = page.locator('.public-link-result')
  await expect(result).toBeInViewport({ ratio: 1 })
  const bounds = await result.evaluate((element) => {
    const rect = element.getBoundingClientRect()
    const topbar = document.querySelector('.topbar')?.getBoundingClientRect()
    const nav = document.querySelector('.bottom-nav')?.getBoundingClientRect()
    return {
      top: rect.top,
      bottom: rect.bottom,
      minimum: topbar?.bottom ?? 0,
      maximum: nav && nav.height > 0 ? nav.top : innerHeight,
    }
  })
  expect(bounds.top).toBeGreaterThanOrEqual(bounds.minimum)
  expect(bounds.bottom).toBeLessThanOrEqual(bounds.maximum)
}
