import { expect, test } from '@playwright/test'

test('public registration is usable without login at mobile widths', async ({
  page,
}) => {
  await page.route('**/api/auth/session/', (route) =>
    route.fulfill({ status: 403, json: { detail: 'Signed out' } }),
  )
  await page.route('**/api/public/events/fictional-token/', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 201,
        json: {
          accepted: true,
          event_title: 'Fictional Community Lunch',
          cancellation_url:
            'http://127.0.0.1:4173/registration/cancel/fictional-cancel-token',
        },
      })
      return
    }
    await route.fulfill({
      json: {
        title: 'Fictional Community Lunch',
        description: 'A fictional event used only for acceptance testing.',
        starts_at: '2099-08-20T08:00:00Z',
        ends_at: '2099-08-20T10:00:00Z',
        location: 'Fictional Hall',
        registration_open: true,
        privacy_notice: {
          version: '2026-08-contact-methods-v1',
          text: 'A fictional privacy notice used only for acceptance testing.',
        },
      },
    })
  })

  await page.goto('/register/fictional-token')
  await expect(
    page.getByRole('heading', { name: 'Fictional Community Lunch' }),
  ).toBeVisible()
  await page.getByLabel(/Full name/).fill('Fictional Mobile Visitor')
  await page.getByLabel('Phone (optional)').fill('+61 400 000 099')
  await page.getByLabel('This phone number uses WhatsApp').check()
  await page.getByLabel(/explicitly consent/).check()
  await page.getByRole('button', { name: 'Register' }).click()

  await expect(
    page.getByText('Your registration request has been accepted.'),
  ).toBeVisible()
  await expect(
    page.getByRole('link', { name: 'Cancel this registration' }),
  ).toBeVisible()
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true)
})
