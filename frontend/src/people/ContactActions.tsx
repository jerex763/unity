import { useTranslation } from 'react-i18next'

import { CopyableContact } from './CopyableContact'
import { EmailContactActions } from './EmailContactActions'
import { whatsappHref } from './contactLinks'

type ContactActionsProps = {
  email: string | null
  fullName: string
  hasWhatsapp: boolean
  phone: string | null
  preferredName: string | null
  wechatId: string | null
}

export function ContactActions({
  email,
  fullName,
  hasWhatsapp,
  phone,
  preferredName,
  wechatId,
}: ContactActionsProps) {
  const { t } = useTranslation()
  const contactName = preferredName?.trim() || fullName
  const whatsapp = hasWhatsapp && phone ? whatsappHref(phone) : null

  if (!email && !phone && !wechatId) return null

  return (
    <div
      aria-label={t('contact.actionsFor', { name: contactName })}
      className="contact-actions"
      role="group"
    >
      {hasWhatsapp && phone ? (
        <div className="contact-channel" data-contact-channel="whatsapp">
          {whatsapp ? (
            <a
              aria-label={t('contact.openWhatsappFor', { name: contactName })}
              className="contact-link"
              href={whatsapp}
              rel="noreferrer"
              target="_blank"
            >
              {t('contact.openWhatsapp')}
            </a>
          ) : (
            <p className="contact-channel-note">
              {t('contact.manualWhatsapp')}
            </p>
          )}
          <CopyableContact
            copyLabel={t('contact.copyPhoneFor', { name: contactName })}
            inputLabel={t('contact.phoneFor', { name: contactName })}
            primary={!whatsapp}
            value={phone}
          />
        </div>
      ) : null}

      {wechatId ? (
        <div className="contact-channel" data-contact-channel="wechat">
          <p className="contact-channel-note">{t('contact.wechat')}</p>
          <CopyableContact
            copyLabel={t('contact.copyWechatFor', { name: contactName })}
            inputLabel={t('contact.wechatFor', { name: contactName })}
            primary
            value={wechatId}
          />
        </div>
      ) : null}

      {phone ? (
        <a
          aria-label={t('directory.callPerson', { name: contactName })}
          className="contact-link"
          data-contact-channel="call"
          href={`tel:${phone}`}
        >
          {t('directory.call')}
        </a>
      ) : null}

      {email ? (
        <EmailContactActions
          email={email}
          fullName={fullName}
          preferredName={preferredName}
        />
      ) : null}
    </div>
  )
}
