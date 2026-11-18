import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  Clock3,
  HelpCircle,
  RefreshCw,
  Sun,
  UserRoundX,
  Users,
  XCircle,
} from 'lucide-react'
import { api, ApiError } from '../api'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { PageHeader } from '../components/ui/PageHeader'
import { cn } from '../lib/cn'
import {
  WEEKDAYS,
  addDays,
  formatDayDate,
  formatPeriodRange,
  formatShortDate,
  formatTimeRange,
  weekdayShort,
} from '../lib/dates'
import type { WeekStatus, WeekVolunteer, WeekView, WeekDay } from '../types'

const statusStyles: Record<WeekStatus, string> = {
  all_day: 'border-brand-200 bg-brand-50 text-brand-800',
  slot: 'border-sky-200 bg-sky-50 text-sky-800',
  unavailable: 'border-stone-200 bg-stone-50 text-stone-500',
  unanswered: 'border-amber-200 bg-amber-50 text-amber-800',
}

function statusLabel(day: WeekDay): string {
  if (day.status === 'all_day') return 'Toute la journée'
  if (day.status === 'slot') return formatTimeRange(day.start, day.end)
  if (day.status === 'unavailable') return 'Indisponible'
  return 'Sans réponse'
}

function StatusIcon({ status }: { status: WeekStatus }) {
  if (status === 'all_day') return <Sun className="h-3.5 w-3.5" aria-hidden />
  if (status === 'slot') return <Clock3 className="h-3.5 w-3.5" aria-hidden />
  if (status === 'unavailable') return <XCircle className="h-3.5 w-3.5" aria-hidden />
  return <HelpCircle className="h-3.5 w-3.5" aria-hidden />
}

function DayCell({ day, compact }: { day: WeekDay; compact: boolean }) {
  return (
    <div
      className={cn(
        'flex flex-col items-start gap-1 rounded-xl border px-2.5 py-2',
        statusStyles[day.status],
        compact && 'min-h-[4.5rem]',
      )}
    >
      <span className="text-[11px] font-semibold uppercase tracking-wide opacity-70">
        {weekdayShort(day.weekday)}
      </span>
      <span className="inline-flex items-center gap-1 text-xs font-medium leading-tight">
        <StatusIcon status={day.status} />
        {statusLabel(day)}
      </span>
    </div>
  )
}

function VolunteerWeekCard({
  volunteer,
  visibleDays,
}: {
  volunteer: WeekVolunteer
  visibleDays: WeekDay[]
}) {
  const initials = volunteer.name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')

  return (
    <Card className="overflow-visible">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-stone-100 px-4 py-3.5">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-800">
            {initials || '?'}
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="truncate font-semibold text-stone-900">{volunteer.name}</p>
              {!volunteer.is_active && <Badge tone="stone">Désactivé</Badge>}
            </div>
            <p className="truncate text-xs text-stone-400">
              {volunteer.email || 'Sans courriel'}
            </p>
          </div>
        </div>
        {volunteer.submitted ? (
          <Badge tone="green">
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
            Réponse reçue
          </Badge>
        ) : (
          <Badge tone="amber">
            <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
            Sans réponse
          </Badge>
        )}
      </div>

      {!volunteer.submitted && (
        <div className="flex items-start gap-2 border-b border-amber-100 bg-amber-50/60 px-4 py-2.5 text-xs leading-relaxed text-amber-900">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          <p>
            Aucune réponse n'a été soumise pour cette période. Ce n'est pas la même chose
            qu'une journée laissée indisponible.
          </p>
        </div>
      )}

      <div
        className={cn(
          'grid gap-2 p-3 sm:p-4',
          visibleDays.length === 1
            ? 'grid-cols-1'
            : visibleDays.length === 2
              ? 'grid-cols-2'
              : 'grid-cols-2 sm:grid-cols-5',
        )}
      >
        {visibleDays.map((day) => (
          <DayCell key={day.date} day={day} compact />
        ))}
      </div>
    </Card>
  )
}

