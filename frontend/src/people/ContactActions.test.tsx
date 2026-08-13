import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import '../i18n'
import { ContactActions } from './ContactActions'
import { whatsappHref } from './contactLinks'

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

function channelOrder(container: HTMLElement) {
  return [...container.querySelectorAll('[data-contact-channel]')].map(
    (element) => element.getAttribute('data-contact-channel'),
  )
}

describe('ContactActions', () => {
  it.each([
    [' +61 (400) 000-001 ', 'https://wa.me/61400000001'],
    ['0061 (400) 000-001', 'https://wa.me/61400000001'],
    ['+1', 'https://wa.me/1'],
    ['+123456789012345', 'https://wa.me/123456789012345'],
  ])('builds a safe WhatsApp URL for valid formatted %s', (phone, expected) => {
    expect(whatsappHref(phone)).toBe(expected)
  })

  it.each([
    ['0400 000 001', 'local number'],
    ['61 400 000 001', 'missing explicit prefix'],
    ['+61 ext 4', 'alphabetic extension'],
    ['+61 x4', 'x extension'],
    ['+61?400', 'query delimiter'],
    ['+61#400', 'fragment delimiter'],
    ['+61%400', 'percent delimiter'],
    ['+61%20400', 'URI-encoded separator'],
    ['+61&400', 'ampersand delimiter'],
    ['+61=400', 'equals delimiter'],
    ['+61+400', 'later plus sign'],
    ['+61\t400', 'tab control'],
    ['+61\n400', 'newline control'],
    [`+61\u0000400`, 'null control'],
    ['+1234567890123456', 'more than 15 digits'],
    ['+0123', 'zero-leading international digits'],
    ['+', 'empty plus number'],
    ['00', 'empty 00 number'],
    ['+61–400', 'Unicode punctuation'],
    ['+６１４００', 'Unicode digits'],
  ])('rejects %s (%s) instead of stripping it', (phone) => {
    expect(whatsappHref(phone)).toBeNull()
  })

  it.each([
    ['+61 ext 4', 'alphabetic extension'],
    ['+61?400', 'URI delimiter'],
    ['+61%20400', 'URI-encoded sequence'],
    ['+61\n400', 'control/newline'],
    ['+1234567890123456', 'too long'],
    ['+0123', 'leading zero'],
    ['+', 'empty'],
    ['+61–400', 'Unicode punctuation'],
  ])('renders manual raw-copy fallback for invalid %s (%s)', (phone) => {
    render(
      <ContactActions
        email={null}
        fullName="Ava Singh"
        hasWhatsapp
        phone={phone}
        preferredName={null}
        wechatId={null}
      />,
    )

    expect(
      screen.queryByRole('link', { name: 'Open WhatsApp for Ava Singh' }),
    ).not.toBeInTheDocument()
    expect(screen.getByText(/open WhatsApp manually/i)).toBeVisible()
    expect(screen.getByLabelText('Phone number for Ava Singh')).toHaveValue(
      phone,
    )
  })

  it('orders WhatsApp, WeChat, Call, then Email and uses a preferred name', () => {
    const { container } = render(
      <ContactActions
        email="mia@example.test"
        fullName="Mia Chen"
        hasWhatsapp
        phone="+61 400 000 001"
        preferredName="Mimi"
        wechatId="mimi_wechat"
      />,
    )

    expect(channelOrder(container)).toEqual([
      'whatsapp',
      'wechat',
      'call',
      'email',
    ])
    expect(
      screen.getByRole('link', { name: 'Open WhatsApp for Mimi' }),
    ).toHaveAttribute('href', 'https://wa.me/61400000001')
    expect(screen.getByLabelText('Phone number for Mimi')).toHaveValue(
      '+61 400 000 001',
    )
    expect(screen.getByLabelText('WeChat ID for Mimi')).toHaveValue(
      'mimi_wechat',
    )
  })

  it('does not guess a WhatsApp URL for a local number and keeps a manual copy fallback', async () => {
    const user = userEvent.setup()
    setClipboard(undefined)
    render(
      <ContactActions
        email={null}
        fullName="Ava Singh"
        hasWhatsapp
        phone="0400 000 001"
        preferredName={null}
        wechatId={null}
      />,
    )

    expect(
      screen.queryByRole('link', { name: 'Open WhatsApp for Ava Singh' }),
    ).not.toBeInTheDocument()
    expect(screen.getByText(/open WhatsApp manually/i)).toBeVisible()
    expect(screen.getByLabelText('Phone number for Ava Singh')).toHaveValue(
      '0400 000 001',
    )
    expect(
      screen.getByRole('link', { name: 'Call Ava Singh' }),
    ).toHaveAttribute('href', 'tel:0400 000 001')
    const phone = screen.getByLabelText('Phone number for Ava Singh')
    await user.click(
      screen.getByRole('button', { name: 'Copy phone number for Ava Singh' }),
    )
    expect(phone).toHaveFocus()
    expect(phone).toHaveProperty('selectionStart', 0)
    expect(phone).toHaveProperty('selectionEnd', '0400 000 001'.length)
    expect(screen.getByRole('alert')).toBeVisible()
  })

  it('copies the raw WeChat ID and falls back to selection when clipboard rejects', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('Denied'))
    const user = userEvent.setup()
    setClipboard({ writeText })
    render(
      <ContactActions
        email={null}
        fullName="Mia Chen"
        hasWhatsapp={false}
        phone={null}
        preferredName="Mimi"
        wechatId="raw.wechat-id"
      />,
    )

    const input = screen.getByLabelText('WeChat ID for Mimi')
    await user.click(
      screen.getByRole('button', { name: 'Copy WeChat ID for Mimi' }),
    )

    expect(writeText).toHaveBeenCalledWith('raw.wechat-id')
    expect(input).toHaveFocus()
    expect(input).toHaveProperty('selectionStart', 0)
    expect(input).toHaveProperty('selectionEnd', 'raw.wechat-id'.length)
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Copy is unavailable. Select the value to copy it manually.',
    )
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('handles missing clipboard, partial contact, and no-contact states', async () => {
    const user = userEvent.setup()
    setClipboard(undefined)
    const { container, rerender } = render(
      <ContactActions
        email="ava@example.test"
        fullName="Ava Singh"
        hasWhatsapp={false}
        phone={null}
        preferredName={null}
        wechatId={null}
      />,
    )

    expect(channelOrder(container)).toEqual(['email'])
    const emailGroup = screen.getByRole('group', {
      name: 'Email actions for Ava Singh',
    })
    await user.click(
      within(emailGroup).getByRole('button', {
        name: 'Copy email address for Ava Singh',
      }),
    )
    expect(within(emailGroup).getByRole('alert')).toBeVisible()

    rerender(
      <ContactActions
        email={null}
        fullName="No Contact"
        hasWhatsapp={false}
        phone={null}
        preferredName={null}
        wechatId={null}
      />,
    )
    expect(container).toBeEmptyDOMElement()
  })
})
