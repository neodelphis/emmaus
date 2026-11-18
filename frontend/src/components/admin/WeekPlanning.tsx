import { useMemo } from 'react'
import { Sun } from 'lucide-react'
import { cn } from '../../lib/cn'
import { formatShortDate, minutesOf, weekdayLabel } from '../../lib/dates'
import type { OpeningHours } from '../../types'

/** Coupure de lecture entre le matin et l'après-midi. */
const SPLIT_MINUTES = 13 * 60

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

interface SectionItem {
  entry: PlanningEntry
  isAllDay: boolean
  timeLabel: string
  sortStart: number
}

interface DaySections {
  morning: SectionItem[]
  afternoon: SectionItem[]
}

function buildSections(day: PlanningDay): DaySections {
  const open = day.opening?.open ?? '08:00'
  const close = day.opening?.close ?? '18:00'
  const openMinutes = minutesOf(open)
  const closeMinutes = minutesOf(close)
  const morning: SectionItem[] = []
  const afternoon: SectionItem[] = []

  for (const entry of day.allDay) {
    const item: SectionItem = {
      entry,
      isAllDay: true,
      timeLabel: `${open} – ${close}`,
      sortStart: openMinutes,
    }
    // Sur les horaires usuels 08:00–18:00, une journée entière figure dans
    // les deux listes, comme demandé. On respecte toutefois des horaires
    // atypiques (ouverture après 13:00, fermeture avant 13:00).
    if (openMinutes < SPLIT_MINUTES) morning.push(item)
    if (closeMinutes > SPLIT_MINUTES) afternoon.push(item)
  }

  for (const entry of day.slots) {
    if (!entry.start || !entry.end) continue
    const start = minutesOf(entry.start)
    const end = minutesOf(entry.end)
    const item: SectionItem = {
      entry,
      isAllDay: false,
      timeLabel: `${entry.start} – ${entry.end}`,
      sortStart: start,
    }
    if (start < SPLIT_MINUTES) morning.push(item)
    if (end > SPLIT_MINUTES) afternoon.push(item)
  }

  const sortItems = (items: SectionItem[]) =>
    items.sort((left, right) => {
      if (left.isAllDay !== right.isAllDay) return left.isAllDay ? -1 : 1
      return (
        left.sortStart - right.sortStart ||
        left.entry.name.localeCompare(right.entry.name, 'fr')
      )
    })

  sortItems(morning)
  sortItems(afternoon)
  return { morning, afternoon }
}

function entryTitle(item: SectionItem): string {
  return [
    item.entry.name,
    item.timeLabel,
    item.entry.email,
    item.entry.isActive ? null : 'Bénévole désactivé',
  ]
    .filter(Boolean)
    .join(' · ')
}

function SectionCard({ item }: { item: SectionItem }) {
  const entry = item.entry
  return (
    <div
      title={entryTitle(item)}
      className={cn(
        'flex items-center gap-1 rounded-md border px-1.5 py-1 shadow-sm',
        entry.isActive
          ? 'border-sky-200 bg-sky-50'
          : 'border-dashed border-stone-300 bg-stone-50 opacity-70',
      )}
    >
      {item.isAllDay && (
        <Sun className="h-3 w-3 shrink-0 text-brand-600" aria-hidden />
      )}
      <span
        className={cn(
          'min-w-0 flex-1 truncate text-[11px] font-semibold leading-tight',
          entry.isActive ? 'text-sky-900' : 'text-stone-500',
        )}
      >
        {entry.name}
      </span>
      <span
        className={cn(
          'shrink-0 text-[10px] leading-tight tabular-nums',
          entry.isActive ? 'text-sky-700' : 'text-stone-400',
        )}
      >
        {item.timeLabel}
      </span>
    </div>
  )
}

