import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError, apiRequest } from '../api/client'
import type { ChurchEvent } from './types'

type Action = 'create' | 'revoke' | 'show' | 'copy'
type Feedback = { error?: string; notice?: string; retry?: 'show' | 'copy' }

export function usePublicLinks(
  onEnabled: (id: number, enabled: boolean) => void,
) {
  const { t } = useTranslation()
  const [urls, setUrls] = useState<Record<number, string>>({})
  const [feedback, setFeedback] = useState<Record<number, Feedback>>({})
  const [pending, setPending] = useState<Set<number>>(new Set())
  const requests = useRef(new Set<number>())
  const lifetime = useRef(0)
  useEffect(() => {
    lifetime.current += 1
    return () => {
      lifetime.current += 1
    }
  }, [])

  function hide(id: number) {
    setUrls((current) => {
      const next = { ...current }
      delete next[id]
      return next
    })
  }

  async function act(event: ChurchEvent, action: Action) {
    const id = event.id
    if (requests.current.has(id)) return
    if (
      action === 'create' &&
      event.public_registration_enabled &&
      !window.confirm(t('events.publicLink.replaceConfirm'))
    )
      return
    requests.current.add(id)
    setPending(new Set(requests.current))
    const generation = lifetime.current
    const active = () => generation === lifetime.current
    hide(id)
    setFeedback((current) => ({ ...current, [id]: {} }))
    try {
      const result = await apiRequest<{ url: string }>(
        `/events/${id}/public-link/`,
        {
          method:
            action === 'create'
              ? 'POST'
              : action === 'revoke'
                ? 'DELETE'
                : 'GET',
          cache: 'no-store',
        },
      )
      if (!active()) return
      if (action === 'revoke' || action === 'create') {
        onEnabled(id, action === 'create')
        setFeedback((current) => ({
          ...current,
          [id]: {
            notice: t(
              action === 'create'
                ? 'events.publicLink.ready'
                : 'events.publicLink.revoked',
            ),
          },
        }))
        return
      }
      if (action === 'show') {
        setUrls((current) => ({ ...current, [id]: result.url }))
      } else {
        try {
          await navigator.clipboard.writeText(result.url)
          if (!active()) return
          setFeedback((current) => ({
            ...current,
            [id]: { notice: t('events.publicLink.copied') },
          }))
        } catch {
          if (!active()) return
          setUrls((current) => ({ ...current, [id]: result.url }))
          setFeedback((current) => ({
            ...current,
            [id]: { error: t('events.publicLink.copyError') },
          }))
        }
      }
    } catch (error) {
      if (!active()) return
      const code = error instanceof ApiError ? error.payload.code : undefined
      const recovery = action === 'copy' || action === 'show'
      const retryable =
        !(error instanceof ApiError) ||
        error.status >= 500 ||
        [408, 429].includes(error.status)
      const message =
        code === 'legacy_link'
          ? 'legacy'
          : code === 'registration_closed'
            ? 'closed'
            : error instanceof ApiError && error.status === 404
              ? 'unavailable'
              : error instanceof ApiError && error.status === 403
                ? 'forbidden'
                : recovery
                  ? 'loadError'
                  : 'error'
      setFeedback((current) => ({
        ...current,
        [id]: {
          error: t(`events.publicLink.${message}`),
          ...(recovery && retryable ? { retry: action } : {}),
        },
      }))
    } finally {
      if (active()) {
        requests.current.delete(id)
        setPending(new Set(requests.current))
      }
    }
  }
  return { urls, feedback, pending, hide, act }
}
