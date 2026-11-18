import { Sparkles, Sun, Sunrise, Sunset, XCircle } from 'lucide-react'
import type { DayKind, DayView, OpeningHours, SiteCode, SiteWithHours } from '../../types'
import { cn } from '../../lib/cn'
import { formatDayDate, formatDayMonth, minutesOf, timeFromMinutes } from '../../lib/dates'

export interface DraftDay {
  kind: DayKind
  start: string
  end: string
  site: SiteCode
}

type HalfDay = 'morning' | 'afternoon'

const MORNING_END = '12:00'
const AFTERNOON_START = '14:00'

function slotTimes(open: string, close: string): string[] {
  const start = minutesOf(open)
  const end = minutesOf(close)
  const values: string[] = []
  for (let minutes = start; minutes <= end; minutes += 30) {
    values.push(timeFromMinutes(minutes))
  }
  return values
}

function included<T extends string>(values: T[], value: T): T[] {
  if (!value || values.includes(value)) return values
  return [...values, value].sort()
}

function presetRange(
  period: HalfDay,
  open: string,
  close: string,
): { start: string; end: string } {
  const openMinutes = minutesOf(open)
  const closeMinutes = minutesOf(close)
  if (period === 'morning') {
    const endMinutes = Math.min(minutesOf(MORNING_END), closeMinutes)
    return endMinutes > openMinutes
      ? { start: open, end: timeFromMinutes(endMinutes) }
      : { start: open, end: close }
  }
  const startMinutes = Math.max(minutesOf(AFTERNOON_START), openMinutes)
  return startMinutes < closeMinutes
    ? { start: timeFromMinutes(startMinutes), end: close }
    : { start: open, end: close }
}

function halfDayOf(draft: DraftDay): HalfDay | null {
  if (draft.kind !== 'slot') return null
  return minutesOf(draft.start) < minutesOf(MORNING_END) ? 'morning' : 'afternoon'
}

interface DayEditorProps {
  day: DayView
  draft: DraftDay
  opening?: OpeningHours
  sites: SiteWithHours[]
  suggested: boolean
  onChange: (draft: DraftDay) => void
}

