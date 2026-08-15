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
  preferredContact?: 'phone' | 'whatsapp' | 'wechat' | 'email' | null
  wechatId: string | null
}

export function ContactActions({
  email,
  fullName,
  hasWhatsapp,
  phone,
  preferredName,
  preferredContact,
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
        <div
          className={`contact-channel${preferredContact === 'whatsapp' ? ' preferred' : ''}`}
          data-contact-channel="whatsapp"
        >
          <strong className="contact-channel-label">
            WhatsApp{preferredContact === 'whatsapp' ? ' · Preferred' : ''}
          </strong>
          <CopyableContact
            copyLabel={t('contact.copyPhoneFor', { name: contactName })}
            inputLabel={t('contact.phoneFor', { name: contactName })}
            primary={!whatsapp}
            value={phone}
          />
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
        </div>
      ) : null}

      {wechatId ? (
        <div
          className={`contact-channel${preferredContact === 'wechat' ? ' preferred' : ''}`}
          data-contact-channel="wechat"
        >
          <strong className="contact-channel-label">
            {t('contact.wechat')}
            {preferredContact === 'wechat' ? ' · Preferred' : ''}
          </strong>
          <CopyableContact
            copyLabel={t('contact.copyWechatFor', { name: contactName })}
            inputLabel={t('contact.wechatFor', { name: contactName })}
            primary
            value={wechatId}
          />
        </div>
      ) : null}

      {phone ? (
        <div
          className={`contact-channel${preferredContact === 'phone' ? ' preferred' : ''}`}
          data-contact-channel="call"
        >
          <strong className="contact-channel-label">
            Phone{preferredContact === 'phone' ? ' · Preferred' : ''}
          </strong>
          {hasWhatsapp ? (
            <span className="contact-value-text">{phone}</span>
          ) : (
            <CopyableContact
              copyLabel={t('contact.copyPhoneFor', { name: contactName })}
              inputLabel={t('contact.phoneFor', { name: contactName })}
              value={phone}
            />
          )}
          <a
            aria-label={t('directory.callPerson', { name: contactName })}
            className="contact-link"
            href={`tel:${phone}`}
          >
            {t('directory.call')}
          </a>
        </div>
      ) : null}

      {email ? (
        <EmailContactActions
          email={email}
          fullName={fullName}
          preferred={preferredContact === 'email'}
          preferredName={preferredName}
        />
      ) : null}
    </div>
  )
}