export function AdminWeekPage() {
  const [requestedPeriod, setRequestedPeriod] = useState<string | null>(null)
  const [includeInactive, setIncludeInactive] = useState(false)
  const [data, setData] = useState<WeekView | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dayFilter, setDayFilter] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const week = await api.getWeek(requestedPeriod ?? undefined, includeInactive)
      setData(week)
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : 'La semaine n’a pas pu être chargée.',
      )
    } finally {
      setLoading(false)
    }
  }, [requestedPeriod, includeInactive])

  useEffect(() => {
    void load()
  }, [load])

  const weekDays = useMemo(() => {
    if (!data) return []
    return WEEKDAYS.map((weekday, index) => ({
      date: addDays(data.period_start, index),
      weekday: weekday.value,
    }))
  }, [data])

  const visibleDays = useMemo(() => {
    if (!data) return []
    const source = data.volunteers[0]?.days
    return source
      ? dayFilter
        ? source.filter((day) => day.weekday === dayFilter)
        : source
      : []
  }, [data, dayFilter])

  const filteredVolunteers = useMemo(() => {
    if (!data) return []
    return [...data.volunteers].sort((left, right) => {
      if (left.submitted !== right.submitted) return left.submitted ? 1 : -1
      return left.name.localeCompare(right.name, 'fr')
    })
  }, [data])

  const answered = data?.volunteers.filter((volunteer) => volunteer.submitted).length ?? 0
  const total = data?.volunteers.length ?? 0
  const unanswered = total - answered
  const periodLabel = data ? formatPeriodRange(data.period_start, data.period_end) : ''

  return (
    <div className="space-y-5">
      <PageHeader
        title="Vue de la semaine"
        description={periodLabel ? `Semaine ${periodLabel}` : 'Chargement de la semaine…'}
        actions={
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
            <select
              className="input w-full bg-white py-2 text-sm sm:w-auto"
              aria-label="Choisir une période"
              value={requestedPeriod ?? data?.period_start ?? ''}
              onChange={(event) => setRequestedPeriod(event.target.value)}
            >
              {(data?.options ?? []).map((option) => (
                <option key={option.start} value={option.start}>
                  {formatShortDate(option.start)} – {formatShortDate(option.end)}
                  {option.is_current ? ' (en cours)' : ''}
                </option>
              ))}
            </select>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void load()}
              leftIcon={<RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />}
              aria-label="Actualiser la semaine"
            >
              <span className="hidden sm:inline">Actualiser</span>
            </Button>
          </div>
        }
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-stone-600">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-stone-300 text-brand-700 focus:ring-brand-600"
            checked={includeInactive}
            onChange={(event) => setIncludeInactive(event.target.checked)}
          />
          Inclure les bénévoles désactivés
        </label>
        {loading && data && (
          <span className="inline-flex items-center gap-1.5 text-xs text-stone-400">
            <RefreshCw className="h-3.5 w-3.5 animate-spin" aria-hidden />
            Mise à jour…
          </span>
        )}
      </div>

      {error ? (
        <Card className="p-6 text-center">
          <AlertTriangle className="mx-auto h-7 w-7 text-red-500" aria-hidden />
          <p className="mt-2 text-sm text-stone-600">{error}</p>
          <Button className="mt-4" variant="secondary" onClick={() => void load()}>
            Réessayer
          </Button>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-2 sm:gap-3">
            <div className="card flex flex-col items-center justify-center gap-1 p-3 text-center sm:flex-row sm:justify-start sm:gap-3 sm:p-4 sm:text-left">
              <span className="hidden h-10 w-10 items-center justify-center rounded-xl bg-stone-100 text-stone-600 sm:flex">
                <Users className="h-5 w-5" aria-hidden />
              </span>
              <div>
                <p className="text-xl font-bold leading-none text-stone-900 sm:text-2xl">{total}</p>
                <p className="mt-1 text-[10px] leading-tight text-stone-500 sm:text-xs">
                  bénévoles affichés
                </p>
              </div>
            </div>
            <div className="card flex flex-col items-center justify-center gap-1 p-3 text-center sm:flex-row sm:justify-start sm:gap-3 sm:p-4 sm:text-left">
              <span className="hidden h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700 sm:flex">
                <CheckCircle2 className="h-5 w-5" aria-hidden />
              </span>
              <div>
                <p className="text-xl font-bold leading-none text-stone-900 sm:text-2xl">{answered}</p>
                <p className="mt-1 text-[10px] leading-tight text-stone-500 sm:text-xs">
                  réponses reçues
                </p>
              </div>
            </div>
            <div className="card flex flex-col items-center justify-center gap-1 p-3 text-center sm:flex-row sm:justify-start sm:gap-3 sm:p-4 sm:text-left">
              <span className="hidden h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-700 sm:flex">
                <UserRoundX className="h-5 w-5" aria-hidden />
              </span>
              <div>
                <p className="text-xl font-bold leading-none text-stone-900 sm:text-2xl">{unanswered}</p>
                <p className="mt-1 text-[10px] leading-tight text-stone-500 sm:text-xs">
                  sans réponse
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-stone-400">
              <CalendarDays className="h-3.5 w-3.5" aria-hidden />
              Filtrer par jour
            </span>
            <button
              type="button"
              onClick={() => setDayFilter(null)}
              className={cn(
                'rounded-full border px-3 py-1 text-xs font-medium transition',
                dayFilter === null
                  ? 'border-brand-700 bg-brand-700 text-white'
                  : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50',
              )}
            >
              Tous
            </button>
            {weekDays.map((day) => (
              <button
                key={day.date}
                type="button"
                onClick={() => setDayFilter(day.weekday)}
                className={cn(
                  'rounded-full border px-3 py-1 text-xs font-medium transition',
                  dayFilter === day.weekday
                    ? 'border-brand-700 bg-brand-700 text-white'
                    : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50',
                )}
              >
                {weekdayShort(day.weekday).replace('.', '')}
              </button>
            ))}
          </div>

          {filteredVolunteers.length === 0 ? (
            <EmptyState
              icon={Users}
              title="Aucun bénévole à afficher"
              description="Ajoutez un bénévole pour commencer à recevoir des disponibilités."
              action={
                <Link
                  to="/admin/benevoles"
                  className="inline-flex rounded-xl bg-brand-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-800"
                >
                  Gérer les bénévoles
                </Link>
              }
            />
          ) : (
            <div className="space-y-3">
              {filteredVolunteers.map((volunteer) => {
                const days = dayFilter
                  ? volunteer.days.filter((day) => day.weekday === dayFilter)
                  : volunteer.days
                return (
                  <VolunteerWeekCard
                    key={volunteer.id}
                    volunteer={volunteer}
                    visibleDays={days.length > 0 ? days : visibleDays}
                  />
                )
              })}
            </div>
          )}

          {visibleDays.length === 0 && data && data.volunteers.length > 0 && (
            <p className="text-center text-xs text-stone-400">
              Aucun jour à afficher pour ce filtre.
            </p>
          )}

          <p className="text-center text-xs text-stone-400">
            {data?.volunteers[0]
              ? `Semaine du ${formatDayDate(data.volunteers[0].days[0].date)} au ${formatDayDate(
                  data.volunteers[0].days[4].date,
                )}`
              : null}
          </p>
        </>
      )}
    </div>
  )
}
