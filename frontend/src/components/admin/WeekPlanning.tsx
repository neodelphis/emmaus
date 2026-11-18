import { useMemo } from 'react'
import { cn } from '../../lib/cn'
import {
  formatShortDate,
  minutesOf,
  timeFromMinutes,
  weekdayLabel,
} from '../../lib/dates'
import type { OpeningHours } from '../../types'

export interface PlanningEntry {
  id: string
  name: string
  email: string | null
  isActive: boolean
  start: string | null
  end: string | null
}

export interface PlanningDay {
  date: string
  weekday: number
  opening: OpeningHours | null
  allDay: PlanningEntry[]
  slots: PlanningEntry[]
  unavailableCount: number
  isClosed: boolean
}

const HOUR_HEIGHT = 64
const HALF_HOUR_HEIGHT = HOUR_HEIGHT / 2
const AXIS_WIDTH = '3.5rem'

interface PositionedSlot {
  entry: PlanningEntry
  lane: number
  laneCount: number
}

function positionSlots(slots: PlanningEntry[]): PositionedSlot[] {
  const sorted = [...slots]
    .filter((entry) => entry.start !== null && entry.end !== null)
    .sort((left, right) => {
      const startDiff = minutesOf(left.start!) - minutesOf(right.start!)
      if (startDiff !== 0) return startDiff
      return minutesOf(left.end!) - minutesOf(right.end!)
    })

  const laneEnds: number[] = []
  const positioned = sorted.map((entry) => {
    const start = minutesOf(entry.start!)
    const end = Math.max(minutesOf(entry.end!), start + 30)
    let lane = laneEnds.findIndex((value) => value <= start)
    if (lane === -1) {
      lane = laneEnds.length
      laneEnds.push(end)
    } else {
      laneEnds[lane] = end
    }
    return { entry, lane }
  })

  const laneCount = Math.max(laneEnds.length, 1)
  return positioned.map((item) => ({ ...item, laneCount }))
}

function entryTitle(entry: PlanningEntry): string {
  const details = [
    entry.name,
    entry.start && entry.end ? `${entry.start} – ${entry.end}` : 'Toute la journée',
    entry.email,
    entry.isActive ? null : 'Bénévole désactivé',
  ].filter(Boolean)
  return details.join(' · ')
}

function AllDayCell({ day }: { day: PlanningDay }) {
  if (day.allDay.length === 0) {
    return <span className="px-1 pt-1 text-[10px] text-stone-300">—</span>
  }
  return (
    <>
      {day.allDay.map((entry) => (
        <div
          key={entry.id}
          title={entryTitle(entry)}
          className={cn(
            'truncate rounded-md border px-1.5 py-1 text-[10px] font-semibold leading-tight',
            entry.isActive
              ? 'border-brand-200 bg-brand-50 text-brand-800'
              : 'border-dashed border-stone-300 bg-stone-50 text-stone-500',
          )}
        >
          {entry.name}
        </div>
      ))}
    </>
  )
}

function DayTimeline({
  day,
  axisStart,
  axisEnd,
  height,
}: {
  day: PlanningDay
  axisStart: number
  axisEnd: number
  height: number
}) {
  const positioned = positionSlots(day.slots)
  const open = day.opening ? minutesOf(day.opening.open) : axisStart
  const close = day.opening ? minutesOf(day.opening.close) : axisEnd
  const openHeight = ((open - axisStart) / 60) * HOUR_HEIGHT
  const closeHeight = ((axisEnd - close) / 60) * HOUR_HEIGHT

  return (
    <div
      className="relative overflow-hidden border-l border-stone-200"
      style={{
        height,
        backgroundImage: `repeating-linear-gradient(to bottom, rgba(231,229,228,0.8) 0, rgba(231,229,228,0.8) 1px, transparent 1px, transparent ${HALF_HOUR_HEIGHT}px), repeating-linear-gradient(to bottom, rgba(214,211,209,0.9) 0, rgba(214,211,209,0.9) 1px, transparent 1px, transparent ${HOUR_HEIGHT}px)`,
      }}
    >
      {open > axisStart && (
        <div
          className="pointer-events-none absolute inset-x-0 top-0 z-0 bg-stone-100/80"
          style={{ height: openHeight }}
          title="En dehors des horaires d'ouverture"
        />
      )}
      {close < axisEnd && (
        <div
          className="pointer-events-none absolute inset-x-0 bottom-0 z-0 bg-stone-100/80"
          style={{ height: closeHeight }}
          title="En dehors des horaires d'ouverture"
        />
      )}

      {positioned.map(({ entry, lane, laneCount }) => {
        const start = minutesOf(entry.start!)
        const end = Math.max(minutesOf(entry.end!), start + 30)
        const top = ((start - axisStart) / 60) * HOUR_HEIGHT
        const blockHeight = Math.max(((end - start) / 60) * HOUR_HEIGHT - 2, 22)
        const width = 100 / laneCount
        return (
          <div
            key={entry.id}
            className="absolute z-10 px-[2px]"
            style={{
              top,
              height: blockHeight,
              left: `${lane * width}%`,
              width: `${width}%`,
            }}
          >
            <div
              title={entryTitle(entry)}
              className={cn(
                'flex h-full flex-col justify-start overflow-hidden rounded-md border px-1.5 py-0.5 shadow-sm',
                entry.isActive
                  ? 'border-sky-200 bg-sky-50 text-sky-900'
                  : 'border-dashed border-stone-300 bg-stone-50 text-stone-500',
              )}
            >
              <span className="truncate text-[10px] font-semibold leading-tight">
                {entry.name}
              </span>
              <span
                className={cn(
                  'truncate text-[9px] leading-tight',
                  entry.isActive ? 'text-sky-700' : 'text-stone-400',
                )}
              >
                {entry.start} – {entry.end}
              </span>
            </div>
          </div>
        )
      })}

      {day.allDay.length === 0 && day.slots.length === 0 && (
        <p className="pointer-events-none absolute inset-x-0 top-5 z-20 px-2 text-center text-[10px] text-stone-400">
          Aucun bénévole disponible
        </p>
      )}
    </div>
  )
}

