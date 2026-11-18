import { CalendarCheck2, Clock3, Lock, Sparkles, Sun, XCircle } from 'lucide-react'
import type { DayKind, DayView, OpeningHours } from '../../types'
import { cn } from '../../lib/cn'
import { formatDayDate, formatTimeRange, minutesOf, timeFromMinutes } from '../../lib/dates'

export interface DraftDay {
  kind: DayKind
  start: string
  end: string
}

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

interface DayEditorProps {
  day: DayView
  draft: DraftDay
  opening?: OpeningHours
  submitted: boolean
  suggested: boolean
  onChange: (draft: DraftDay) => void
}

export function DayEditor({
  day,
  draft,
  opening,
  submitted,
  suggested,
  onChange,
}: DayEditorProps) {
  const open = opening?.open ?? '08:00'
  const close = opening?.close ?? '18:00'
  const baseTimes = slotTimes(open, close)
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

  const updateStart = (start: string) => {
    let end = draft.end
    if (minutesOf(end) <= minutesOf(start)) {
      end = timeFromMinutes(Math.min(minutesOf(start) + 30, minutesOf(close)))
    }
    onChange({ ...draft, start, end })
  }

  if (!day.editable) {
    const empty = day.answer === null
    return (
      <article className="rounded-2xl border border-stone-200 bg-stone-50/70 p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">
              {formatDayDate(day.date).split(' ')[0]}
            </p>
            <h3 className="mt-0.5 text-base font-semibold first-letter:uppercase text-stone-700">
              {formatDayDate(day.date)}
            </h3>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-stone-200/70 px-2.5 py-1 text-xs font-medium text-stone-500">
            <Lock className="h-3 w-3" aria-hidden />
            Clôturé
          </span>
        </div>
        <div className="mt-3 flex items-center gap-2 text-sm">
          {day.answer?.kind === 'all_day' && (
            <span className="inline-flex items-center gap-1.5 font-medium text-brand-700">
              <Sun className="h-4 w-4" aria-hidden />
              Toute la journée
            </span>
          )}
          {day.answer?.kind === 'slot' && (
            <span className="inline-flex items-center gap-1.5 font-medium text-sky-700">
              <Clock3 className="h-4 w-4" aria-hidden />
              {formatTimeRange(day.answer.start, day.answer.end)}
            </span>
          )}
          {empty && submitted && (
            <span className="inline-flex items-center gap-1.5 text-stone-500">
              <XCircle className="h-4 w-4" aria-hidden />
              Indisponible
            </span>
          )}
          {empty && !submitted && (
            <span className="text-stone-500">Aucune réponse pour ce jour</span>
          )}
        </div>
        <p className="mt-2 text-xs text-stone-400">
          Ce jour ne peut plus être modifié après 23 h 59 la veille.
        </p>
      </article>
    )
  }

  const options: { kind: DayKind; label: string; icon: typeof Sun }[] = [
    { kind: 'unavailable', label: 'Indisponible', icon: XCircle },
    { kind: 'all_day', label: 'Toute la journée', icon: Sun },
    { kind: 'slot', label: 'Créneau', icon: Clock3 },
  ]

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
        <legend className="sr-only">
          Disponibilité du {formatDayDate(day.date)}
        </legend>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              {formatDayDate(day.date).split(' ')[0]}
            </p>
            <h3 className="mt-0.5 text-base font-semibold first-letter:uppercase text-stone-900">
              {formatDayDate(day.date)}
            </h3>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700 ring-1 ring-inset ring-brand-600/15">
            Modifiable
          </span>
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2">
          {options.map((option) => {
            const Icon = option.icon
            const selected = draft.kind === option.kind
            return (
              <label
                key={option.kind}
                className={cn(
                  'flex cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border px-2 py-2.5 text-center text-xs font-medium transition sm:flex-row sm:gap-1.5 sm:text-sm',
                  selected
                    ? option.kind === 'unavailable'
                      ? 'border-stone-400 bg-stone-100 text-stone-800 ring-1 ring-inset ring-stone-400/25'
                      : option.kind === 'slot'
                        ? 'border-sky-600 bg-sky-50 text-sky-800 ring-1 ring-inset ring-sky-600/20'
                        : 'border-brand-600 bg-brand-50 text-brand-800 ring-1 ring-inset ring-brand-600/20'
                    : 'border-stone-200 bg-white text-stone-600 hover:border-stone-300 hover:bg-stone-50',
                )}
              >
                <input
                  type="radio"
                  name={`day-${day.date}`}
                  value={option.kind}
                  checked={selected}
                  onChange={() => updateKind(option.kind)}
                  className="sr-only"
                />
                <Icon
                  className={cn(
                    'h-4 w-4',
                    !selected && 'text-stone-400',
                    selected && option.kind === 'unavailable' && 'text-stone-600',
                    selected && option.kind === 'all_day' && 'text-brand-700',
                    selected && option.kind === 'slot' && 'text-sky-700',
                  )}
                  aria-hidden
                />
                <span className="leading-tight">{option.label}</span>
              </label>
            )
          })}
        </div>

        {draft.kind === 'slot' && (
          <div className="mt-4 grid grid-cols-2 gap-3 rounded-xl bg-stone-50 p-3">
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
            <p className="col-span-2 text-xs text-stone-400">
              Créneau continu, par pas de 30 minutes, dans les horaires d'ouverture
              ({open}–{close}).
            </p>
          </div>
        )}

        {suggested && (
          <div className="mt-3 flex items-start gap-2 rounded-lg bg-amber-50/70 px-3 py-2 text-xs text-amber-800">
            <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
            Prérempli d'après vos réponses passées. Vous pouvez modifier ce choix.
          </div>
        )}
        {!suggested && draft.kind === 'all_day' && (
          <p className="mt-3 flex items-center gap-1.5 text-xs text-brand-700">
            <CalendarCheck2 className="h-3.5 w-3.5" aria-hidden />
            Vous serez disponible sur toute la plage d'ouverture de ce jour.
          </p>
        )}
      </fieldset>
    </article>
  )
}
