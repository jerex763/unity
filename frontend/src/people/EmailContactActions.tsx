import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { emailAppHref } from './emailAppHref'

type EmailContactActionsProps = {
  email: string
  fullName: string
  preferredName: string | null
}

type CopyResult = {
  email: string
  status: 'copied' | 'unavailable'
} | null

export function EmailContactActions({
  email,
  fullName,
  preferredName,
}: EmailContactActionsProps) {
  const { t } = useTranslation()
  const emailInput = useRef<HTMLInputElement>(null)
  const [copyResult, setCopyResult] = useState<CopyResult>(null)
  const contactName = preferredName?.trim() || fullName
  const copyState = copyResult?.email === email ? copyResult.status : 'idle'

  function selectEmail() {
    emailInput.current?.focus()
    emailInput.current?.select()
  }

  async function copyEmail() {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard missing')
      await navigator.clipboard.writeText(email)
      setCopyResult({ email, status: 'copied' })
    } catch {
      selectEmail()
      setCopyResult({ email, status: 'unavailable' })
    }
  }

  return (
    <div
      aria-label={t('contact.emailActionsFor', { name: contactName })}
      className="email-contact-actions"
      role="group"
    >
      <a
        aria-label={t('contact.openEmailAppFor', { name: contactName })}
        className="contact-link"
        href={emailAppHref(email)}
      >
        {t('contact.openEmailApp')}
      </a>
      <button
        aria-label={t('contact.copyEmailFor', { name: contactName })}
        className="contact-link secondary"
        onClick={() => void copyEmail()}
        type="button"
      >
        {t('contact.copyEmail')}
      </button>
      <input
        aria-label={t('contact.emailAddressFor', { name: contactName })}
        className="email-address-copy"
        inputMode="email"
        onFocus={(event) => event.currentTarget.select()}
        readOnly
        ref={emailInput}
        type="text"
        value={email}
      />
      {copyState !== 'idle' ? (
        <p
          className={`email-copy-feedback ${copyState}`}
          role={copyState === 'unavailable' ? 'alert' : 'status'}
        >
          {t(
            copyState === 'copied'
              ? 'contact.emailCopied'
              : 'contact.emailCopyUnavailable',
          )}
        </p>
      ) : null}
    </div>
  )
}
