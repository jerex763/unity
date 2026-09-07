import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { ApiError, apiRequest } from '../api/client'
import { useModalDialog } from '../accessibility/useModalDialog'
import { useAuth } from '../auth/useAuth'
import { ContactActions } from '../people/ContactActions'
import type {
  FollowUp,
  FollowUpStatus,
  Interaction,
  WorkerChoice,
} from './types'
import '../styles/task-navigation.css'

const statuses: FollowUpStatus[] = [
  'new',
  'assigned',
  'in_progress',
  'connected',
  'closed',
]

type EditFields = {
  status: FollowUpStatus
  engagement: FollowUp['engagement']
  assigned_to: string
  due_at: string
  outcome: string
  postpone_reason: string
  postpone_interaction: string
}

type EditFieldErrors = Partial<Record<keyof EditFields, string>>

function firstError(value: unknown): string | undefined {
  if (typeof value === 'string') return value
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return undefined
}

function editFields(item: FollowUp): EditFields {
  return {
    status: item.status,
    engagement: item.engagement,
    assigned_to: item.assigned_to?.toString() ?? '',
    due_at: item.due_at ?? '',
    outcome: item.outcome ?? '',
    postpone_reason: '',
    postpone_interaction: '',
  }
}

function formatDisplayDate(value: string | null) {
  if (!value) return null
  return new Intl.DateTimeFormat('en-AU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${value}T00:00:00Z`))
}

function usePhoneLayout() {
  const [isPhone, setIsPhone] = useState(() =>
    typeof window.matchMedia === 'function'
      ? window.matchMedia('(max-width: 47.999rem)').matches
      : false,
  )

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const query = window.matchMedia('(max-width: 47.999rem)')
    const updateLayout = () => setIsPhone(query.matches)
    if (typeof query.addEventListener !== 'function') return
    query.addEventListener('change', updateLayout)
    return () => query.removeEventListener('change', updateLayout)
  }, [])

  return isPhone
}

