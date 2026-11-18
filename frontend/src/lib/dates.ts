const LOCALE = 'fr-FR'

export const WEEKDAYS = [
  { value: 1, label: 'Mardi', short: 'Mar.' },
  { value: 2, label: 'Mercredi', short: 'Mer.' },
  { value: 3, label: 'Jeudi', short: 'Jeu.' },
  { value: 4, label: 'Vendredi', short: 'Ven.' },
  { value: 5, label: 'Samedi', short: 'Sam.' },
] as const

const longDayFormatter = new Intl.DateTimeFormat(LOCALE, {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
})

const shortDateFormatter = new Intl.DateTimeFormat(LOCALE, {
  day: 'numeric',
  month: 'short',
})

const dayMonthFormatter = new Intl.DateTimeFormat(LOCALE, {
  day: 'numeric',
  month: 'long',
})

const dateTimeFormatter = new Intl.DateTimeFormat(LOCALE, {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'Europe/Paris',
})

export function parseIsoDate(iso: string): Date {
  return new Date(`${iso}T12:00:00`)
}

export function weekdayLabel(weekday: number): string {
  return WEEKDAYS.find((day) => day.value === weekday)?.label ?? ''
}

export function weekdayShort(weekday: number): string {
  return WEEKDAYS.find((day) => day.value === weekday)?.short ?? ''
}

export function formatDayDate(iso: string): string {
  return longDayFormatter.format(parseIsoDate(iso))
}

export function formatShortDate(iso: string): string {
  return shortDateFormatter.format(parseIsoDate(iso))
}

export function formatDayMonth(iso: string): string {
  return dayMonthFormatter.format(parseIsoDate(iso))
}

export function formatPeriodRange(start: string, end: string): string {
  const startDate = parseIsoDate(start)
  const endDate = parseIsoDate(end)
  const sameMonth =
    startDate.getMonth() === endDate.getMonth() &&
    startDate.getFullYear() === endDate.getFullYear()
  const monthFormatter = new Intl.DateTimeFormat(LOCALE, { month: 'long' })
  const year = endDate.getFullYear()

  if (sameMonth) {
    return `du ${startDate.getDate()} au ${endDate.getDate()} ${monthFormatter.format(
      endDate,
    )} ${year}`
  }
  return `du ${formatShortDate(start)} au ${formatShortDate(end)} ${year}`
}

export function formatPeriodChip(start: string, today: string): string {
  const current = currentPeriodStart(today)
  if (start === current) return 'Cette semaine'
  const next = addDays(current, 7)
  if (start === next) return 'La semaine prochaine'
  return `Semaine du ${formatShortDate(start)}`
}

export function formatDateTime(iso: string): string {
  return dateTimeFormatter.format(new Date(iso))
}

export function formatTimeRange(start: string | null, end: string | null): string {
  if (!start || !end) return ''
  return `${start} – ${end}`
}

export function currentPeriodStart(today: string): string {
  const date = parseIsoDate(today)
  const offset = (date.getDay() - 2 + 7) % 7
  date.setDate(date.getDate() - offset)
  return toIsoDate(date)
}

export function addDays(iso: string, days: number): string {
  const date = parseIsoDate(iso)
  date.setDate(date.getDate() + days)
  return toIsoDate(date)
}

export function toIsoDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function minutesOf(time: string): number {
  const [hours, minutes] = time.split(':').map(Number)
  return hours * 60 + minutes
}

export function timeFromMinutes(total: number): string {
  const hours = Math.floor(total / 60)
  const minutes = total % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

export function isHalfHour(time: string): boolean {
  const minutes = minutesOf(time)
  return Number.isFinite(minutes) && minutes % 30 === 0
}
