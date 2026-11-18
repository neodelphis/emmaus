import { useState } from 'react'

export function useHashToken(): string | null {
  const [token] = useState(() => {
    const raw = window.location.hash.replace(/^#/, '')
    if (!raw) return ''
    try {
      return decodeURIComponent(raw)
    } catch {
      return raw
    }
  })
  return token || null
}

export function clearHash(): void {
  window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
}
