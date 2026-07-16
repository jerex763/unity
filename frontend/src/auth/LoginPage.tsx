import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { useAuth } from './useAuth'

export function LoginPage() {
  const { t } = useTranslation()
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [churchId, setChurchId] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await login({
        username,
        password,
        ...(churchId ? { church_id: Number(churchId) } : {}),
      })
      navigate('/', { replace: true })
    } catch {
      setError(t('auth.invalid'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-intro" aria-labelledby="login-brand">
        <div className="brand-mark" aria-hidden="true">
          U
        </div>
        <p className="eyebrow">{t('appName')}</p>
        <h1 id="login-brand">{t('appTagline')}</h1>
        <div className="growth-line" aria-hidden="true" />
      </section>

      <section className="login-card" aria-labelledby="login-title">
        <p className="eyebrow">{t('appName')}</p>
        <h2 id="login-title">{t('auth.signIn')}</h2>
        <form onSubmit={handleSubmit}>
          <label>
            <span>{t('auth.username')}</span>
            <input
              autoComplete="username"
              name="username"
              onChange={(event) => setUsername(event.target.value)}
              required
              value={username}
            />
          </label>
          <label>
            <span>{t('auth.password')}</span>
            <input
              autoComplete="current-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          <label>
            <span>{t('auth.churchId')}</span>
            <input
              inputMode="numeric"
              min="1"
              name="churchId"
              onChange={(event) => setChurchId(event.target.value)}
              type="number"
              value={churchId}
            />
            <small>{t('auth.churchIdHint')}</small>
          </label>
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}
          <button
            className="primary-button"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? t('auth.signingIn') : t('auth.signIn')}
          </button>
        </form>
      </section>
    </main>
  )
}
