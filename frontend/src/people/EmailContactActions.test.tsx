import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import '../i18n'
import { emailAppHref } from './contactLinks'
import { EmailContactActions } from './EmailContactActions'

const originalClipboard = Object.getOwnPropertyDescriptor(
  navigator,
  'clipboard',
)

afterEach(() => {
  if (originalClipboard) {
    Object.defineProperty(navigator, 'clipboard', originalClipboard)
  } else {
    Reflect.deleteProperty(navigator, 'clipboard')
  }
})

function setClipboard(value: Pick<Clipboard, 'writeText'> | undefined) {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value,
  })
}

describe('EmailContactActions', () => {
  it.each([
    ['mia?tag@example.test', 'mailto:mia%3Ftag@example.test'],
    ['mia#tag@example.test', 'mailto:mia%23tag@example.test'],
    ['mia%tag@example.test', 'mailto:mia%25tag@example.test'],
  ])(
    'encodes URI delimiters in %s without creating mailto query or fragment data',
    (email, expectedHref) => {
      const href = emailAppHref(email)
      const parsed = new URL(href)

      expect(href).toBe(expectedHref)
      expect(parsed.search).toBe('')
      expect(parsed.hash).toBe('')
      expect(decodeURIComponent(parsed.pathname)).toBe(email)
    },
  )

  it('opens the email app and copies the address using the preferred name', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    setClipboard({ writeText })
    const email = 'mia?subject#progress%@example.test'

    render(
      <EmailContactActions
        email={email}
        fullName="Mia Chen"
        preferredName="Mimi"
      />,
    )

    expect(
      screen.getByRole('link', { name: 'Open email app for Mimi' }),
    ).toHaveAttribute('href', 'mailto:mia%3Fsubject%23progress%25@example.test')
    expect(screen.getByLabelText('Email address for Mimi')).toHaveValue(email)

    await user.click(
      screen.getByRole('button', { name: 'Copy email address for Mimi' }),
    )

    expect(writeText).toHaveBeenCalledWith(email)
    expect(screen.getByRole('status')).toHaveTextContent('Copied.')
  })

  it('uses the full name and selects the visible fallback without clipboard access', async () => {
    const user = userEvent.setup()
    setClipboard(undefined)

    render(
      <EmailContactActions
        email="ava@example.test"
        fullName="Ava Singh"
        preferredName={null}
      />,
    )

    const address = screen.getByLabelText('Email address for Ava Singh')
    await user.click(
      screen.getByRole('button', {
        name: 'Copy email address for Ava Singh',
      }),
    )

    expect(address).toHaveFocus()
    expect(address).toHaveProperty('selectionStart', 0)
    expect(address).toHaveProperty('selectionEnd', 'ava@example.test'.length)
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Copy is unavailable. Select the value to copy it manually.',
    )
  })

  it('selects the manual fallback when clipboard writing is rejected', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('Permission denied'))
    const user = userEvent.setup()
    setClipboard({ writeText })

    render(
      <EmailContactActions
        email="mia@example.test"
        fullName="Mia Chen"
        preferredName="Mimi"
      />,
    )

    const address = screen.getByLabelText('Email address for Mimi')
    await user.click(
      screen.getByRole('button', { name: 'Copy email address for Mimi' }),
    )

    expect(writeText).toHaveBeenCalledWith('mia@example.test')
    expect(address).toHaveFocus()
    expect(address).toHaveProperty('selectionStart', 0)
    expect(address).toHaveProperty('selectionEnd', 'mia@example.test'.length)
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Copy is unavailable. Select the value to copy it manually.',
    )
  })
})
