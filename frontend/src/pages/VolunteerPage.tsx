import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  Link2Off,
  Lock,
  RefreshCw,
  Save,
} from 'lucide-react'
import { api, ApiError } from '../api'
import { DayEditor, type DraftDay } from '../components/volunteer/DayEditor'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { FullPageLoader } from '../components/ui/Spinner'
import { Logo } from '../components/ui/Logo'
import { useToast } from '../toast'
import {
  formatDateTime,
  formatPeriodChip,
  formatPeriodRange,
  formatShortDate,
} from '../lib/dates'
import { cn } from '../lib/cn'
import { useHashToken } from '../lib/token'
import type {
  PeriodView,
  SiteCode,
  SiteWithHours,
  VolunteerAccess,
} from '../types'

function buildDrafts(
  period: PeriodView,
  sites: SiteWithHours[],
  defaultSite: SiteCode,
): { drafts: Record<string, DraftDay>; suggested: string[] } {
  const siteByCode = new Map(sites.map((item) => [item.code, item]))
  const drafts: Record<string, DraftDay> = {}
  const suggested: string[] = []

  for (const day of period.days) {
    if (!day.editable) continue

    let answer = day.answer
    let fromSuggestion = false
    if (!answer && !period.submitted && day.suggestion) {
      answer = day.suggestion
      fromSuggestion = true
    }

    const site = answer?.site ?? defaultSite
    const window = siteByCode
      .get(site)
      ?.opening_hours.find((item) => item.weekday === day.weekday)
    const open = window?.open ?? '08:00'
    const close = window?.close ?? '18:00'

    if (answer) {
      drafts[day.date] = {
        kind: answer.kind,
        start: answer.start ?? open,
        end: answer.end ?? close,
        site,
      }
      if (fromSuggestion) suggested.push(day.date)
    } else {
      drafts[day.date] = { kind: 'unavailable', start: open, end: close, site }
    }
  }
  return { drafts, suggested }
}

function InvalidLink() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-100 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Logo variant="dark" />
        </div>
        <Card className="p-6 text-center sm:p-8">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
            <Link2Off className="h-6 w-6" aria-hidden />
          </div>
          <h1 className="mt-4 text-xl font-bold text-stone-900">Lien personnel invalide</h1>
          <p className="mt-2 text-sm leading-relaxed text-stone-500">
            Ce lien n'est plus valable, ou il a été révoqué. Contactez l'équipe Emmaüs pour
            recevoir un nouveau lien personnel.
          </p>
        </Card>
        <p className="mt-6 text-center text-xs text-stone-400">
          Ne partagez jamais votre lien personnel.
        </p>
      </div>
    </div>
  )
}

