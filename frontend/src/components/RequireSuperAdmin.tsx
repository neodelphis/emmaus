import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth'

export function RequireSuperAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (!user || user.role !== 'super_admin') {
    return <Navigate to="/admin/semaine" replace />
  }
  return <>{children}</>
}
