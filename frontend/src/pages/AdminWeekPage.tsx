import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  RefreshCw,
  Users,
} from 'lucide-react'
import { api, ApiError } from '../api'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { PageHeader } from '../components/ui/PageHeader'
import {
  WeekPlanning,
  type PlanningDay,
  type PlanningEntry,
} from '../components/admin/WeekPlanning'
import { cn } from '../lib/cn'
import {
  WEEKDAYS,
  addDays,
  formatPeriodRange,
  formatShortDate,
  parseIsoDate,
  weekdayShort,
} from '../lib/dates'
import type { WeekView } from '../types'

function availableCount(day: PlanningDay): number {
  return day.allDay.length + day.slots.length
}

export function AdminWeekPage() {
  const [requestedPeriod, setRequestedPeriod] = useState<string | null>(null)
  const [includeInactive, setIncludeInactive] = useState(false)
  const [data, setData] = useState<WeekView | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dayFilter, setDayFilter] = useState<number | null>(null)
  const [mobileWeekday, setMobileWeekday] = useState<number | null>(null)
  const loadSequence = useRef(0)

  const load = useCallback(async () => {
    const sequence = ++loadSequence.current
    setLoading(true)
    setError(null)
    try {
      const week = await api.getWeek(requestedPeriod ?? undefined, includeInactive)
      if (sequence === loadSequence.current) setData(week)
    } catch (caught) {
      if (sequence === loadSequence.current) {
        setError(
          caught instanceof ApiError
            ? caught.message
            : 'La semaine n’a pas pu être chargée.',
        )
      }
    } finally {
      if (sequence === loadSequence.current) setLoading(false)
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

  const openingByWeekday = useMemo(() => {
    return new Map((data?.opening_hours ?? []).map((item) => [item.weekday, item]))
  }, [data])

  const planningDays = useMemo<PlanningDay[]>(() => {
    if (!data) return []
    return weekDays.map(({ date, weekday }) => {
      const allDay: PlanningEntry[] = []
      const slots: PlanningEntry[] = []
      let unavailableCount = 0

      for (const volunteer of data.volunteers) {
        const day = volunteer.days.find((item) => item.weekday === weekday)
        if (!day || day.status === 'unanswered') continue
        const entry: PlanningEntry = {
          id: volunteer.id,
          name: volunteer.name,
          email: volunteer.email,
          isActive: volunteer.is_active,
          start: day.start,
          end: day.end,
        }
        if (day.status === 'all_day') allDay.push(entry)
        else if (day.status === 'slot') slots.push(entry)
        else unavailableCount += 1
      }

      return {
        date,
        weekday,
        opening: openingByWeekday.get(weekday) ?? null,
        allDay,
        slots,
        unavailableCount,
        isClosed: date <= data.today,
      }
    })
  }, [data, openingByWeekday, weekDays])

  useEffect(() => {
    if (!data || weekDays.length === 0) return
    setMobileWeekday((current) => {
      if (current && weekDays.some((day) => day.weekday === current)) {
        return current
      }
      const todayInWeek =
        data.today >= data.period_start && data.today <= data.period_end
      if (todayInWeek) {
        const weekday = parseIsoDate(data.today).getDay() - 1
        if (weekDays.some((day) => day.weekday === weekday)) return weekday
      }
      return weekDays[0]?.weekday ?? null
    })
  }, [data, weekDays])

  const answeredCount = (data?.volunteers ?? []).filter(
    (volunteer) => volunteer.submitted,
  ).length
  const total = data?.volunteers.length ?? 0
  const periodLabel = data ? formatPeriodRange(data.period_start, data.period_end) : ''

  const desktopDays = useMemo(
    () =>
      dayFilter
        ? planningDays.filter((day) => day.weekday === dayFilter)
        : planningDays,
    [dayFilter, planningDays],
  )
  const mobileDay =
    planningDays.find((day) => day.weekday === mobileWeekday) ?? planningDays[0]
  const hasInactive = (data?.volunteers ?? []).some((volunteer) => !volunteer.is_active)

  return (
    <div className="space-y-5">
      <PageHeader
        title="Planning de la semaine"
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
      ) : loading && !data ? (
        <Card className="p-4" aria-busy="true">
          <div className="grid grid-cols-5 gap-2">
            {[0, 1, 2, 3, 4].map((index) => (
              <div key={index} className="space-y-2">
                <div className="h-14 animate-pulse rounded-lg bg-stone-100" />
                <div className="h-[26rem] animate-pulse rounded-lg bg-stone-100" />
              </div>
            ))}
          </div>
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-stone-600">
            <span className="inline-flex items-center gap-1.5">
              <Users className="h-4 w-4 text-stone-400" aria-hidden />
              <strong className="font-semibold text-stone-900">{total}</strong>
              bénévole{total > 1 ? 's' : ''}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-brand-600" aria-hidden />
              <strong className="font-semibold text-stone-900">{answeredCount}</strong>
              réponse{answeredCount > 1 ? 's' : ''}
            </span>
          </div>

          {total === 0 ? (
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
            <>
              <div className="hidden xl:block">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span className="mr-1 inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-stone-400">
                    <CalendarDays className="h-3.5 w-3.5" aria-hidden />
                    Filtrer par jour
                  </span>
                  <button
                    type="button"
                    onClick={() => setDayFilter(null)}
                    aria-pressed={dayFilter === null}
                    className={cn(
                      'rounded-full border px-3 py-1 text-xs font-medium transition',
                      dayFilter === null
                        ? 'border-brand-700 bg-brand-700 text-white'
                        : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50',
                    )}
                  >
                    Tous
                  </button>
                  {planningDays.map((day) => (
                    <button
                      key={day.date}
                      type="button"
                      onClick={() => setDayFilter(day.weekday)}
                      aria-pressed={dayFilter === day.weekday}
                      className={cn(
                        'rounded-full border px-3 py-1 text-xs font-medium transition',
                        dayFilter === day.weekday
                          ? 'border-brand-700 bg-brand-700 text-white'
                          : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50',
                      )}
                    >
                      {weekdayShort(day.weekday).replace('.', '')}
                      <span
                        className={cn(
                          'ml-1.5 rounded-full px-1.5 py-0.5 text-[10px]',
                          dayFilter === day.weekday
                            ? 'bg-white/15 text-white'
                            : 'bg-stone-100 text-stone-500',
                        )}
                      >
                        {availableCount(day)}
                      </span>
                    </button>
                  ))}
                </div>
                <WeekPlanning
                  days={desktopDays}
                  single={desktopDays.length === 1}
                />
              </div>

              <div className="xl:hidden">
                <div className="mb-2 grid grid-cols-5 gap-1.5">
                  {planningDays.map((day) => {
                    const selected = mobileDay?.weekday === day.weekday
                    return (
                      <button
                        key={day.date}
                        type="button"
                        onClick={() => setMobileWeekday(day.weekday)}
                        aria-pressed={selected}
                        className={cn(
                          'flex flex-col items-center rounded-xl border px-1 py-2 text-center transition',
                          selected
                            ? 'border-brand-700 bg-brand-700 text-white shadow-sm'
                            : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50',
                        )}
                      >
                        <span className="text-[11px] font-semibold leading-tight">
                          {weekdayShort(day.weekday).replace('.', '')}
                        </span>
                        <span
                          className={cn(
                            'text-[10px] leading-tight',
                            selected ? 'text-brand-100' : 'text-stone-400',
                          )}
                        >
                          {formatShortDate(day.date)}
                        </span>
                        <span
                          className={cn(
                            'mt-0.5 text-[10px] font-medium leading-tight',
                            selected ? 'text-white' : 'text-brand-700',
                          )}
                        >
                          {availableCount(day)} dispo.
                        </span>
                      </button>
                    )
                  })}
                </div>
                {mobileDay && <WeekPlanning days={[mobileDay]} single />}
              </div>

              <div className="space-y-2 pt-1">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-stone-500">
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-sm bg-brand-200" />
                    Toute la journée (vert, repris dans les listes)
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-sm bg-sky-200" />
                    Créneau
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-sm bg-stone-200" />
                    Indisponible (non affiché)
                  </span>
                  {hasInactive && (
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-sm border border-dashed border-stone-400" />
                      Désactivé
                    </span>
                  )}
                </div>
                <p className="text-[11px] leading-relaxed text-stone-400">
                  Les bénévoles sont listés par demi-journée. Un créneau qui chevauche
                  13:00 apparaît dans les deux listes avec ses horaires réels. Les
                  journées entières sont affichées en vert en haut et reprises dans les
                  deux listes. Les bénévoles indisponibles ne sont pas listés : leur
                  nombre est indiqué dans l'en-tête de chaque jour.
                </p>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
