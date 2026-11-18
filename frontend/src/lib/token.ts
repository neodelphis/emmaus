import { useEffect, useState } from 'react'

function readHashToken(): string {
  const raw = window.location.hash.replace(/^#/, '')
  if (!raw) return ''
  try {
    return decodeURIComponent(raw)
  } catch {
    return raw
  }
}

export function useHashToken(): string | null {
  const [token, setToken] = useState(readHashToken)

  useEffect(() => {
    const handleHashChange = () => setToken(readHashToken())
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  return token || null
}

export function clearHash(): void {
  window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
}