export function WeekPlanning({
  days,
  single = false,
}: {
  days: PlanningDay[]
  single?: boolean
}) {
  const axis = useMemo(() => {
    const values: number[] = []
    for (const day of days) {
      if (day.opening) {
        values.push(minutesOf(day.opening.open), minutesOf(day.opening.close))
      }
      for (const slot of day.slots) {
        if (slot.start) values.push(minutesOf(slot.start))
        if (slot.end) values.push(minutesOf(slot.end))
      }
    }
    if (values.length === 0) values.push(8 * 60, 18 * 60)
    const start = Math.floor(Math.min(...values) / 60) * 60
    const end = Math.max(Math.ceil(Math.max(...values) / 60) * 60, start + 60)
    return { start, end }
  }, [days])

  if (days.length === 0) return null

  const height = ((axis.end - axis.start) / 60) * HOUR_HEIGHT
  const timeLabels = Array.from(
    { length: Math.floor((axis.end - axis.start) / 60) },
    (_, index) => axis.start + index * 60,
  )
  const columns = `${AXIS_WIDTH} repeat(${days.length}, minmax(0, 1fr))`

  return (
    <div className="overflow-x-auto">
      <div className={cn('min-w-0', !single && 'min-w-[48rem]')}>
        <div
          className="grid overflow-hidden rounded-xl border border-stone-200 bg-white"
          style={{ gridTemplateColumns: columns }}
        >
          <div className="border-b border-stone-200 bg-stone-50/70" />
          {days.map((day) => (
            <div
              key={`head-${day.date}`}
              className="border-b border-l border-stone-200 bg-stone-50/70 px-2.5 py-2"
            >
              <p className="text-[10px] font-semibold uppercase tracking-wide text-stone-400">
                {weekdayLabel(day.weekday)}
              </p>
              <p className="text-sm font-bold leading-tight text-stone-900">
                {formatShortDate(day.date)}
              </p>
              <div className="mt-0.5 flex flex-wrap items-center gap-1 text-[10px] text-stone-400">
                <span>
                  {day.opening
                    ? `${day.opening.open} – ${day.opening.close}`
                    : 'Horaires non définis'}
                </span>
                {day.isClosed && (
                  <span className="rounded bg-stone-100 px-1 py-0.5 text-[9px] font-medium text-stone-500">
                    Clôturé
                  </span>
                )}
              </div>
              <div className="mt-1 flex flex-col gap-0.5 text-[10px]">
                <span className="font-semibold text-brand-700">
                  {day.allDay.length + day.slots.length}{' '}
                  {day.allDay.length + day.slots.length > 1
                    ? 'disponibles'
                    : 'disponible'}
                </span>
                {day.unavailableCount > 0 && (
                  <span className="text-stone-400">
                    {day.unavailableCount} indisponible
                    {day.unavailableCount > 1 ? 's' : ''}
                  </span>
                )}
              </div>
            </div>
          ))}

          <div className="flex min-h-[3.25rem] items-center justify-end border-b border-stone-200 bg-stone-50/40 px-2 text-right text-[9px] font-semibold uppercase leading-tight tracking-wide text-stone-400">
            Toute la journée
          </div>
          {days.map((day) => (
            <div
              key={`allday-${day.date}`}
              className="flex min-h-[3.25rem] flex-col gap-1 border-b border-l border-stone-200 p-1.5"
            >
              <AllDayCell day={day} />
            </div>
          ))}

          <div className="relative" style={{ height }}>
            {timeLabels.map((minutes) => (
              <span
                key={minutes}
                className="absolute right-2 -translate-y-1/2 text-[10px] tabular-nums text-stone-400"
                style={{ top: ((minutes - axis.start) / 60) * HOUR_HEIGHT }}
              >
                {timeFromMinutes(minutes)}
              </span>
            ))}
          </div>
          {days.map((day) => (
            <DayTimeline
              key={`body-${day.date}`}
              day={day}
              axisStart={axis.start}
              axisEnd={axis.end}
              height={height}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
