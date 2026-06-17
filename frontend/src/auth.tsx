import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getCurrentUser, login as loginRequest, logout as logoutRequest, setAuthToken } from './api'
import type { AuthUser } from './types'

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)
const STORAGE_KEY = 'crewlink_auth_token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = window.localStorage.getItem(STORAGE_KEY)
    if (!token) {
      setLoading(false)
      return
    }

    setAuthToken(token)
    getCurrentUser()
      .then(setUser)
      .catch(() => {
        window.localStorage.removeItem(STORAGE_KEY)
        setAuthToken(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (username: string, password: string) => {
        const response = await loginRequest(username, password)
        window.localStorage.setItem(STORAGE_KEY, response.token)
        setAuthToken(response.token)
        setUser(response.user)
      },
      logout: async () => {
        try {
          await logoutRequest()
        } catch {
          // Clear the local session even if the server session has expired.
        }
        window.localStorage.removeItem(STORAGE_KEY)
        setAuthToken(null)
        setUser(null)
      },
    }),
    [loading, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
