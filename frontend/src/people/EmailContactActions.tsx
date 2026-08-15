import { useTranslation } from 'react-i18next'

import { CopyableContact } from './CopyableContact'
import { emailAppHref } from './contactLinks'

type EmailContactActionsProps = {
  email: string
  fullName: string
  preferredName: string | null
  preferred?: boolean
}

export function EmailContactActions({
  email,
  fullName,
  preferredName,
  preferred = false,
}: EmailContactActionsProps) {
  const { t } = useTranslation()
  const contactName = preferredName?.trim() || fullName

  return (
    <div
      aria-label={t('contact.emailActionsFor', { name: contactName })}
      className={`contact-channel email-contact-actions${preferred ? ' preferred' : ''}`}
      data-contact-channel="email"
      role="group"
    >
      <strong className="contact-channel-label">
        Email{preferred ? ' · Preferred' : ''}
      </strong>
      <CopyableContact
        copyLabel={t('contact.copyEmailFor', { name: contactName })}
        inputLabel={t('contact.emailAddressFor', { name: contactName })}
        value={email}
      />
      <a
        aria-label={t('contact.openEmailAppFor', { name: contactName })}
        className="contact-link secondary"
        href={emailAppHref(email)}
      >
        {t('contact.openEmailApp')}
      </a>
    </div>
  )
}
