export type DayKind = 'unavailable' | 'all_day' | 'slot'
export type SavedDayKind = 'all_day' | 'slot'
export type SiteCode = 'vaire' | 'les-essarts'

export interface Site {
  code: SiteCode
  name: string
}

export interface SiteWithHours extends Site {
  opening_hours: OpeningHours[]
}

export interface DayAnswer {
  kind: SavedDayKind
  start: string | null
  end: string | null
  site: SiteCode | null
}

export interface DayView {
  date: string
  weekday: number
  editable: boolean
  answer: DayAnswer | null
  suggestion: DayAnswer | null
}

export interface PeriodView {
  start: string
  end: string
  submitted: boolean
  submitted_at: string | null
  days: DayView[]
}

export interface OpeningHours {
  weekday: number
  open: string
  close: string
}

export interface VolunteerAccess {
  volunteer_name: string
  today: string
  default_site: SiteCode
  sites: SiteWithHours[]
  periods: PeriodView[]
}

export type AdminRole = 'admin' | 'super_admin'

export interface AdminUser {
  id: string
  email: string
  first_name: string | null
  last_name: string | null
  role: AdminRole
  gender: 'homme' | 'femme' | null
  last_site: SiteCode | null
}

export interface Volunteer {
  id: string
  name: string
  email: string | null
  gender: 'homme' | 'femme' | null
  default_site: SiteCode | null
  is_active: boolean
  has_link: boolean
  created_at: string
}

export interface VolunteerCreated extends Volunteer {
  link: string
}

export type WeekStatus = 'unanswered' | 'unavailable' | 'all_day' | 'slot'

export interface WeekDay {
  date: string
  weekday: number
  status: WeekStatus
  start: string | null
  end: string | null
  meal_excluded: boolean
}

export interface WeekVolunteer {
  id: string
  name: string
  email: string | null
  is_active: boolean
  submitted: boolean
  days: WeekDay[]
}

export interface PeriodOption {
  start: string
  end: string
  is_current: boolean
}

export interface WeekView {
  period_start: string
  period_end: string
  today: string
  site: SiteCode
  opening_hours: OpeningHours[]
  options: PeriodOption[]
  volunteers: WeekVolunteer[]
}

export interface DaySavePayload {
  date: string
  kind: DayKind
  start?: string
  end?: string
  site?: SiteCode
}

export interface VolunteerPayload {
  name?: string
  email?: string | null
  gender?: 'homme' | 'femme'
  default_site?: SiteCode
  is_active?: boolean
}
