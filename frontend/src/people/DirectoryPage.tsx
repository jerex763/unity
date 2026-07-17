import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { apiRequest } from '../api/client'
import type { DirectoryPerson } from './types'

type LoadState =
  | { status: 'loading'; people: DirectoryPerson[] }
  | { status: 'ready'; people: DirectoryPerson[] }
  | { status: 'error'; people: DirectoryPerson[] }

function initials(person: DirectoryPerson) {
  return person.full_name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

export function DirectoryPage() {
  const { t } = useTranslation()
  const [loadState, setLoadState] = useState<LoadState>({
    status: 'loading',
    people: [],
  })
  const [reloadKey, setReloadKey] = useState(0)
  const [search, setSearch] = useState('')
  const [membershipStatus, setMembershipStatus] = useState('')
  const [groupId, setGroupId] = useState('')
  const [university, setUniversity] = useState('')

  useEffect(() => {
    let active = true
    void apiRequest<DirectoryPerson[]>('/people/')
      .then((people) => {
        if (active) setLoadState({ status: 'ready', people })
      })
      .catch(() => {
        if (active) setLoadState({ status: 'error', people: [] })
      })
    return () => {
      active = false
    }
  }, [reloadKey])

  const groups = useMemo(() => {
    const unique = new Map<number, string>()
    loadState.people.forEach((person) =>
      person.groups.forEach((group) => unique.set(group.id, group.name)),
    )
    return [...unique].sort((left, right) => left[1].localeCompare(right[1]))
  }, [loadState.people])

  const universities = useMemo(
    () =>
      [
        ...new Set(
          loadState.people
            .map((person) => person.university)
            .filter((value): value is string => Boolean(value)),
        ),
      ].sort((left, right) => left.localeCompare(right)),
    [loadState.people],
  )

  const visiblePeople = useMemo(() => {
    const query = search.trim().toLocaleLowerCase()
    return loadState.people.filter((person) => {
      const matchesSearch =
        !query ||
        person.full_name.toLocaleLowerCase().includes(query) ||
        person.preferred_name?.toLocaleLowerCase().includes(query)
      const matchesStatus =
        !membershipStatus || person.membership_status === membershipStatus
      const matchesGroup =
        !groupId || person.groups.some((group) => String(group.id) === groupId)
      const matchesUniversity = !university || person.university === university
      return matchesSearch && matchesStatus && matchesGroup && matchesUniversity
    })
  }, [groupId, loadState.people, membershipStatus, search, university])

  const hasFilters = Boolean(
    search || membershipStatus || groupId || university,
  )

  function clearFilters() {
    setSearch('')
    setMembershipStatus('')
    setGroupId('')
    setUniversity('')
  }

  function retry() {
    setLoadState({ status: 'loading', people: [] })
    setReloadKey((value) => value + 1)
  }

  return (
    <main className="directory-page">
      <header className="directory-heading">
        <div>
          <p className="eyebrow">{t('directory.eyebrow')}</p>
          <h1>{t('directory.title')}</h1>
          <p>{t('directory.intro')}</p>
        </div>
        <span className="directory-total" aria-live="polite">
          <strong>{visiblePeople.length}</strong>
          {t('directory.peopleCount', { count: visiblePeople.length })}
        </span>
      </header>

      <section
        className="directory-controls"
        aria-label={t('directory.filters')}
      >
        <div className="search-field">
          <label className="visually-hidden" htmlFor="directory-search">
            {t('directory.searchLabel')}
          </label>
          <span className="search-icon" aria-hidden="true">
            ⌕
          </span>
          <input
            id="directory-search"
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t('directory.searchPlaceholder')}
            type="search"
            value={search}
          />
        </div>

        <div className="filter-row">
          <label htmlFor="directory-status">
            <span>{t('directory.status')}</span>
            <select
              aria-label={t('directory.status')}
              id="directory-status"
              onChange={(event) => setMembershipStatus(event.target.value)}
              value={membershipStatus}
            >
              <option value="">{t('directory.allStatuses')}</option>
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

          <label htmlFor="directory-group">
            <span>{t('directory.group')}</span>
            <select
              aria-label={t('directory.group')}
              id="directory-group"
              onChange={(event) => setGroupId(event.target.value)}
              value={groupId}
            >
              <option value="">{t('directory.allGroups')}</option>
              {groups.map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </label>

          <label htmlFor="directory-university">
            <span>{t('directory.university')}</span>
            <select
              aria-label={t('directory.university')}
              id="directory-university"
              onChange={(event) => setUniversity(event.target.value)}
              value={university}
            >
              <option value="">{t('directory.allUniversities')}</option>
              {universities.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>

          {hasFilters ? (
            <button
              className="clear-filters"
              onClick={clearFilters}
              type="button"
            >
              {t('directory.clear')}
            </button>
          ) : null}
        </div>
      </section>

      {loadState.status === 'loading' ? (
        <section className="directory-list" aria-label={t('directory.loading')}>
          {[0, 1, 2].map((item) => (
            <div className="person-row skeleton-row" key={item} />
          ))}
        </section>
      ) : null}

      {loadState.status === 'error' ? (
        <section className="directory-message" role="alert">
          <div className="message-mark" aria-hidden="true">
            !
          </div>
          <h2>{t('directory.errorTitle')}</h2>
          <p>{t('directory.errorBody')}</p>
          <button
            className="primary-button inline"
            onClick={retry}
            type="button"
          >
            {t('directory.tryAgain')}
          </button>
        </section>
      ) : null}

      {loadState.status === 'ready' && visiblePeople.length === 0 ? (
        <section className="directory-message">
          <div className="message-mark leaf" aria-hidden="true">
            ·
          </div>
          <h2>
            {hasFilters
              ? t('directory.noMatchesTitle')
              : t('directory.emptyTitle')}
          </h2>
          <p>
            {hasFilters
              ? t('directory.noMatchesBody')
              : t('directory.emptyBody')}
          </p>
        </section>
      ) : null}

      {loadState.status === 'ready' && visiblePeople.length > 0 ? (
        <section className="directory-list" aria-label={t('directory.results')}>
          {visiblePeople.map((person) => (
            <article className="person-row" key={person.id}>
              <div className="person-avatar" aria-hidden="true">
                {person.photo_url ? (
                  <img alt="" src={person.photo_url} />
                ) : (
                  initials(person)
                )}
              </div>
              <div className="person-summary">
                <div className="person-name-line">
                  <h2>{person.full_name}</h2>
                  <span
                    className={`status-chip status-${person.membership_status}`}
                  >
                    {t(`directory.statuses.${person.membership_status}`)}
                  </span>
                </div>
                <p>
                  {[person.university, person.suburb]
                    .filter(Boolean)
                    .join(' · ') || t('directory.noContext')}
                </p>
                {person.groups.length > 0 ? (
                  <div className="person-groups">
                    {person.groups.slice(0, 2).map((group) => (
                      <span className="group-chip" key={group.id}>
                        {group.name}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
              <div className="person-actions">
                {person.phone ? (
                  <a
                    aria-label={t('directory.callPerson', {
                      name: person.full_name,
                    })}
                    className="contact-link"
                    href={`tel:${person.phone}`}
                  >
                    {t('directory.call')}
                  </a>
                ) : null}
                {person.email ? (
                  <a
                    aria-label={t('directory.emailPerson', {
                      name: person.full_name,
                    })}
                    className="contact-link secondary"
                    href={`mailto:${person.email}`}
                  >
                    {t('directory.email')}
                  </a>
                ) : null}
              </div>
            </article>
          ))}
        </section>
      ) : null}
    </main>
  )
}
