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
  phone: '+61000000001',
  wechat_id: null,
  has_whatsapp: false,
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

test.beforeEach(async ({ context, page }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'])
  await mockApi(page)
})

test('email handoff and copy fallback remain usable at the configured viewport', async ({
  page,
}) => {
  await page.goto('/people')

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
  await expect(page.getByRole('status')).toHaveText('Email address copied.')
  await expectNoHorizontalOverflow(page)

  await page
    .getByRole('link', { name: 'View Fictional Mia Chen profile' })
    .click()
  await expect(
    page.getByRole('heading', { name: 'Fictional Mia Chen', level: 1 }),
  ).toBeVisible()
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
})
