import type {
  AdminUser,
  DaySavePayload,
  OpeningHours,
  PeriodView,
  Volunteer,
  VolunteerAccess,
  VolunteerCreated,
  VolunteerPayload,
  WeekView,
} from './types'

export class ApiError extends Error {
  status: number
  fields?: string[]

  constructor(message: string, status: number, fields?: string[]) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fields = fields
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  let response: Response
  try {
    response = await fetch(path, {
      credentials: 'include',
      ...init,
      headers,
    })
  } catch {
    throw new ApiError('Le serveur est injoignable. Vérifiez votre connexion.', 0)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const data = (await response.json().catch(() => null)) as
    | { detail?: string; fields?: string[] }
    | null

  if (!response.ok) {
    if (response.status === 401 && path.startsWith('/api/admin')) {
      window.dispatchEvent(new Event('admin:unauthorized'))
    }
    throw new ApiError(
      data?.detail ?? 'Une erreur inattendue est survenue.',
      response.status,
      data?.fields,
    )
  }

  return data as T
}

function json(body: unknown): RequestInit {
  return { method: 'POST', body: JSON.stringify(body) }
}

function volunteerHeaders(token: string): HeadersInit {
  return { 'X-Volunteer-Token': token }
}

export const api = {
  // Administration — authentification
  login(email: string, password: string) {
    return request<AdminUser>('/api/admin/auth/login', json({ email, password }))
  },
  logout() {
    return request<void>('/api/admin/auth/logout', { method: 'POST' })
  },
  me() {
    return request<AdminUser>('/api/admin/auth/me')
  },
  forgotPassword(email: string) {
    return request<{ message: string }>(
      '/api/admin/auth/forgot-password',
      json({ email }),
    )
  },
  resetPassword(token: string, password: string) {
    return request<void>(
      '/api/admin/auth/reset-password',
      json({ token, password }),
    )
  },
  listAdministrators() {
    return request<AdminUser[]>('/api/admin/auth/administrators')
  },
  createAdministrator(email: string, password: string) {
    return request<AdminUser>(
      '/api/admin/auth/administrators',
      json({ email, password }),
    )
  },

  // Administration — bénévoles
  listVolunteers() {
    return request<Volunteer[]>('/api/admin/volunteers')
  },
  createVolunteer(payload: { name: string; email?: string | null }) {
    return request<VolunteerCreated>('/api/admin/volunteers', json(payload))
  },
  updateVolunteer(id: string, payload: VolunteerPayload) {
    return request<Volunteer>(`/api/admin/volunteers/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },
  deleteVolunteer(id: string) {
    return request<void>(`/api/admin/volunteers/${id}`, { method: 'DELETE' })
  },
  getVolunteerLink(id: string) {
    return request<{ link: string }>(`/api/admin/volunteers/${id}/link`)
  },
  revokeVolunteerLink(id: string) {
    return request<void>(`/api/admin/volunteers/${id}/link/revoke`, {
      method: 'POST',
    })
  },
  regenerateVolunteerLink(id: string) {
    return request<{ link: string }>(
      `/api/admin/volunteers/${id}/link/regenerate`,
      { method: 'POST' },
    )
  },
  sendVolunteerLink(id: string) {
    return request<void>(`/api/admin/volunteers/${id}/link/send`, {
      method: 'POST',
    })
  },
  excludeVolunteerMeal(id: string, date: string) {
    return request<void>(`/api/admin/volunteers/${id}/meal-exclusions/${date}`, {
      method: 'PUT',
    })
  },
  includeVolunteerMeal(id: string, date: string) {
    return request<void>(`/api/admin/volunteers/${id}/meal-exclusions/${date}`, {
      method: 'DELETE',
    })
  },

  // Administration — semaine et horaires
  getWeek(periodStart?: string, includeInactive = false) {
    const params = new URLSearchParams()
    if (periodStart) params.set('period_start', periodStart)
    if (includeInactive) params.set('include_inactive', 'true')
    const query = params.toString()
    return request<WeekView>(`/api/admin/week${query ? `?${query}` : ''}`)
  },
  getOpeningHours() {
    return request<OpeningHours[]>('/api/admin/opening-hours')
  },
  updateOpeningHours(hours: OpeningHours[]) {
    return request<OpeningHours[]>('/api/admin/opening-hours', {
      method: 'PUT',
      body: JSON.stringify({ hours }),
    })
  },

  // Bénévole
  getVolunteerAccess(token: string) {
    return request<VolunteerAccess>('/api/volunteer', {
      headers: volunteerHeaders(token),
    })
  },
  saveVolunteerPeriod(token: string, periodStart: string, days: DaySavePayload[]) {
    return request<PeriodView>(`/api/volunteer/periods/${periodStart}`, {
      method: 'PUT',
      headers: volunteerHeaders(token),
      body: JSON.stringify({ days }),
    })
  },
}