export function FollowUpQueuePage() {
  const { t } = useTranslation()
  const { session } = useAuth()
  const isPhone = usePhoneLayout()
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const taskParam = searchParams.get('task')
  const requestedTaskId =
    taskParam && /^\d+$/.test(taskParam) ? Number(taskParam) : null
  const hasTaskQuery = taskParam !== null
  const [items, setItems] = useState<FollowUp[]>([])
  const [workers, setWorkers] = useState<WorkerChoice[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [editing, setEditing] = useState<FollowUp | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [queueFilter, setQueueFilter] = useState<
    'mine' | 'unassigned' | 'overdue' | 'all'
  >('all')
  const [fields, setFields] = useState<EditFields | null>(null)
  const [fieldErrors, setFieldErrors] = useState<EditFieldErrors>({})
  const [saveError, setSaveError] = useState('')
  const [saveNotice, setSaveNotice] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [interactions, setInteractions] = useState<Interaction[]>([])
  const [interactionKind, setInteractionKind] =
    useState<Interaction['kind']>('call')
  const [interactionVisibility, setInteractionVisibility] =
    useState<Interaction['visibility']>('staff')
  const [interactionSummary, setInteractionSummary] = useState('')
  const [interactionError, setInteractionError] = useState('')
  const selectionGeneration = useRef(0)
  const interactionRequestGeneration = useRef(0)
  const selectedFollowUpIdRef = useRef<number | null>(null)
  const interactionSummaryRef = useRef('')
  const interactionDraftsRef = useRef<Record<number, string>>({})
  const queueReturnRef = useRef<{
    filter: typeof queueFilter
    selectedId: number
    scrollY: number
  } | null>(null)
  const updateTitleRef = useRef<HTMLHeadingElement>(null)
  const detailHeadingRef = useRef<HTMLHeadingElement>(null)
  const detailSectionRef = useRef<HTMLElement>(null)
  const updateDialogRef = useModalDialog<HTMLElement>(
    isEditing,
    closeEdit,
    updateTitleRef,
  )

  function openEdit() {
    if (!editing) return
    setFields(editFields(editing))
    setFieldErrors({})
    setSaveError('')
    setSaveNotice('')
    setIsEditing(true)
  }

  function closeEdit() {
    if (isSaving) return
    if (editing) setFields(editFields(editing))
    setFieldErrors({})
    setSaveError('')
    setIsEditing(false)
  }

  const loadInteractions = useCallback(
    (followUpId: number) => {
      const generation = ++interactionRequestGeneration.current
      setInteractions([])
      setInteractionError('')
      void apiRequest<Interaction[]>(`/follow-ups/${followUpId}/interactions/`)
        .then((rows) => {
          if (generation === interactionRequestGeneration.current) {
            setInteractions(rows)
          }
        })
        .catch(() => {
          if (generation === interactionRequestGeneration.current) {
            setInteractionError(t('followUps.interactions.loadError'))
          }
        })
    },
    [t],
  )

  const selectFollowUp = useCallback(
    (item: FollowUp | null) => {
      const previousId = selectedFollowUpIdRef.current
      if (previousId !== null) {
        interactionDraftsRef.current[previousId] = interactionSummaryRef.current
      }
      selectionGeneration.current += 1
      setIsSaving(false)
      setFieldErrors({})
      setSaveError('')
      setSaveNotice('')
      if (!item) {
        selectedFollowUpIdRef.current = null
        interactionSummaryRef.current = ''
        setInteractionSummary('')
        interactionRequestGeneration.current += 1
        setEditing(null)
        setFields(null)
        setInteractions([])
        setInteractionError('')
        setIsEditing(false)
        return
      }
      selectedFollowUpIdRef.current = item.id
      const itemDraft = interactionDraftsRef.current[item.id] ?? ''
      interactionSummaryRef.current = itemDraft
      setInteractionSummary(itemDraft)
      setEditing(item)
      setIsEditing(false)
      setFields(editFields(item))
      loadInteractions(item.id)
    },
    [loadInteractions],
  )

  useEffect(() => {
    let active = true
    void Promise.all([
      apiRequest<FollowUp[]>('/follow-ups/'),
      apiRequest<WorkerChoice[]>('/follow-ups/workers/'),
    ])
      .then(([followUps, workerRows]) => {
        if (!active) return
        setItems(followUps)
        setWorkers(workerRows)
      })
      .catch(() => {
        if (active) setLoadError(t('followUps.loadError'))
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [t])

  useEffect(() => {
    if (!saveNotice) return
    ;(isPhone
      ? detailSectionRef.current
      : detailHeadingRef.current
    )?.scrollIntoView?.({
      behavior: 'smooth',
      block: 'start',
    })
    detailHeadingRef.current?.focus({ preventScroll: true })
  }, [saveNotice, isPhone])

  function beginEdit(item: FollowUp) {
    selectFollowUp(item)
    queueReturnRef.current = {
      filter: queueFilter,
      selectedId: item.id,
      scrollY: window.scrollY,
    }
    const next = new URLSearchParams(searchParams)
    next.set('task', String(item.id))
    navigate(
      { pathname: location.pathname, search: `?${next.toString()}` },
      {
        state: { fromFollowUpQueue: true },
      },
    )
  }

  function returnToQueue() {
    if (isSaving) return
    if (
      location.state &&
      typeof location.state === 'object' &&
      'fromFollowUpQueue' in location.state
    ) {
      navigate(-1)
      return
    }
    const next = new URLSearchParams(searchParams)
    next.delete('task')
    setSearchParams(next, { replace: true })
  }

  function changeQueueFilter(
    filter: 'mine' | 'unassigned' | 'overdue' | 'all',
  ) {
    setQueueFilter(filter)
    if (!hasTaskQuery) return
    const next = new URLSearchParams(searchParams)
    next.delete('task')
    setSearchParams(next, { replace: true })
  }

  async function addInteraction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editing) return
    const generation = interactionRequestGeneration.current
    setInteractionError('')
    try {
      const interaction = await apiRequest<Interaction>(
        `/follow-ups/${editing.id}/interactions/`,
        {
          method: 'POST',
          body: JSON.stringify({
            kind: interactionKind,
            visibility: interactionVisibility,
            summary: interactionSummary,
          }),
        },
      )
      if (generation === interactionRequestGeneration.current) {
        setInteractions((current) => [interaction, ...current])
        interactionDraftsRef.current[editing.id] = ''
        interactionSummaryRef.current = ''
        setInteractionSummary('')
      }
    } catch {
      if (generation === interactionRequestGeneration.current) {
        setInteractionError(t('followUps.interactions.saveError'))
      }
    }
  }

  function update<Key extends keyof EditFields>(
    key: Key,
    value: EditFields[Key],
  ) {
    setFields((current) => {
      if (!current) return current
      const next = { ...current, [key]: value }
      if (
        key === 'due_at' &&
        editing?.due_at &&
        (!value || String(value) <= editing.due_at)
      ) {
        next.postpone_reason = ''
        next.postpone_interaction = ''
      }
      return next
    })
    setFieldErrors((current) => {
      const next = { ...current, [key]: undefined }
      if (key === 'due_at') {
        next.postpone_reason = undefined
        next.postpone_interaction = undefined
      }
      return next
    })
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editing || !fields) return
    const savedFollowUpId = editing.id
    const savedSelectionGeneration = selectionGeneration.current
    const isCurrentSelection = () =>
      savedSelectionGeneration === selectionGeneration.current
    setIsSaving(true)
    setFieldErrors({})
    setSaveError('')
    try {
      const isMovingLater = Boolean(
        editing.due_at && fields.due_at && fields.due_at > editing.due_at,
      )
      const postponementEvidence = isMovingLater
        ? {
            ...(fields.postpone_reason
              ? { postpone_reason: fields.postpone_reason }
              : {}),
            ...(fields.postpone_interaction
              ? { postpone_interaction: Number(fields.postpone_interaction) }
              : {}),
          }
        : {}
      const updated = await apiRequest<FollowUp>(`/follow-ups/${editing.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({
          status: fields.status,
          engagement: fields.engagement,
          assigned_to: fields.assigned_to ? Number(fields.assigned_to) : null,
          due_at: fields.due_at || null,
          outcome: fields.outcome || null,
          ...postponementEvidence,
        }),
      })
      setItems((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      )
      if (isCurrentSelection() && updated.id === savedFollowUpId) {
        setEditing(updated)
        setFields(editFields(updated))
        setIsEditing(false)
        setSaveNotice(t('followUps.saved'))
      }
    } catch (error) {
      if (!isCurrentSelection()) return
      if (error instanceof ApiError) {
        const nextFieldErrors = Object.fromEntries(
          (Object.keys(fields) as (keyof EditFields)[])
            .map((key) => [key, firstError(error.payload[key])])
            .filter((entry): entry is [keyof EditFields, string] =>
              Boolean(entry[1]),
            ),
        )
        setFieldErrors(nextFieldErrors)
        const generalError =
          firstError(error.payload.non_field_errors) ??
          firstError(error.payload.detail)
        if (generalError || !Object.keys(nextFieldErrors).length) {
          setSaveError(generalError ?? t('followUps.saveError'))
        }
      } else {
        setSaveError(t('followUps.saveError'))
      }
    } finally {
      if (isCurrentSelection()) setIsSaving(false)
    }
  }

  const queueItems = useMemo(() => {
    const priority = (item: FollowUp) => {
      if (item.status === 'closed') return 5
      if (item.attention?.escalated) return 0
      if (item.attention?.overdue) return 1
      if (item.attention?.due_today) return 2
      if (item.assigned_to === null) return 3
      return 4
    }
    return items
      .map((item, serverIndex) => ({ item, serverIndex }))
      .filter(({ item }) => {
        if (queueFilter === 'mine') {
          return item.assigned_to === session?.user.id
        }
        if (queueFilter === 'unassigned') return item.assigned_to === null
        if (queueFilter === 'overdue') return Boolean(item.attention?.overdue)
        return true
      })
      .sort((first, second) => {
        const priorityDifference = priority(first.item) - priority(second.item)
        if (priorityDifference) return priorityDifference
        const firstDue = first.item.due_at
        const secondDue = second.item.due_at
        if (firstDue && secondDue && firstDue !== secondDue) {
          return firstDue.localeCompare(secondDue)
        }
        if (firstDue && !secondDue) return -1
        if (!firstDue && secondDue) return 1
        return first.serverIndex - second.serverIndex
      })
      .map(({ item }) => item)
  }, [items, queueFilter, session?.user.id])

  useEffect(() => {
    if (isLoading || loadError) return
    if (hasTaskQuery) {
      const requested =
        requestedTaskId === null
          ? null
          : (items.find((item) => item.id === requestedTaskId) ?? null)
      if (requested?.id === editing?.id) return
      selectFollowUp(requested)
      return
    }
    if (isPhone) return
    if (editing && queueItems.some((item) => item.id === editing.id)) return
    selectFollowUp(queueItems[0] ?? null)
  }, [
    editing,
    hasTaskQuery,
    isLoading,
    isPhone,
    items,
    loadError,
    queueItems,
    requestedTaskId,
    selectFollowUp,
  ])

  useEffect(() => {
    if (hasTaskQuery || !isPhone || !queueReturnRef.current) return
    const queueReturn = queueReturnRef.current
    setQueueFilter(queueReturn.filter)
    const frame = window.requestAnimationFrame(() => {
      window.scrollTo({ top: queueReturn.scrollY, behavior: 'auto' })
      window.requestAnimationFrame(() => {
        document
          .querySelector<HTMLElement>(
            `[data-follow-up-id="${queueReturn.selectedId}"]`,
          )
          ?.focus({ preventScroll: true })
      })
    })
    return () => window.cancelAnimationFrame(frame)
  }, [hasTaskQuery, isPhone])

  const taskUnavailable =
    !isLoading &&
    !loadError &&
    hasTaskQuery &&
    (requestedTaskId === null ||
      !items.some((item) => item.id === requestedTaskId))
  const hasVisibleEditing =
    editing !== null &&
    fields !== null &&
    (!hasTaskQuery || editing.id === requestedTaskId)

  useEffect(() => {
    if (!isPhone || !hasTaskQuery || !hasVisibleEditing) return
    const frame = window.requestAnimationFrame(() => {
      detailSectionRef.current?.scrollIntoView({
        behavior: 'auto',
        block: 'start',
      })
      detailHeadingRef.current?.focus({ preventScroll: true })
    })
    return () => window.cancelAnimationFrame(frame)
  }, [hasTaskQuery, hasVisibleEditing, isPhone, requestedTaskId])

  return (
    <main
      className={`follow-up-page${isPhone && hasTaskQuery ? ' mobile-detail-open' : ''}`}
    >
      <section className="page-heading">
        <p className="eyebrow">{t('followUps.eyebrow')}</p>
        <h1>{t('followUps.title')}</h1>
        <p>{t('followUps.intro')}</p>
      </section>

      {isPhone && hasTaskQuery && !hasVisibleEditing && !taskUnavailable ? (
        <button
          className="text-button follow-up-mobile-back follow-up-query-back"
          onClick={returnToQueue}
          type="button"
        >
          ← {t('followUps.backToQueue', { defaultValue: 'Back to queue' })}
        </button>
      ) : null}

      {isLoading ? (
        <p className="events-loading">{t('followUps.loading')}</p>
      ) : null}
      {loadError ? (
        <p className="form-error" role="alert">
          {loadError}
        </p>
      ) : null}

      <div
        className="follow-up-filters"
        role="group"
        aria-label="Follow-up queue filter"
      >
        {(['mine', 'unassigned', 'overdue', 'all'] as const).map((filter) => (
          <button
            aria-pressed={queueFilter === filter}
            className={queueFilter === filter ? 'active' : undefined}
            key={filter}
            onClick={() => changeQueueFilter(filter)}
            type="button"
          >
            {filter === 'mine'
              ? 'My follow-ups'
              : filter === 'unassigned'
                ? 'Unassigned'
                : filter === 'overdue'
                  ? 'Overdue'
                  : 'All'}
          </button>
        ))}
      </div>

      <div className="follow-up-workspace">
        <section className="follow-up-board" aria-label={t('followUps.board')}>
          <header>
            <h2>Priority queue</h2>
            <span>{queueItems.length}</span>
          </header>
          <div className="follow-up-card-list">
            {queueItems.map((item) => (
              <button
                className={`follow-up-card${editing?.id === item.id ? ' selected' : ''}`}
                data-follow-up-id={item.id}
                key={item.id}
                onClick={() => beginEdit(item)}
                type="button"
              >
                <div className="follow-up-card-heading">
                  <h3>{item.person.full_name}</h3>
                  <span
                    className={`engagement-chip engagement-${item.engagement}`}
                  >
                    {t(`followUps.engagement.${item.engagement}`)}
                  </span>
                </div>
                <p>
                  {t(`followUps.statuses.${item.status}`)} ·{' '}
                  {item.assigned_to_name ?? t('followUps.unassigned')} ·{' '}
                  {formatDisplayDate(item.due_at) ?? t('followUps.notSet')}
                </p>
                <div
                  className="follow-up-attention"
                  aria-label={t('followUps.attention.label')}
                >
                  {(
                    [
                      'escalated',
                      'overdue',
                      'due_today',
                      'stale',
                      'unassigned_too_long',
                      'no_action',
                    ] as const
                  ).map((flag) =>
                    item.attention?.[flag] ? (
                      <span
                        className={`attention-chip attention-${flag}`}
                        key={flag}
                      >
                        {t(`followUps.attention.${flag}`)}
                      </span>
                    ) : null,
                  )}
                </div>
                <p className="follow-up-next-action">
                  <strong>
                    {t('followUps.attention.nextAction')}:{' '}
                    {item.attention?.next_action ??
                      t('followUps.attention.defaultAction')}
                  </strong>
                </p>
              </button>
            ))}
            {!queueItems.length ? (
              <p className="follow-up-column-empty">
                No follow-ups match this filter.
              </p>
            ) : null}
          </div>
        </section>

        {hasVisibleEditing && editing && fields ? (
          <section
            className="follow-up-editor"
            ref={detailSectionRef}
            aria-labelledby="follow-up-editor"
          >
            <button
              className="text-button follow-up-mobile-back"
              disabled={isSaving}
              onClick={returnToQueue}
              type="button"
            >
              ← {t('followUps.backToQueue', { defaultValue: 'Back to queue' })}
            </button>
            <div className="profile-panel-heading">
              <div>
                <p className="eyebrow">{t('followUps.editorEyebrow')}</p>
                <h2 id="follow-up-editor" ref={detailHeadingRef} tabIndex={-1}>
                  {editing.person.full_name}
                </h2>
              </div>
              <button className="text-button" onClick={openEdit} type="button">
                {t('followUps.update')}
              </button>
            </div>
            <p className="follow-up-detail-next">
              <strong>
                {t('followUps.attention.nextAction')}:{' '}
                {editing.attention?.next_action ??
                  t('followUps.attention.defaultAction')}
              </strong>
            </p>
            {saveNotice ? (
              <p className="form-success follow-up-save-notice" role="status">
                {saveNotice}
              </p>
            ) : null}
            <dl className="follow-up-detail-summary">
              <div>
                <dt>{t('followUps.status')}</dt>
                <dd>{t(`followUps.statuses.${editing.status}`)}</dd>
              </div>
              <div>
                <dt>{t('followUps.assignee')}</dt>
                <dd>{editing.assigned_to_name ?? t('followUps.unassigned')}</dd>
              </div>
              <div>
                <dt>{t('followUps.due')}</dt>
                <dd>
                  {formatDisplayDate(editing.due_at) ?? t('followUps.notSet')}
                </dd>
              </div>
              {editing.outcome ? (
                <div className="follow-up-outcome-summary">
                  <dt>{t('followUps.outcome')}</dt>
                  <dd>{editing.outcome}</dd>
                </div>
              ) : null}
            </dl>
            <ContactActions
              email={editing.person.email}
              fullName={editing.person.full_name}
              hasWhatsapp={editing.person.has_whatsapp}
              phone={editing.person.phone}
              preferredContact={editing.person.preferred_contact}
              preferredName={editing.person.preferred_name}
              wechatId={editing.person.wechat_id}
            />
            {isEditing ? (
              <div className="dialog-backdrop">
                <section
                  aria-labelledby="follow-up-update-title"
                  aria-modal="true"
                  className="event-editor follow-up-update-dialog"
                  ref={updateDialogRef}
                  role="dialog"
                  tabIndex={-1}
                >
                  <div className="profile-panel-heading">
                    <div>
                      <p className="eyebrow">{t('followUps.editorEyebrow')}</p>
                      <h2
                        id="follow-up-update-title"
                        ref={updateTitleRef}
                        tabIndex={-1}
                      >
                        {t('followUps.editorTitle', {
                          name: editing.person.full_name,
                        })}
                      </h2>
                    </div>
                    <button
                      aria-label={t('followUps.cancel')}
                      className="dialog-close"
                      disabled={isSaving}
                      onClick={closeEdit}
                      type="button"
                    >
                      <span aria-hidden="true">×</span>
                    </button>
                  </div>
                  <form className="follow-up-form" onSubmit={save}>
                    <label>
                      <span>{t('followUps.status')}</span>
                      <select
                        onChange={(event) =>
                          update('status', event.target.value as FollowUpStatus)
                        }
                        value={fields.status}
                      >
                        {statuses.map((status) => (
                          <option key={status} value={status}>
                            {t(`followUps.statuses.${status}`)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span>{t('followUps.engagementLabel')}</span>
                      <small className="field-help">
                        {t('followUps.engagementHelp')}
                      </small>
                      <select
                        aria-label={t('followUps.engagementLabel')}
                        onChange={(event) =>
                          update(
                            'engagement',
                            event.target.value as FollowUp['engagement'],
                          )
                        }
                        value={fields.engagement}
                      >
                        {(['possible', 'probable', 'likely'] as const).map(
                          (value) => (
                            <option key={value} value={value}>
                              {t(`followUps.engagement.${value}`)}
                            </option>
                          ),
                        )}
                      </select>
                    </label>
                    <fieldset className="follow-up-assignment wide-field">
                      <legend>{t('followUps.assignmentLegend')}</legend>
                      <p>{t('followUps.assignmentHelp')}</p>
                      <div>
                        <label>
                          <span>{t('followUps.assignee')}</span>
                          <select
                            aria-label={t('followUps.assignee')}
                            aria-describedby={
                              fieldErrors.assigned_to
                                ? 'follow-up-assignee-error'
                                : undefined
                            }
                            aria-invalid={Boolean(fieldErrors.assigned_to)}
                            onChange={(event) =>
                              update('assigned_to', event.target.value)
                            }
                            value={fields.assigned_to}
                          >
                            <option value="">
                              {t('followUps.unassigned')}
                            </option>
                            {workers.map((worker) => (
                              <option key={worker.id} value={worker.id}>
                                {worker.name}
                              </option>
                            ))}
                          </select>
                          {fieldErrors.assigned_to ? (
                            <span
                              className="field-error"
                              id="follow-up-assignee-error"
                              role="alert"
                            >
                              {fieldErrors.assigned_to}
                            </span>
                          ) : null}
                        </label>
                        <label>
                          <span>{t('followUps.due')}</span>
                          <input
                            aria-label={t('followUps.due')}
                            aria-describedby={
                              fieldErrors.due_at
                                ? 'follow-up-due-error'
                                : undefined
                            }
                            aria-invalid={Boolean(fieldErrors.due_at)}
                            onChange={(event) =>
                              update('due_at', event.target.value)
                            }
                            type="date"
                            value={fields.due_at}
                          />
                          {fieldErrors.due_at ? (
                            <span
                              className="field-error"
                              id="follow-up-due-error"
                              role="alert"
                            >
                              {fieldErrors.due_at}
                            </span>
                          ) : null}
                        </label>
                      </div>
                    </fieldset>
                    {fields.due_at &&
                    editing.due_at &&
                    fields.due_at > editing.due_at &&
                    (editing.attention?.overdue ||
                      (editing.attention?.postponement_count ?? 0) > 0) ? (
                      <fieldset className="follow-up-assignment wide-field">
                        <legend>{t('followUps.postpone.legend')}</legend>
                        <p>{t('followUps.postpone.help')}</p>
                        <div>
                          <label>
                            <span>{t('followUps.postpone.reason')}</span>
                            <select
                              aria-invalid={Boolean(
                                fieldErrors.postpone_reason,
                              )}
                              onChange={(event) =>
                                update('postpone_reason', event.target.value)
                              }
                              value={fields.postpone_reason}
                            >
                              <option value="">
                                {t('followUps.postpone.chooseReason')}
                              </option>
                              {(
                                [
                                  'awaiting_response',
                                  'person_requested',
                                  'worker_availability',
                                  'other_operational',
                                ] as const
                              ).map((reason) => (
                                <option key={reason} value={reason}>
                                  {t(`followUps.postpone.reasons.${reason}`)}
                                </option>
                              ))}
                            </select>
                            {fieldErrors.postpone_reason ? (
                              <span className="field-error" role="alert">
                                {fieldErrors.postpone_reason}
                              </span>
                            ) : null}
                          </label>
                          <label>
                            <span>{t('followUps.postpone.interaction')}</span>
                            <select
                              aria-invalid={Boolean(
                                fieldErrors.postpone_interaction,
                              )}
                              onChange={(event) =>
                                update(
                                  'postpone_interaction',
                                  event.target.value,
                                )
                              }
                              value={fields.postpone_interaction}
                            >
                              <option value="">
                                {t('followUps.postpone.chooseInteraction')}
                              </option>
                              {interactions.map((interaction) => (
                                <option
                                  key={interaction.id}
                                  value={interaction.id}
                                >
                                  {t(
                                    `followUps.interactions.kinds.${interaction.kind}`,
                                  )}{' '}
                                  ·{' '}
                                  {new Date(
                                    interaction.created_at,
                                  ).toLocaleDateString()}
                                </option>
                              ))}
                            </select>
                            {fieldErrors.postpone_interaction ? (
                              <span className="field-error" role="alert">
                                {fieldErrors.postpone_interaction}
                              </span>
                            ) : null}
                          </label>
                        </div>
                      </fieldset>
                    ) : null}
                    <label className="wide-field">
                      <span>{t('followUps.outcome')}</span>
                      <small className="field-help">
                        {t('followUps.outcomeHelp')}
                      </small>
                      <textarea
                        aria-label={t('followUps.outcome')}
                        aria-describedby={
                          fieldErrors.outcome
                            ? 'follow-up-outcome-error'
                            : undefined
                        }
                        aria-invalid={Boolean(fieldErrors.outcome)}
                        onChange={(event) =>
                          update('outcome', event.target.value)
                        }
                        rows={3}
                        value={fields.outcome}
                      />
                      {fieldErrors.outcome ? (
                        <span
                          className="field-error"
                          id="follow-up-outcome-error"
                          role="alert"
                        >
                          {fieldErrors.outcome}
                        </span>
                      ) : null}
                    </label>
                    {saveError ? (
                      <p className="form-error wide-field" role="alert">
                        {saveError}
                      </p>
                    ) : null}
                    <div className="event-form-actions wide-field">
                      <button
                        className="secondary-button"
                        disabled={isSaving}
                        onClick={closeEdit}
                        type="button"
                      >
                        {t('followUps.cancel')}
                      </button>
                      <button
                        className="primary-button inline"
                        disabled={isSaving}
                        type="submit"
                      >
                        {isSaving ? t('followUps.saving') : t('followUps.save')}
                      </button>
                    </div>
                  </form>
                </section>
              </div>
            ) : null}
            <section className="interaction-log">
              <h3>{t('followUps.interactions.title')}</h3>
              {interactions.length ? (
                <div className="interaction-list">
                  {interactions.map((interaction) => (
                    <article key={interaction.id}>
                      <strong>
                        {t(`followUps.interactions.kinds.${interaction.kind}`)}
                      </strong>
                      <span>
                        {interaction.author} ·{' '}
                        {new Intl.DateTimeFormat(undefined, {
                          day: 'numeric',
                          month: 'short',
                          hour: 'numeric',
                          minute: '2-digit',
                        }).format(new Date(interaction.occurred_at))}
                      </span>
                      <p>{interaction.summary}</p>
                    </article>
                  ))}
                </div>
              ) : (
                <p>{t('followUps.interactions.empty')}</p>
              )}
              <form className="interaction-form" onSubmit={addInteraction}>
                <label>
                  <span>{t('followUps.interactions.kind')}</span>
                  <select
                    onChange={(event) =>
                      setInteractionKind(
                        event.target.value as Interaction['kind'],
                      )
                    }
                    value={interactionKind}
                  >
                    {(
                      ['call', 'message', 'visit', 'meeting', 'other'] as const
                    ).map((kind) => (
                      <option key={kind} value={kind}>
                        {t(`followUps.interactions.kinds.${kind}`)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>{t('followUps.interactions.visibility')}</span>
                  <select
                    onChange={(event) =>
                      setInteractionVisibility(
                        event.target.value as Interaction['visibility'],
                      )
                    }
                    value={interactionVisibility}
                  >
                    <option value="staff">
                      {t('followUps.interactions.visibilities.staff')}
                    </option>
                    <option value="leaders">
                      {t('followUps.interactions.visibilities.leaders')}
                    </option>
                    {session?.membership.role !== 'leader' ? (
                      <option value="pastors_only">
                        {t('followUps.interactions.visibilities.pastors_only')}
                      </option>
                    ) : null}
                  </select>
                </label>
                <label className="wide-field">
                  <span>{t('followUps.interactions.summary')}</span>
                  <textarea
                    onChange={(event) => {
                      interactionSummaryRef.current = event.target.value
                      setInteractionSummary(event.target.value)
                    }}
                    required
                    rows={2}
                    value={interactionSummary}
                  />
                </label>
                <button className="secondary-button" type="submit">
                  {t('followUps.interactions.add')}
                </button>
              </form>
              {interactionError ? (
                <p className="form-error" role="alert">
                  {interactionError}
                </p>
              ) : null}
            </section>
          </section>
        ) : null}
        {taskUnavailable ? (
          <section
            className="follow-up-editor follow-up-detail-unavailable"
            role="status"
          >
            <button
              className="text-button follow-up-mobile-back"
              onClick={returnToQueue}
              type="button"
            >
              ← {t('followUps.backToQueue', { defaultValue: 'Back to queue' })}
            </button>
            <h2>
              {t('followUps.unavailableTitle', {
                defaultValue: 'Follow-up unavailable',
              })}
            </h2>
            <p>
              {t('followUps.unavailableBody', {
                defaultValue:
                  'This follow-up may have been completed, removed, or may not be available in this church.',
              })}
            </p>
          </section>
        ) : null}
        {!hasVisibleEditing && !taskUnavailable ? (
          <section className="follow-up-editor follow-up-detail-empty">
            <h2>Select a follow-up</h2>
            <p>
              Choose a person from the priority queue to see contact details and
              activity.
            </p>
          </section>
        ) : null}
      </div>
    </main>
  )
}
