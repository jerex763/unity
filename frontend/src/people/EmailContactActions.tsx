import { useTranslation } from 'react-i18next'

import { CopyableContact } from './CopyableContact'
import { emailAppHref } from './contactLinks'

type EmailContactActionsProps = {
  email: string
  fullName: string
  preferredName: string | null
}

export function EmailContactActions({
  email,
  fullName,
  preferredName,
}: EmailContactActionsProps) {
  const { t } = useTranslation()
  const contactName = preferredName?.trim() || fullName

  return (
    <div
      aria-label={t('contact.emailActionsFor', { name: contactName })}
      className="contact-channel email-contact-actions"
      data-contact-channel="email"
      role="group"
    >
      <a
        aria-label={t('contact.openEmailAppFor', { name: contactName })}
        className="contact-link secondary"
        href={emailAppHref(email)}
      >
        {t('contact.openEmailApp')}
      </a>
      <CopyableContact
        copyLabel={t('contact.copyEmailFor', { name: contactName })}
        inputLabel={t('contact.emailAddressFor', { name: contactName })}
        value={email}
      />
    </div>
  )
}
