import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'

import { apiRequest } from '../api/client'
import { useAuth } from '../auth/useAuth'
import type {
  DirectoryPerson,
  PersonRelationship,
  ProfilePerson,
} from './types'

type ProfileTab =
  'overview' | 'relationships' | 'groups' | 'events' | 'followUps'
type ProfileState =
  | { status: 'loading'; person: null }
  | { status: 'ready'; person: ProfilePerson }
  | { status: 'error'; person: null }

type EditFields = {
  full_name: string
  preferred_name: string
  email: string
  phone: string
  wechat_id: string
  suburb: string
  university: string
  membership_status: ProfilePerson['membership_status']
  notes: string
  faith_background: string
  discipleship_stage: string
  invited_by: string
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))
}

function initials(person: ProfilePerson) {
  return person.full_name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

function editFields(person: ProfilePerson): EditFields {
  return {
    full_name: person.full_name,
    preferred_name: person.preferred_name ?? '',
    email: person.email ?? '',
    phone: person.phone ?? '',
    wechat_id: person.wechat_id ?? '',
    suburb: person.suburb ?? '',
    university: person.university ?? '',
    membership_status: person.membership_status,
    notes: person.notes ?? '',
    faith_background: person.faith_background ?? '',
    discipleship_stage: person.discipleship_stage ?? '',
    invited_by: person.invited_by?.toString() ?? '',
  }
}

export function ProfilePage() {
  const { t } = useTranslation()
  const { personId } = useParams()
  const { session } = useAuth()
  const [state, setState] = useState<ProfileState>({
    status: 'loading',
    person: null,
  })
  const [activeTab, setActiveTab] = useState<ProfileTab>('overview')
  const [isEditing, setIsEditing] = useState(false)
  const [fields, setFields] = useState<EditFields | null>(null)
  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [people, setPeople] = useState<DirectoryPerson[]>([])
  const [relationshipPerson, setRelationshipPerson] = useState('')
  const [relationshipKind, setRelationshipKind] =
    useState<PersonRelationship['kind']>('friend')
  const [relationshipError, setRelationshipError] = useState('')
  const [isSavingRelationship, setIsSavingRelationship] = useState(false)

  useEffect(() => {
    let active = true
    void apiRequest<ProfilePerson>(`/people/${personId}/`).then((person) => {
      if (active) {
        setState({ status: 'ready', person })
        setFields(editFields(person))
      }
    })
    void apiRequest<DirectoryPerson[]>('/people/')
      .then((result) => {
        if (active) setPeople(result)
      })
      .catch(() => {
        if (active) setPeople([])
      })
      .catch(() => {
        if (active) setState({ status: 'error', person: null })
      })
    return () => {
      active = false
    }
  }, [personId])

  const person = state.person
  const canEdit = session?.membership.role !== 'member'
  const canViewSensitive = ['admin', 'pastor'].includes(
    session?.membership.role ?? '',
  )

  function updateField<Key extends keyof EditFields>(
    key: Key,
    value: EditFields[Key],
  ) {
    setFields((current) => (current ? { ...current, [key]: value } : current))
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!fields || !person) return
    setSaveError('')
    setIsSaving(true)
    try {
      const updated = await apiRequest<ProfilePerson>(`/people/${person.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({
          full_name: fields.full_name,
          preferred_name: fields.preferred_name || null,
          email: fields.email || null,
          phone: fields.phone || null,
          wechat_id: fields.wechat_id || null,
          suburb: fields.suburb || null,
          university: fields.university || null,
          membership_status: fields.membership_status,
          invited_by: fields.invited_by ? Number(fields.invited_by) : null,
          notes: fields.notes,
          ...(canViewSensitive
            ? {
                faith_background: fields.faith_background || null,
                discipleship_stage: fields.discipleship_stage || null,
              }
            : {}),
        }),
      })
      setState({ status: 'ready', person: updated })
      setFields(editFields(updated))
      setIsEditing(false)
    } catch {
      setSaveError(t('profile.saveError'))
    } finally {
      setIsSaving(false)
    }
  }

  async function addRelationship(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!person || !relationshipPerson) return
    setRelationshipError('')
    setIsSavingRelationship(true)
    try {
      const relationship = await apiRequest<PersonRelationship>(
        `/people/${person.id}/relationships/`,
        {
          method: 'POST',
          body: JSON.stringify({
            person: Number(relationshipPerson),
            kind: relationshipKind,
          }),
        },
      )
      setState({
        status: 'ready',
        person: {
          ...person,
          relationships: [...person.relationships, relationship],
        },
      })
      setRelationshipPerson('')
      setRelationshipKind('friend')
    } catch {
      setRelationshipError(t('profile.relationships.saveError'))
    } finally {
      setIsSavingRelationship(false)
    }
  }

  async function removeRelationship(relationship: PersonRelationship) {
    if (!person) return
    setRelationshipError('')
    try {
      await apiRequest(
        `/people/${person.id}/relationships/${relationship.id}/`,
        { method: 'DELETE' },
      )
      setState({
        status: 'ready',
        person: {
          ...person,
          relationships: person.relationships.filter(
            (item) => item.id !== relationship.id,
          ),
        },
      })
    } catch {
      setRelationshipError(t('profile.relationships.removeError'))
    }
  }

  if (state.status === 'loading') {
    return <div className="profile-loading">{t('profile.loading')}</div>
  }

  if (state.status === 'error' || !person || !fields) {
    return (
      <main className="profile-error">
        <p className="eyebrow">{t('profile.errorEyebrow')}</p>
        <h1>{t('profile.errorTitle')}</h1>
        <p>{t('profile.errorBody')}</p>
        <Link className="primary-button inline" to="/people">
          {t('profile.backToDirectory')}
        </Link>
      </main>
    )
  }

  const tabs: Array<{ id: ProfileTab; label: string; count?: number }> = [
    { id: 'overview', label: t('profile.tabs.overview') },
    {
      id: 'relationships',
      label: t('profile.tabs.relationships'),
      count:
        person.relationships.length +
        person.invitees.length +
        (person.inviter ? 1 : 0),
    },
    {
      id: 'groups',
      label: t('profile.tabs.groups'),
      count: person.groups.length,
    },
    {
      id: 'events',
      label: t('profile.tabs.events'),
      count: person.events_attended.length,
    },
    ...(person.follow_up_history
      ? [
          {
            id: 'followUps' as const,
            label: t('profile.tabs.followUps'),
            count: person.follow_up_history.length,
          },
        ]
      : []),
  ]
  const overviewDetails: Array<[string, string | null | undefined]> = [
    ['profile.fields.email', person.email],
    ['profile.fields.phone', person.phone],
    ['profile.fields.wechatId', person.wechat_id],
    ['profile.fields.suburb', person.suburb],
    ['profile.fields.university', person.university],
    ['profile.fields.occupation', person.occupation],
    ['profile.fields.course', person.course],
    ['profile.fields.birthDate', person.date_of_birth],
    ['profile.fields.homeCountry', person.home_country],
  ]
  if (person.faith_background !== undefined) {
    overviewDetails.push(
      ['profile.fields.faithBackground', person.faith_background],
      [
        'profile.fields.discipleshipStage',
        person.discipleship_stage
          ? t(`profile.stages.${person.discipleship_stage}`)
          : null,
      ],
    )
  }

  return (
    <main className="profile-page">
      <Link className="profile-back" to="/people">
        ← {t('profile.backToDirectory')}
      </Link>

      <header className="profile-hero">
        <div className="profile-avatar" aria-hidden="true">
          {person.photo_url ? (
            <img alt="" src={person.photo_url} />
          ) : (
            initials(person)
          )}
        </div>
        <div className="profile-identity">
          <p className="eyebrow">{t('profile.eyebrow')}</p>
          <h1>{person.full_name}</h1>
          {person.preferred_name ? (
            <p className="profile-preferred-name">
              {t('profile.preferredName', { name: person.preferred_name })}
            </p>
          ) : null}
          <div className="profile-meta">
            <span className={`status-chip status-${person.membership_status}`}>
              {t(`directory.statuses.${person.membership_status}`)}
            </span>
          </div>
        </div>
        <div className="profile-contact-actions">
          {person.phone ? (
            <a className="contact-link" href={`tel:${person.phone}`}>
              {t('directory.call')}
            </a>
          ) : null}
          {person.email ? (
            <a
              className="contact-link secondary"
              href={`mailto:${person.email}`}
            >
              {t('directory.email')}
            </a>
          ) : null}
        </div>
      </header>

      <nav className="profile-tabs" aria-label={t('profile.sections')}>
        {tabs.map((tab) => (
          <button
            aria-label={tab.label}
            aria-selected={activeTab === tab.id}
            className={activeTab === tab.id ? 'active' : undefined}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            role="tab"
            type="button"
          >
            {tab.label}
            {tab.count !== undefined ? <small>{tab.count}</small> : null}
          </button>
        ))}
      </nav>

      {activeTab === 'overview' ? (
        <section className="profile-panel" aria-labelledby="profile-overview">
          <div className="profile-panel-heading">
            <div>
              <p className="eyebrow">{t('profile.overviewEyebrow')}</p>
              <h2 id="profile-overview">{t('profile.overviewTitle')}</h2>
            </div>
            {canEdit && !isEditing ? (
              <button
                className="secondary-button"
                onClick={() => setIsEditing(true)}
                type="button"
              >
                {t('profile.edit')}
              </button>
            ) : null}
          </div>

          {isEditing ? (
            <form className="profile-form" onSubmit={save}>
              <label>
                <span>{t('profile.fields.fullName')}</span>
                <input
                  onChange={(event) =>
                    updateField('full_name', event.target.value)
                  }
                  required
                  value={fields.full_name}
                />
              </label>
              <label>
                <span>{t('profile.fields.preferredName')}</span>
                <input
                  onChange={(event) =>
                    updateField('preferred_name', event.target.value)
                  }
                  value={fields.preferred_name}
                />
              </label>
              <label>
                <span>{t('profile.fields.email')}</span>
                <input
                  onChange={(event) => updateField('email', event.target.value)}
                  type="email"
                  value={fields.email}
                />
              </label>
              <label>
                <span>{t('profile.fields.phone')}</span>
                <input
                  onChange={(event) => updateField('phone', event.target.value)}
                  type="tel"
                  value={fields.phone}
                />
              </label>
              <label>
                <span>{t('profile.fields.wechatId')}</span>
                <input
                  onChange={(event) =>
                    updateField('wechat_id', event.target.value)
                  }
                  value={fields.wechat_id}
                />
              </label>
              <label>
                <span>{t('profile.fields.suburb')}</span>
                <input
                  onChange={(event) =>
                    updateField('suburb', event.target.value)
                  }
                  value={fields.suburb}
                />
              </label>
              <label>
                <span>{t('profile.fields.university')}</span>
                <input
                  onChange={(event) =>
                    updateField('university', event.target.value)
                  }
                  value={fields.university}
                />
              </label>
              <label>
                <span>{t('profile.fields.status')}</span>
                <select
                  onChange={(event) =>
                    updateField(
                      'membership_status',
                      event.target.value as ProfilePerson['membership_status'],
                    )
                  }
                  value={fields.membership_status}
                >
                  {(
                    [
                      'visitor',
                      'newcomer',
                      'regular',
                      'member',
                      'inactive',
                    ] as const
                  ).map((status) => (
                    <option key={status} value={status}>
                      {t(`directory.statuses.${status}`)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>{t('profile.fields.invitedBy')}</span>
                <select
                  onChange={(event) =>
                    updateField('invited_by', event.target.value)
                  }
                  value={fields.invited_by}
                >
                  <option value="">{t('profile.notRecorded')}</option>
                  {people
                    .filter((candidate) => candidate.id !== person.id)
                    .map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>
                        {candidate.full_name}
                      </option>
                    ))}
                </select>
              </label>
              {person.notes !== undefined ? (
                <label className="wide-field">
                  <span>{t('profile.fields.notes')}</span>
                  <textarea
                    onChange={(event) =>
                      updateField('notes', event.target.value)
                    }
                    rows={3}
                    value={fields.notes}
                  />
                </label>
              ) : null}
              {canViewSensitive ? (
                <>
                  <label>
                    <span>{t('profile.fields.faithBackground')}</span>
                    <input
                      onChange={(event) =>
                        updateField('faith_background', event.target.value)
                      }
                      value={fields.faith_background}
                    />
                  </label>
                  <label>
                    <span>{t('profile.fields.discipleshipStage')}</span>
                    <select
                      onChange={(event) =>
                        updateField('discipleship_stage', event.target.value)
                      }
                      value={fields.discipleship_stage}
                    >
                      <option value="">{t('profile.notRecorded')}</option>
                      {(
                        [
                          'pre_evangelism',
                          'evangelism',
                          'conversion',
                          'maturity',
                          'leadership',
                        ] as const
                      ).map((stage) => (
                        <option key={stage} value={stage}>
                          {t(`profile.stages.${stage}`)}
                        </option>
                      ))}
                    </select>
                  </label>
                </>
              ) : null}
              {saveError ? (
                <p className="form-error wide-field" role="alert">
                  {saveError}
                </p>
              ) : null}
              <div className="profile-form-actions wide-field">
                <button
                  className="text-button"
                  onClick={() => {
                    setFields(editFields(person))
                    setIsEditing(false)
                  }}
                  type="button"
                >
                  {t('profile.cancel')}
                </button>
                <button
                  className="primary-button inline"
                  disabled={isSaving}
                  type="submit"
                >
                  {isSaving ? t('profile.saving') : t('profile.save')}
                </button>
              </div>
            </form>
          ) : (
            <dl className="profile-details">
              {overviewDetails.map(([label, value]) => (
                <div key={label}>
                  <dt>{t(label)}</dt>
                  <dd>{value || t('profile.notRecorded')}</dd>
                </div>
              ))}
              {person.notes !== undefined ? (
                <div className="wide-detail">
                  <dt>{t('profile.fields.notes')}</dt>
                  <dd>{person.notes || t('profile.notRecorded')}</dd>
                </div>
              ) : null}
            </dl>
          )}
        </section>
      ) : null}

      {activeTab === 'relationships' ? (
        <section className="profile-panel">
          <div className="profile-panel-heading">
            <div>
              <p className="eyebrow">{t('profile.relationships.eyebrow')}</p>
              <h2>{t('profile.relationships.title')}</h2>
            </div>
          </div>

          <div className="relationship-context">
            <div>
              <span>{t('profile.relationships.invitedBy')}</span>
              <strong>
                {person.inviter?.full_name ?? t('profile.notRecorded')}
              </strong>
            </div>
            <div>
              <span>{t('profile.relationships.peopleInvited')}</span>
              <strong>
                {person.invitees.length
                  ? person.invitees
                      .map((invitee) => invitee.full_name)
                      .join(', ')
                  : t('profile.relationships.none')}
              </strong>
            </div>
          </div>

          {person.relationships.length ? (
            <div className="profile-card-list">
              {person.relationships.map((relationship) => (
                <article
                  className="profile-record-card relationship-card"
                  key={relationship.id}
                >
                  <div className="record-mark" aria-hidden="true">
                    ↔
                  </div>
                  <div>
                    <h3>{relationship.person.full_name}</h3>
                    <p>
                      {t(`profile.relationships.kinds.${relationship.kind}`)}
                    </p>
                  </div>
                  {canEdit ? (
                    <button
                      aria-label={t('profile.relationships.removeNamed', {
                        name: relationship.person.full_name,
                      })}
                      className="text-button"
                      onClick={() => void removeRelationship(relationship)}
                      type="button"
                    >
                      {t('profile.relationships.remove')}
                    </button>
                  ) : null}
                </article>
              ))}
            </div>
          ) : (
            <p className="profile-empty">{t('profile.relationships.empty')}</p>
          )}

          {canEdit ? (
            <form className="relationship-form" onSubmit={addRelationship}>
              <label>
                <span>{t('profile.relationships.person')}</span>
                <select
                  onChange={(event) =>
                    setRelationshipPerson(event.target.value)
                  }
                  required
                  value={relationshipPerson}
                >
                  <option value="">
                    {t('profile.relationships.choosePerson')}
                  </option>
                  {people
                    .filter((candidate) => candidate.id !== person.id)
                    .map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>
                        {candidate.full_name}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                <span>{t('profile.relationships.kind')}</span>
                <select
                  onChange={(event) =>
                    setRelationshipKind(
                      event.target.value as PersonRelationship['kind'],
                    )
                  }
                  value={relationshipKind}
                >
                  {(['friend', 'family', 'spouse', 'guardian'] as const).map(
                    (kind) => (
                      <option key={kind} value={kind}>
                        {t(`profile.relationships.kinds.${kind}`)}
                      </option>
                    ),
                  )}
                </select>
              </label>
              <button
                className="primary-button inline"
                disabled={isSavingRelationship}
                type="submit"
              >
                {isSavingRelationship
                  ? t('profile.relationships.adding')
                  : t('profile.relationships.add')}
              </button>
              {relationshipError ? (
                <p className="form-error" role="alert">
                  {relationshipError}
                </p>
              ) : null}
            </form>
          ) : null}
        </section>
      ) : null}

      {activeTab === 'groups' ? (
        <section className="profile-panel">
          <div className="profile-panel-heading">
            <div>
              <p className="eyebrow">{t('profile.groupsEyebrow')}</p>
              <h2>{t('profile.groupsTitle')}</h2>
            </div>
          </div>
          {person.groups.length ? (
            <div className="profile-card-list">
              {person.groups.map((group) => (
                <article className="profile-record-card" key={group.id}>
                  <div className="record-mark" aria-hidden="true">
                    G
                  </div>
                  <div>
                    <h3>{group.name}</h3>
                    <p>
                      {group.role
                        ? t(`profile.groupRoles.${group.role}`)
                        : t('profile.groupRoles.member')}
                      {group.joined_at
                        ? ` · ${t('profile.joined', {
                            date: formatDate(group.joined_at),
                          })}`
                        : ''}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="profile-empty">{t('profile.noGroups')}</p>
          )}
        </section>
      ) : null}

      {activeTab === 'events' ? (
        <section className="profile-panel">
          <div className="profile-panel-heading">
            <div>
              <p className="eyebrow">{t('profile.eventsEyebrow')}</p>
              <h2>{t('profile.eventsTitle')}</h2>
            </div>
          </div>
          {person.events_attended.length ? (
            <div className="profile-card-list">
              {person.events_attended.map((event) => (
                <article className="profile-record-card" key={event.id}>
                  <time className="record-date" dateTime={event.starts_at}>
                    <strong>
                      {new Intl.DateTimeFormat(undefined, {
                        day: 'numeric',
                      }).format(new Date(event.starts_at))}
                    </strong>
                    {new Intl.DateTimeFormat(undefined, {
                      month: 'short',
                    }).format(new Date(event.starts_at))}
                  </time>
                  <div>
                    <h3>{event.title}</h3>
                    <p>
                      {[formatDate(event.starts_at), event.location]
                        .filter(Boolean)
                        .join(' · ')}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="profile-empty">{t('profile.noEvents')}</p>
          )}
        </section>
      ) : null}

      {activeTab === 'followUps' && person.follow_up_history ? (
        <section className="profile-panel">
          <div className="profile-panel-heading">
            <div>
              <p className="eyebrow">{t('profile.followUpsEyebrow')}</p>
              <h2>{t('profile.followUpsTitle')}</h2>
            </div>
          </div>
          {person.follow_up_history.length ? (
            <div className="profile-card-list">
              {person.follow_up_history.map((followUp) => (
                <article className="profile-record-card" key={followUp.id}>
                  <div className="record-mark" aria-hidden="true">
                    ↗
                  </div>
                  <div>
                    <div className="record-title-line">
                      <h3>{t(`profile.sources.${followUp.source}`)}</h3>
                      <span className="group-chip">
                        {t(`profile.followUpStatuses.${followUp.status}`)}
                      </span>
                    </div>
                    <p>
                      {followUp.assigned_to
                        ? t('profile.assignedTo', {
                            name: followUp.assigned_to,
                          })
                        : t('profile.unassigned')}
                    </p>
                    {followUp.outcome ? (
                      <p className="record-outcome">{followUp.outcome}</p>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="profile-empty">{t('profile.noFollowUps')}</p>
          )}
        </section>
      ) : null}
    </main>
  )
}