export function VolunteerPage() {
  const token = useHashToken()
  const toast = useToast()
  const [access, setAccess] = useState<VolunteerAccess | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [invalidLink, setInvalidLink] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, DraftDay>>({})
  const [suggested, setSuggested] = useState<Set<string>>(new Set())
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!token) {
      setInvalidLink(true)
      setLoading(false)
      return
    }
    setLoading(true)
    setLoadError(null)
    setInvalidLink(false)
    setAccess(null)
    setSelected(null)
    try {
      const data = await api.getVolunteerAccess(token)
      setAccess(data)
      setSelected(data.periods[0]?.start ?? null)
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) {
        setInvalidLink(true)
      } else {
        setLoadError(
          caught instanceof ApiError
            ? caught.message
            : 'Impossible de charger vos disponibilités.',
        )
      }
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!access || !selected) return
    const period =
      access.periods.find((item) => item.start === selected) ?? access.periods[0]
    if (!period) return
    if (selected !== period.start) {
      setSelected(period.start)
    }
    const built = buildDrafts(period, access.sites, access.default_site)
    setDrafts(built.drafts)
    setSuggested(new Set(built.suggested))
    setDirty(false)
  }, [access, selected])

  useEffect(() => {
    document.title = access
      ? `${access.volunteer_name} — Disponibilités`
      : 'Disponibilités Emmaüs'
  }, [access])

  useEffect(() => {
    if (!dirty) return
    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [dirty])

  const period = useMemo(() => {
    if (!access) return null
    return access.periods.find((item) => item.start === selected) ?? access.periods[0] ?? null
  }, [access, selected])

  const openingFor = (site: SiteCode, weekday: number) =>
    access?.sites
      .find((item) => item.code === site)
      ?.opening_hours.find((item) => item.weekday === weekday)

  const editableDays = useMemo(
    () => period?.days.filter((day) => day.editable) ?? [],
    [period],
  )

  if (invalidLink) {
    return <InvalidLink />
  }

  if (loading && !access) {
    return (
      <div className="min-h-screen bg-stone-100">
        <div className="bg-brand-950 pb-24 pt-6">
          <div className="mx-auto max-w-3xl px-4">
            <Logo />
          </div>
        </div>
        <FullPageLoader label="Chargement de vos disponibilités…" />
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-100 px-4">
        <Card className="w-full max-w-md p-6 text-center">
          <AlertCircle className="mx-auto h-8 w-8 text-red-500" aria-hidden />
          <h1 className="mt-3 text-lg font-semibold text-stone-900">
            Impossible de charger la page
          </h1>
          <p className="mt-2 text-sm text-stone-500">{loadError}</p>
          <Button className="mt-5" onClick={() => void load()} leftIcon={<RefreshCw className="h-4 w-4" />}>
            Réessayer
          </Button>
        </Card>
      </div>
    )
  }

  if (!access || !period) {
    return <InvalidLink />
  }

  const firstName = access.volunteer_name.split(' ')[0]

  const selectPeriod = (start: string) => {
    if (start === period.start) return
    if (
      dirty &&
      !window.confirm(
        'Des modifications ne sont pas enregistrées. Changer de période les effacera. Continuer ?',
      )
    ) {
      return
    }
    setSelected(start)
    setSaveError(null)
  }

  const updateDay = (date: string, draft: DraftDay) => {
    setDrafts((current) => ({ ...current, [date]: draft }))
    setDirty(true)
    setSuggested((current) => {
      if (!current.has(date)) return current
      const next = new Set(current)
      next.delete(date)
      return next
    })
  }

  const handleSave = async () => {
    if (!token) return
    setSaveError(null)
    const days = editableDays.map((day) => {
      const draft = drafts[day.date]
      if (!draft || draft.kind === 'unavailable') {
        return { date: day.date, kind: 'unavailable' as const }
      }
      if (draft.kind === 'all_day') {
        return { date: day.date, kind: 'all_day' as const, site: draft.site }
      }
      return {
        date: day.date,
        kind: 'slot' as const,
        start: draft.start,
        end: draft.end,
        site: draft.site,
      }
    })
    if (days.length === 0) {
      toast.info('Aucun jour modifiable pour cette période.')
      return
    }
    setSaving(true)
    try {
      const updated = await api.saveVolunteerPeriod(token, period.start, days)
      setAccess((current) =>
        current
          ? {
              ...current,
              periods: current.periods.map((item) =>
                item.start === updated.start ? updated : item,
              ),
            }
          : current,
      )
      toast.success('Vos disponibilités ont été enregistrées.')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (caught) {
      const message =
        caught instanceof ApiError
          ? caught.message
          : "L'enregistrement a échoué. Réessayez."
      setSaveError(message)
      toast.error(message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-stone-100">
      <header className="relative overflow-hidden bg-brand-950 pb-24 pt-6 text-white">
        <div
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-brand-500/20 blur-3xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -bottom-32 left-1/4 h-72 w-72 rounded-full bg-emerald-400/10 blur-3xl"
          aria-hidden
        />
        <div className="relative mx-auto max-w-3xl px-4">
          <Logo />
          <div className="mt-8">
            <p className="text-sm font-medium text-brand-200">Votre espace personnel</p>
            <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl">
              Bonjour {firstName}
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-brand-100/80">
              Indiquez vos disponibilités pour les périodes de service du mardi au samedi.
              Chaque jour reste modifiable jusqu'à 23 h 59 la veille.
            </p>
            <p className="mt-2 text-xs text-brand-200/80">
              Site par défaut :{' '}
              {access.sites.find((item) => item.code === access.default_site)?.name ??
                access.default_site}
            </p>
          </div>
        </div>
      </header>

      <main className="relative z-10 -mt-16 mx-auto max-w-3xl px-4 pb-12">
        <Card className="overflow-visible p-4 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">
                Période de service
              </p>
              <h2 className="mt-0.5 text-lg font-semibold first-letter:uppercase text-stone-900">
                {formatPeriodRange(period.start, period.end)}
              </h2>
            </div>
            <div aria-live="polite">
              {dirty ? (
                <Badge tone="amber">Modifications non enregistrées</Badge>
              ) : period.submitted ? (
                <Badge tone="green">
                  <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                  Réponse enregistrée
                </Badge>
              ) : (
                <Badge tone="amber">À renseigner</Badge>
              )}
            </div>
          </div>

          <div className="-mx-1 mt-4 flex gap-2 overflow-x-auto px-1 pb-2">
            {access.periods.map((item) => {
              const isSelected = item.start === period.start
              return (
                <button
                  key={item.start}
                  type="button"
                  onClick={() => selectPeriod(item.start)}
                  aria-pressed={isSelected}
                  className={cn(
                    'min-w-[9.5rem] shrink-0 rounded-xl border px-3 py-2 text-left transition',
                    isSelected
                      ? 'border-brand-700 bg-brand-700 text-white shadow-sm'
                      : 'border-stone-200 bg-white text-stone-700 hover:border-stone-300 hover:bg-stone-50',
                  )}
                >
                  <span className="block text-xs font-semibold">
                    {formatPeriodChip(item.start, access.today)}
                  </span>
                  <span
                    className={cn(
                      'mt-0.5 block text-[11px]',
                      isSelected ? 'text-brand-100' : 'text-stone-400',
                    )}
                  >
                    {formatShortDate(item.start)} – {formatShortDate(item.end)}
                  </span>
                </button>
              )
            })}
          </div>

          {period.submitted_at && (
            <p className="mt-3 text-xs text-stone-400">
              Dernière modification : {formatDateTime(period.submitted_at)}
            </p>
          )}

          {saveError && (
            <div
              className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
              role="alert"
            >
              {saveError}
            </div>
          )}

          {editableDays.length === 0 ? (
            <div className="mt-5 rounded-xl bg-stone-50 px-4 py-6 text-center text-sm text-stone-500">
              Cette période ne contient plus de jours modifiables.
            </div>
          ) : (
            <>
              <div className="mt-5 space-y-3">
                {editableDays.map((day) => {
                  const draft = drafts[day.date]
                  if (!draft) return null
                  return (
                    <DayEditor
                      key={day.date}
                      day={day}
                      draft={draft}
                      opening={openingFor(draft.site, day.weekday)}
                      sites={access.sites}
                      suggested={suggested.has(day.date)}
                      onChange={(value) => updateDay(day.date, value)}
                    />
                  )
                })}
              </div>

              <div className="sticky bottom-0 z-10 -mx-4 mt-5 border-t border-stone-200 bg-white/95 px-4 py-3 shadow-[0_-8px_24px_-20px_rgba(0,0,0,0.35)] backdrop-blur sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:px-0 sm:py-0 sm:shadow-none">
                <div className="flex items-center justify-between gap-3 sm:pt-2">
                  <p className="text-xs text-stone-500">
                    {dirty
                      ? 'Modifications non enregistrées'
                      : period.submitted
                        ? 'Votre réponse est à jour.'
                        : 'Aucune réponse enregistrée pour cette période.'}
                  </p>
                  <Button
                    onClick={() => void handleSave()}
                    loading={saving}
                    leftIcon={<Save className="h-4 w-4" />}
                  >
                    Enregistrer
                  </Button>
                </div>
              </div>
            </>
          )}
        </Card>

        <div className="mt-6 flex flex-col items-center gap-2 text-center text-xs text-stone-400">
          <p className="inline-flex items-center gap-1.5">
            <Lock className="h-3.5 w-3.5" aria-hidden />
            Ce lien est personnel, ne le partagez pas.
          </p>
          <p className="inline-flex items-center gap-1.5">
            <CalendarDays className="h-3.5 w-3.5" aria-hidden />
            Les périodes ouvertes à la saisie sont affichées ci-dessus.
          </p>
        </div>
      </main>
    </div>
  )
}