function SectionHeading({
  label,
  hint,
  count,
  tone,
}: {
  label: string
  hint: string
  count: number
  tone: 'brand' | 'neutral'
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <p className="flex items-center gap-1.5">
        <span
          className={cn(
            'text-[9px] font-semibold uppercase tracking-wide',
            tone === 'brand' ? 'text-brand-700' : 'text-stone-500',
          )}
        >
          {label}
        </span>
        <span className="rounded-full bg-stone-100 px-1.5 py-0.5 text-[9px] font-medium leading-none text-stone-500">
          {count}
        </span>
      </p>
      <span className="text-[9px] text-stone-400">{hint}</span>
    </div>
  )
}

function HalfDaySection({
  label,
  hint,
  items,
  last = false,
}: {
  label: string
  hint: string
  items: SectionItem[]
  last?: boolean
}) {
  return (
    <section
      className={cn(
        'px-2.5 py-2',
        !last && 'border-b border-stone-100',
      )}
    >
      <SectionHeading label={label} hint={hint} count={items.length} tone="neutral" />
      <div className="mt-1.5 flex flex-col gap-1">
        {items.length === 0 ? (
          <p className="text-[10px] text-stone-400">Aucun bénévole</p>
        ) : (
          items.map((item) => <SectionCard key={item.entry.id} item={item} />)
        )}
      </div>
    </section>
  )
}

function DayCard({ day, sections }: { day: PlanningDay; sections: DaySections }) {
  const available = day.allDay.length + day.slots.length
  return (
    <article className="flex flex-col overflow-hidden rounded-xl border border-stone-200 bg-white">
      <header className="border-b border-stone-200 bg-stone-50/70 px-2.5 py-2">
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
        <div className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5 text-[10px]">
          <span className="font-semibold text-brand-700">
            {available} {available > 1 ? 'disponibles' : 'disponible'}
          </span>
          {day.unavailableCount > 0 && (
            <span className="text-stone-400">
              {day.unavailableCount} indisponible
              {day.unavailableCount > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </header>

      <section className="border-b border-brand-100 bg-brand-50/80 px-2.5 py-2">
        <SectionHeading
          label="Toute la journée"
          hint="repris dans les listes"
          count={day.allDay.length}
          tone="brand"
        />
        <div className="mt-1.5 flex flex-col gap-1">
          {day.allDay.length === 0 ? (
            <p className="text-[10px] text-stone-400">—</p>
          ) : (
            day.allDay.map((entry) => (
              <div
                key={entry.id}
                title={entryTitle({
                  entry,
                  isAllDay: true,
                  timeLabel: 'Toute la journée',
                  sortStart: 0,
                })}
                className={cn(
                  'truncate rounded-md border px-1.5 py-1 text-[11px] font-semibold leading-tight',
                  entry.isActive
                    ? 'border-brand-300 bg-brand-100/80 text-brand-800'
                    : 'border-dashed border-stone-300 bg-stone-50 text-stone-500',
                )}
              >
                {entry.name}
              </div>
            ))
          )}
        </div>
      </section>

      <HalfDaySection
        label="Matin"
        hint="avant 13:00"
        items={sections.morning}
      />
      <HalfDaySection
        label="Après-midi"
        hint="dès 13:00"
        items={sections.afternoon}
        last
      />
    </article>
  )
}

export function WeekPlanning({
  days,
  single = false,
}: {
  days: PlanningDay[]
  single?: boolean
}) {
  const sections = useMemo(() => days.map((day) => buildSections(day)), [days])

  if (days.length === 0) return null

  return (
    <div className="overflow-x-auto">
      <div className={cn('min-w-0', !single && 'min-w-[48rem]')}>
        <div
          className="grid items-start gap-2"
          style={{
            gridTemplateColumns: single
              ? '1fr'
              : `repeat(${days.length}, minmax(0, 1fr))`,
          }}
        >
          {days.map((day, index) => (
            <DayCard key={day.date} day={day} sections={sections[index]} />
          ))}
        </div>
      </div>
    </div>
  )
}
