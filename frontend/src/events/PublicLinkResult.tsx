import { useLayoutEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'

type Props = {
  url?: string
  error?: string
  notice?: string
  retry?: () => void
}

export function PublicLinkResult({ url, error, notice, retry }: Props) {
  const { t } = useTranslation()
  const resultRef = useRef<HTMLDivElement>(null)
  useLayoutEffect(() => {
    const region = resultRef.current
    if (!region || (!url && !error && !notice)) return
    const target = region.querySelector('input') ?? region
    target.focus({ preventScroll: true })
    region.scrollIntoView?.({ block: 'center', behavior: 'instant' })
  }, [url, error, notice])

  if (!url && !error && !notice) return null
  return (
    <div className="public-link-result" ref={resultRef} tabIndex={-1}>
      {url ? (
        <input
          aria-label={t('events.publicLink.url')}
          readOnly
          type="text"
          inputMode="url"
          value={url}
          onFocus={(event) => event.currentTarget.select()}
        />
      ) : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p className="form-success" role="status">
          {notice}
        </p>
      ) : null}
      {retry ? (
        <button className="secondary-button" onClick={retry} type="button">
          {t('events.publicLink.retry')}
        </button>
      ) : null}
    </div>
  )
}
