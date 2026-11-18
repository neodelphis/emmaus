import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, ApiError } from './api'
import type { AdminUser } from './types'

interface AuthContextValue {
  user: AdminUser | null
  loading: boolean
  signIn: (user: AdminUser) => void
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AdminUser | null>(null)
  const [loading, setLoading] = useState(
    () => !window.location.pathname.startsWith('/b'),
  )

  useEffect(() => {
    if (window.location.pathname.startsWith('/b')) return
    let active = true
    api
      .me()
      .then((admin) => {
        if (active) setUser(admin)
      })
      .catch((error: unknown) => {
        if (!(error instanceof ApiError) || error.status !== 401) {
          console.error(error)
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const handleUnauthorized = () => setUser(null)
    window.addEventListener('admin:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('admin:unauthorized', handleUnauthorized)
  }, [])

  const signIn = useCallback((admin: AdminUser) => setUser(admin), [])

  const signOut = useCallback(async () => {
    try {
      await api.logout()
    } catch {
      // La session est considérée fermée même si le serveur est injoignable.
    }
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, signIn, signOut }),
    [user, loading, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// Le hook accompagne volontairement son provider dans ce module.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('useAuth doit être utilisé dans AuthProvider.')
  }
  return value
}