export function DayEditor({
  day,
  draft,
  opening,
  sites,
  suggested,
  onChange,
}: DayEditorProps) {
  const open = opening?.open ?? '08:00'
  const close = opening?.close ?? '18:00'
  const baseTimes = slotTimes(open, close)
  const morningPreset = presetRange('morning', open, close)
  const afternoonPreset = presetRange('afternoon', open, close)
  const halfDay = halfDayOf(draft)
  const startOptions = included(baseTimes.slice(0, -1), draft.start)
  const endOptions = included(
    baseTimes.filter((value) => minutesOf(value) > minutesOf(draft.start)),
    draft.end,
  )

  const updateKind = (kind: DayKind) => {
    if (kind === 'slot' && minutesOf(draft.start) >= minutesOf(draft.end)) {
      onChange({ ...draft, kind, start: open, end: close })
      return
    }
    onChange({ ...draft, kind })
  }

  const selectHalfDay = (period: HalfDay) => {
    if (draft.kind === 'slot' && halfDay === period) return
    const range = period === 'morning' ? morningPreset : afternoonPreset
    onChange({ ...draft, kind: 'slot', start: range.start, end: range.end })
  }

  const changeSite = (siteCode: SiteCode) => {
    const site = sites.find((item) => item.code === siteCode)
    const window = site?.opening_hours.find((item) => item.weekday === day.weekday)
    const nextOpen = window?.open ?? open
    const nextClose = window?.close ?? close
    if (draft.kind !== 'slot') {
      onChange({ ...draft, site: siteCode })
      return
    }
    let start = draft.start
    let end = draft.end
    if (minutesOf(start) < minutesOf(nextOpen) || minutesOf(start) >= minutesOf(nextClose)) {
      start = nextOpen
    }
    if (minutesOf(end) <= minutesOf(start) || minutesOf(end) > minutesOf(nextClose)) {
      end = nextClose
    }
    onChange({ ...draft, site: siteCode, start, end })
  }

  const updateStart = (start: string) => {
    let end = draft.end
    if (minutesOf(end) <= minutesOf(start)) {
      end = timeFromMinutes(Math.min(minutesOf(start) + 30, minutesOf(close)))
    }
    onChange({ ...draft, start, end })
  }

  return (
    <article
      className={cn(
        'rounded-2xl border bg-white p-4 transition sm:p-5',
        draft.kind === 'unavailable' && 'border-stone-200',
        draft.kind === 'all_day' &&
          'border-brand-200 shadow-[0_0_0_1px_rgba(5,150,105,0.06)]',
        draft.kind === 'slot' &&
          'border-sky-200 shadow-[0_0_0_1px_rgba(2,132,199,0.06)]',
      )}
    >
      <fieldset>
        <legend className="sr-only">Disponibilité du {formatDayDate(day.date)}</legend>
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              {formatDayDate(day.date).split(' ')[0]}
            </p>
            <h3 className="mt-0.5 text-base font-semibold text-stone-900">
              {formatDayMonth(day.date)}
            </h3>
          </div>
          <select
            className="input w-36 shrink-0 bg-white py-1.5 text-xs"
            aria-label="Site de la journée"
            value={draft.site}
            onChange={(event) => changeSite(event.target.value as SiteCode)}
          >
            {sites.map((site) => (
              <option key={site.code} value={site.code}>
                {site.name}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-3 grid grid-cols-3 items-stretch gap-2">
          <label
            className={cn(
              'flex h-full cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border px-1.5 py-2 text-center text-[10px] font-medium transition sm:text-xs',
              draft.kind === 'all_day'
                ? 'border-brand-600 bg-brand-50 text-brand-800 ring-1 ring-inset ring-brand-600/20'
                : 'border-stone-200 bg-white text-stone-600 hover:border-stone-300 hover:bg-stone-50',
            )}
          >
            <input
              type="radio"
              name={`day-${day.date}`}
              value="all_day"
              checked={draft.kind === 'all_day'}
              onChange={() => updateKind('all_day')}
              className="sr-only"
            />
            <Sun
              className={cn(
                'h-4 w-4',
                draft.kind === 'all_day' ? 'text-brand-700' : 'text-stone-400',
              )}
              aria-hidden
            />
            <span className="whitespace-nowrap leading-tight">Toute la journée</span>
          </label>

          <div className="grid gap-2">
            {[
              {
                period: 'morning' as const,
                label: 'Matin',
                icon: Sunrise,
              },
              {
                period: 'afternoon' as const,
                label: 'Après-midi',
                icon: Sunset,
              },
            ].map((option) => {
              const Icon = option.icon
              const selected = halfDay === option.period
              return (
                <button
                  key={option.period}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => selectHalfDay(option.period)}
                  className={cn(
                    'flex flex-col items-center justify-center gap-1 rounded-xl border px-1.5 py-2 text-center text-[10px] font-medium transition sm:text-xs',
                    selected
                      ? 'border-sky-600 bg-sky-50 text-sky-900 ring-1 ring-inset ring-sky-600/20'
                      : 'border-stone-200 bg-white text-stone-700 hover:border-stone-300 hover:bg-stone-50',
                  )}
                >
                  <span className="inline-flex items-center gap-1 whitespace-nowrap leading-tight">
                    <Icon
                      className={cn(
                        'h-4 w-4',
                        selected ? 'text-sky-700' : 'text-stone-400',
                      )}
                      aria-hidden
                    />
                    {option.label}
                  </span>
                </button>
              )
            })}
          </div>

          <label
            className={cn(
              'flex h-full cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border px-1.5 py-2 text-center text-[10px] font-medium transition sm:text-xs',
              draft.kind === 'unavailable'
                ? 'border-stone-400 bg-stone-100 text-stone-800 ring-1 ring-inset ring-stone-400/25'
                : 'border-stone-200 bg-white text-stone-600 hover:border-stone-300 hover:bg-stone-50',
            )}
          >
            <input
              type="radio"
              name={`day-${day.date}`}
              value="unavailable"
              checked={draft.kind === 'unavailable'}
              onChange={() => updateKind('unavailable')}
              className="sr-only"
            />
            <XCircle
              className={cn(
                'h-4 w-4',
                draft.kind === 'unavailable' ? 'text-stone-600' : 'text-stone-400',
              )}
              aria-hidden
            />
            <span className="whitespace-nowrap leading-tight">Indisponible</span>
          </label>
        </div>


        {draft.kind === 'slot' && (
          <div className="mt-3 rounded-xl bg-stone-50 p-3">
            <p className="text-xs font-medium text-stone-600">Horaires</p>
            <div className="mt-1.5 grid grid-cols-2 gap-3">
              <label className="text-xs font-medium text-stone-600">
                De
                <select
                  className="input mt-1 bg-white py-2"
                  value={draft.start}
                  onChange={(event) => updateStart(event.target.value)}
                >
                  {startOptions.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs font-medium text-stone-600">
                À
                <select
                  className="input mt-1 bg-white py-2"
                  value={draft.end}
                  onChange={(event) => onChange({ ...draft, end: event.target.value })}
                >
                  {endOptions.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="mt-1.5 text-[11px] text-stone-400">
              Ajustez les horaires si besoin.
            </p>
          </div>
        )}

        {suggested && (
          <div className="mt-3 flex items-start gap-2 rounded-lg bg-amber-50/70 px-3 py-2 text-xs text-amber-800">
            <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
            Prérempli d'après vos réponses passées. Vous pouvez modifier ce choix.
          </div>
        )}
      </fieldset>
    </article>
  )
}
