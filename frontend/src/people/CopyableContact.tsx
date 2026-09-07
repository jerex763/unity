import { useLayoutEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

type CopyableContactProps = {
  copyLabel: string
  inputLabel: string
  primary?: boolean
  value: string
}

type CopyResult = {
  value: string
  status: 'copied' | 'unavailable'
} | null

export function CopyableContact({
  copyLabel,
  inputLabel,
  primary = false,
  value,
}: CopyableContactProps) {
  const { t } = useTranslation()
  const input = useRef<HTMLTextAreaElement>(null)
  const [copyResult, setCopyResult] = useState<CopyResult>(null)
  const copyState = copyResult?.value === value ? copyResult.status : 'idle'

  useLayoutEffect(() => {
    const element = input.current
    if (!element) return
    let previousWidth = -1
    function fitValue() {
      if (!element) return
      element.style.height = 'auto'
      element.style.height = `${element.scrollHeight}px`
    }
    fitValue()
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', fitValue)
      return () => window.removeEventListener('resize', fitValue)
    }
    const observer = new ResizeObserver(() => {
      const width = element.clientWidth
      if (width === previousWidth) return
      previousWidth = width
      fitValue()
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [value])

  function selectValue() {
    input.current?.focus()
    input.current?.select()
  }

  async function copyValue() {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard missing')
      await navigator.clipboard.writeText(value)
      setCopyResult({ value, status: 'copied' })
    } catch {
      selectValue()
      setCopyResult({ value, status: 'unavailable' })
    }
  }

  return (
    <>
      <textarea
        aria-label={inputLabel}
        className="contact-value-copy"
        onFocus={(event) => event.currentTarget.select()}
        readOnly
        ref={input}
        rows={1}
        value={value}
      />
      <button
        aria-label={copyLabel}
        className={`contact-link${primary ? '' : ' secondary'}`}
        onClick={() => void copyValue()}
        type="button"
      >
        {t('contact.copy')}
      </button>
      {copyState !== 'idle' ? (
        <p
          className={`contact-copy-feedback ${copyState}`}
          role={copyState === 'unavailable' ? 'alert' : 'status'}
        >
          {t(
            copyState === 'copied'
              ? 'contact.valueCopied'
              : 'contact.copyUnavailable',
          )}
        </p>
      ) : null}
    </>
  )
}
