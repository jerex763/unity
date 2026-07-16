import { createContext } from 'react'

import type { LoginInput, SessionPayload } from './types'

export type AuthContextValue = {
  isLoading: boolean
  session: SessionPayload | null
  login: (input: LoginInput) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
