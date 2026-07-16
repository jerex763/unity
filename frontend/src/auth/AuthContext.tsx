import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react'

import { ApiError, apiRequest } from '../api/client'
import { AuthContext } from './auth-context'
import type { LoginInput, SessionPayload } from './types'

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<SessionPayload | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true
    void apiRequest<SessionPayload>('/auth/session/')
      .then((payload) => {
        if (active) setSession(payload)
      })
      .catch((error: unknown) => {
        if (
          active &&
          (!(error instanceof ApiError) || ![401, 403].includes(error.status))
        ) {
          console.error(error)
        }
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (input: LoginInput) => {
    const payload = await apiRequest<SessionPayload>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify(input),
    })
    setSession(payload)
  }, [])

  const logout = useCallback(async () => {
    await apiRequest<void>('/auth/logout/', { method: 'POST' })
    setSession(null)
  }, [])

  const value = useMemo(
    () => ({ isLoading, session, login, logout }),
    [isLoading, login, logout, session],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
