import { useCallback, useEffect, useState } from 'react'
import { AlertCircle, Clock3, Info, Save } from 'lucide-react'
import { api, ApiError } from '../api'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { useToast } from '../toast'
import { minutesOf, weekdayLabel } from '../lib/dates'
import type { OpeningHours } from '../types'

function validateHours(hours: OpeningHours[]): string | null {
  for (const row of hours) {
    if (!row.open || !row.close) {
      return `Renseignez les deux horaires du ${weekdayLabel(row.weekday).toLowerCase()}.`
    }
    if (minutesOf(row.open) % 30 !== 0 || minutesOf(row.close) % 30 !== 0) {
      return `Les horaires du ${weekdayLabel(row.weekday).toLowerCase()} doivent suivre un pas de 30 minutes.`
    }
    if (minutesOf(row.open) >= minutesOf(row.close)) {
      return `La fermeture doit être postérieure à l'ouverture du ${weekdayLabel(
        row.weekday,
      ).toLowerCase()}.`
    }
  }
  return null
}

export function AdminHoursPage() {
  const toast = useToast()
  const [hours, setHours] = useState<OpeningHours[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setHours(await api.getOpeningHours())
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : 'Les horaires n’ont pas pu être chargés.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const update = (weekday: number, field: 'open' | 'close', value: string) => {
    setHours((current) =>
      current.map((row) => (row.weekday === weekday ? { ...row, [field]: value } : row)),
    )
  }

  const save = async () => {
    const validation = validateHours(hours)
    if (validation) {
      setError(validation)
      return
    }
    setSaving(true)
    setError(null)
    try {
      setHours(await api.updateOpeningHours(hours))
      toast.success('Les horaires d’ouverture ont été enregistrés.')
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : 'L’enregistrement a échoué.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Horaires d'ouverture"
        description="Définissez la plage horaire dans laquelle les bénévoles peuvent proposer un créneau."
        actions={
          <Button
            onClick={() => void save()}
            loading={saving}
            disabled={loading}
            leftIcon={<Save className="h-4 w-4" />}
          >
            Enregistrer
          </Button>
        }
      />

      <div className="flex items-start gap-2.5 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm leading-relaxed text-sky-900">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-sky-600" aria-hidden />
        <p>
          Une modification ne réécrit pas les réponses déjà enregistrées. Les nouvelles
          saisies et les modifications ultérieures devront respecter les bornes configurées.
          Les horaires sont exprimés dans le fuseau <strong>Europe/Paris</strong>.
        </p>
      </div>

      {error && (
        <div
          className="flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
          role="alert"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <p>{error}</p>
        </div>
      )}

      <Card className="overflow-hidden">
        <div className="hidden grid-cols-[1fr_10rem_10rem] gap-4 border-b border-stone-100 bg-stone-50/70 px-5 py-3 text-xs font-semibold uppercase tracking-wide text-stone-400 md:grid">
          <span>Jour</span>
          <span>Ouverture</span>
          <span>Fermeture</span>
        </div>

        {loading ? (
          <div className="divide-y divide-stone-100">
            {[0, 1, 2, 3, 4].map((index) => (
              <div key={index} className="h-[4.75rem] animate-pulse bg-stone-100/60" />
            ))}
          </div>
        ) : (
          <div className="divide-y divide-stone-100">
            {hours.map((row) => (
              <div
                key={row.weekday}
                className="grid gap-3 px-4 py-4 md:grid-cols-[1fr_10rem_10rem] md:items-center md:gap-4 md:px-5"
              >
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                    <Clock3 className="h-4 w-4" aria-hidden />
                  </span>
                  <span className="font-medium text-stone-800">
                    {weekdayLabel(row.weekday)}
                  </span>
                </div>
                <label className="flex items-center gap-2 text-xs font-medium text-stone-500 md:block">
                  <span className="w-20 md:hidden">Ouverture</span>
                  <input
                    type="time"
                    className="input bg-white"
                    step={1800}
                    value={row.open}
                    onChange={(event) => update(row.weekday, 'open', event.target.value)}
                    aria-label={`Heure d'ouverture du ${weekdayLabel(row.weekday).toLowerCase()}`}
                  />
                </label>
                <label className="flex items-center gap-2 text-xs font-medium text-stone-500 md:block">
                  <span className="w-20 md:hidden">Fermeture</span>
                  <input
                    type="time"
                    className="input bg-white"
                    step={1800}
                    value={row.close}
                    onChange={(event) => update(row.weekday, 'close', event.target.value)}
                    aria-label={`Heure de fermeture du ${weekdayLabel(row.weekday).toLowerCase()}`}
                  />
                </label>
              </div>
            ))}
          </div>
        )}
      </Card>

      <p className="text-xs text-stone-400">
        Valeurs initiales : 08:00–18:00 du mardi au samedi. Un créneau doit tenir dans la
        plage d'ouverture et suivre un pas de 30 minutes.
      </p>

      <div className="flex justify-end md:hidden">
        <Button
          onClick={() => void save()}
          loading={saving}
          disabled={loading}
          leftIcon={<Save className="h-4 w-4" />}
          className="w-full"
        >
          Enregistrer les horaires
        </Button>
      </div>
    </div>
  )
}
