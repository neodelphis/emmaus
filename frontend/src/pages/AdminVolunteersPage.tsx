import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import {
  AlertCircle,
  Check,
  Copy,
  Link2,
  Link2Off,
  Mail,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  UserCheck,
  UserRoundX,
  Users,
} from 'lucide-react'
import { api, ApiError } from '../api'
import { ActionMenu } from '../components/ui/ActionMenu'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { EmptyState } from '../components/ui/EmptyState'
import { Input, Select } from '../components/ui/Input'
import { Modal } from '../components/ui/Modal'
import { PageHeader } from '../components/ui/PageHeader'
import { cn } from '../lib/cn'
import { useToast } from '../toast'
import type { Volunteer } from '../types'

interface LinkModalState {
  name: string
  link: string
}

type FormState = { mode: 'create' } | { mode: 'edit'; volunteer: Volunteer } | null

interface ConfirmState {
  title: string
  description: string
  confirmLabel: string
  tone?: 'primary' | 'danger'
  action: () => Promise<void>
}

function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
}

function IconAction({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string
  onClick: () => void
  disabled?: boolean
  children: ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className="rounded-lg p-2 text-stone-500 transition hover:bg-stone-100 hover:text-stone-800 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {children}
    </button>
  )
}

function VolunteerCard({
  volunteer,
  onCopy,
  onSend,
  onEdit,
  onToggleActive,
  onRevoke,
  onRegenerate,
  onDelete,
  busy,
}: {
  volunteer: Volunteer
  onCopy: (volunteer: Volunteer) => void
  onSend: (volunteer: Volunteer) => void
  onEdit: (volunteer: Volunteer) => void
  onToggleActive: (volunteer: Volunteer) => void
  onRevoke: (volunteer: Volunteer) => void
  onRegenerate: (volunteer: Volunteer) => void
  onDelete: (volunteer: Volunteer) => void
  busy: boolean
}) {
  return (
    <Card className={cn('p-3.5 sm:p-4', !volunteer.is_active && 'bg-stone-50')}>
      <div className="flex flex-wrap items-center gap-3">
        <span
          className={cn(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-xs font-bold',
            volunteer.is_active
              ? 'bg-brand-100 text-brand-800'
              : 'bg-stone-200 text-stone-500',
          )}
        >
          {initials(volunteer.name) || '?'}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate font-semibold text-stone-900">{volunteer.name}</p>
            {volunteer.is_active ? (
              <Badge tone="green">Actif</Badge>
            ) : (
              <Badge tone="stone">Désactivé</Badge>
            )}
            {volunteer.has_link ? (
              <Badge tone="blue">
                <Link2 className="h-3 w-3" aria-hidden />
                Lien actif
              </Badge>
            ) : (
              <Badge tone="stone">
                <Link2Off className="h-3 w-3" aria-hidden />
                Sans lien
              </Badge>
            )}
            {volunteer.gender ? (
              <Badge tone="stone">
                {volunteer.gender === 'femme' ? 'Femme' : 'Homme'}
              </Badge>
            ) : (
              <Badge tone="amber">Genre à renseigner</Badge>
            )}
          </div>
          <p className="mt-0.5 truncate text-xs text-stone-400">
            {volunteer.email || 'Sans courriel — lien à transmettre autrement'}
          </p>
        </div>

        <div className="flex items-center gap-0.5">
          <IconAction
            label="Copier le lien personnel"
            onClick={() => onCopy(volunteer)}
            disabled={busy || !volunteer.has_link}
          >
            <Copy className="h-4 w-4" />
          </IconAction>
          <IconAction
            label="Envoyer le lien par courriel"
            onClick={() => onSend(volunteer)}
            disabled={busy || !volunteer.email || !volunteer.is_active || !volunteer.has_link}
          >
            <Mail className="h-4 w-4" />
          </IconAction>
          <IconAction label="Modifier" onClick={() => onEdit(volunteer)} disabled={busy}>
            <Pencil className="h-4 w-4" />
          </IconAction>
          <ActionMenu
            label={`Autres actions pour ${volunteer.name}`}
            items={[
              {
                label: volunteer.is_active ? 'Désactiver' : 'Réactiver',
                icon: volunteer.is_active ? UserRoundX : UserCheck,
                onSelect: () => onToggleActive(volunteer),
                disabled: busy,
              },
              {
                label: 'Révoquer le lien',
                icon: Link2Off,
                onSelect: () => onRevoke(volunteer),
                disabled: busy || !volunteer.has_link,
              },
              {
                label: 'Générer un nouveau lien',
                icon: RefreshCw,
                onSelect: () => onRegenerate(volunteer),
                disabled: busy,
              },
              {
                label: 'Supprimer définitivement',
                icon: Trash2,
                onSelect: () => onDelete(volunteer),
                disabled: busy,
                tone: 'danger',
              },
            ]}
          />
        </div>
      </div>
    </Card>
  )
}

function VolunteerFormModal({
  open,
  initial,
  onClose,
  onSubmit,
}: {
  open: boolean
  initial: Volunteer | null
  onClose: () => void
  onSubmit: (
    name: string,
    email: string,
    gender: 'homme' | 'femme',
  ) => Promise<void>
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [email, setEmail] = useState(initial?.email ?? '')
  const [gender, setGender] = useState<'homme' | 'femme' | ''>(
    initial?.gender ?? '',
  )
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const isEdit = initial !== null

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    if (!name.trim()) {
      setError('Le nom est obligatoire.')
      return
    }
    if (!gender) {
      setError('Le genre est obligatoire.')
      return
    }
    setLoading(true)
    try {
      await onSubmit(name.trim(), email.trim(), gender)
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : 'L’enregistrement a échoué.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Modifier le bénévole' : 'Ajouter un bénévole'}
      description={
        isEdit
          ? 'Le lien personnel existant reste inchangé.'
          : 'Un lien personnel sécurisé sera créé automatiquement.'
      }
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Annuler
          </Button>
          <Button type="submit" form="volunteer-form" loading={loading}>
            {isEdit ? 'Enregistrer' : 'Ajouter le bénévole'}
          </Button>
        </>
      }
    >
      <form id="volunteer-form" className="space-y-4" onSubmit={handleSubmit}>
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
            {error}
          </div>
        )}
        <Input
          label="Nom et prénom"
          required
          maxLength={120}
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Marie Dupont"
          autoFocus
        />
        <Select
          label="Genre"
          required
          value={gender}
          onChange={(event) =>
            setGender(event.target.value as 'homme' | 'femme' | '')
          }
          hint="Requis pour accorder les messages destinés au bénévole."
        >
          <option value="">Sélectionner…</option>
          <option value="homme">Homme</option>
          <option value="femme">Femme</option>
        </Select>
        <Input
          label="Adresse courriel (facultatif)"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="marie@exemple.fr"
          hint="Sans courriel, le lien devra être transmis par un autre moyen."
        />
      </form>
    </Modal>
  )
}

export function AdminVolunteersPage() {
  const toast = useToast()
  const [volunteers, setVolunteers] = useState<Volunteer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>(null)
  const [linkModal, setLinkModal] = useState<LinkModalState | null>(null)
  const [confirm, setConfirm] = useState<ConfirmState | null>(null)
  const [confirmLoading, setConfirmLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setVolunteers(await api.listVolunteers())
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : 'La liste des bénévoles n’a pas pu être chargée.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const active = useMemo(
    () =>
      volunteers
        .filter((volunteer) => volunteer.is_active)
        .sort((left, right) => left.name.localeCompare(right.name, 'fr')),
    [volunteers],
  )
  const inactive = useMemo(
    () =>
      volunteers
        .filter((volunteer) => !volunteer.is_active)
        .sort((left, right) => left.name.localeCompare(right.name, 'fr')),
    [volunteers],
  )

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return { active, inactive }
    const matches = (volunteer: Volunteer) =>
      volunteer.name.toLowerCase().includes(term) ||
      (volunteer.email ?? '').toLowerCase().includes(term)
    return { active: active.filter(matches), inactive: inactive.filter(matches) }
  }, [active, inactive, search])

  const runBusy = async (id: string, action: () => Promise<void>) => {
    setBusyId(id)
    try {
      await action()
    } finally {
      setBusyId(null)
    }
  }

  const copyLink = async (volunteer: Volunteer) => {
    await runBusy(volunteer.id, async () => {
      try {
        const { link } = await api.getVolunteerLink(volunteer.id)
        try {
          await navigator.clipboard.writeText(link)
          toast.success('Lien personnel copié dans le presse-papiers.')
        } catch {
          setLinkModal({ name: volunteer.name, link })
        }
      } catch (caught) {
        toast.error(
          caught instanceof ApiError
            ? caught.message
            : 'Le lien n’a pas pu être récupéré.',
        )
      }
    })
  }

  const sendLink = async (volunteer: Volunteer) => {
    await runBusy(volunteer.id, async () => {
      try {
        await api.sendVolunteerLink(volunteer.id)
        toast.success('Le lien a été envoyé par courriel.')
      } catch (caught) {
        toast.error(
          caught instanceof ApiError ? caught.message : 'L’envoi a échoué.',
        )
      }
    })
  }

  const openConfirm = (state: ConfirmState) => setConfirm(state)

  const executeConfirm = async () => {
    if (!confirm) return
    setConfirmLoading(true)
    try {
      await confirm.action()
      setConfirm(null)
    } catch (caught) {
      toast.error(
        caught instanceof ApiError ? caught.message : 'L’action a échoué.',
      )
    } finally {
      setConfirmLoading(false)
    }
  }

  const revoke = (volunteer: Volunteer) => {
    openConfirm({
      title: 'Révoquer ce lien ?',
      description:
        'L’ancien lien cessera immédiatement de fonctionner. Vous pourrez ensuite générer un nouveau lien pour ce bénévole.',
      confirmLabel: 'Révoquer le lien',
      tone: 'danger',
      action: async () => {
        await api.revokeVolunteerLink(volunteer.id)
        toast.success('Le lien a été révoqué.')
        await load()
      },
    })
  }

  const regenerate = (volunteer: Volunteer) => {
    openConfirm({
      title: 'Générer un nouveau lien ?',
      description:
        'L’ancien lien cessera immédiatement de fonctionner. Le nouveau lien devra être transmis au bénévole.',
      confirmLabel: 'Générer un nouveau lien',
      action: async () => {
        const { link } = await api.regenerateVolunteerLink(volunteer.id)
        setLinkModal({ name: volunteer.name, link })
        toast.success('Un nouveau lien a été généré.')
        await load()
      },
    })
  }

  const toggleActive = (volunteer: Volunteer) => {
    if (!volunteer.is_active) {
      void (async () => {
        await runBusy(volunteer.id, async () => {
          try {
            await api.updateVolunteer(volunteer.id, { is_active: true })
            toast.success('Le bénévole a été réactivé.')
            await load()
          } catch (caught) {
            toast.error(
              caught instanceof ApiError ? caught.message : 'La réactivation a échoué.',
            )
          }
        })
      })()
      return
    }
    openConfirm({
      title: 'Désactiver ce bénévole ?',
      description:
        'Son historique de réponses et son lien sont conservés, mais son lien personnel ne fonctionnera plus tant qu’il est désactivé. Vous pourrez le réactiver à tout moment.',
      confirmLabel: 'Désactiver',
      action: async () => {
        await api.updateVolunteer(volunteer.id, { is_active: false })
        toast.success('Le bénévole a été désactivé.')
        await load()
      },
    })
  }

  const remove = (volunteer: Volunteer) => {
    openConfirm({
      title: 'Supprimer définitivement ?',
      description:
        'Cette action supprime le bénévole, son lien personnel et toutes ses déclarations de disponibilités. Elle est irréversible.',
      confirmLabel: 'Supprimer définitivement',
      tone: 'danger',
      action: async () => {
        await api.deleteVolunteer(volunteer.id)
        toast.success('Le bénévole a été supprimé.')
        await load()
      },
    })
  }

  const handleFormSubmit = async (
    name: string,
    email: string,
    gender: 'homme' | 'femme',
  ) => {
    if (form?.mode === 'edit') {
      await api.updateVolunteer(form.volunteer.id, {
        name,
        email: email || null,
        gender,
      })
      toast.success('Le bénévole a été mis à jour.')
      setForm(null)
      await load()
      return
    }
    const created = await api.createVolunteer({
      name,
      email: email || null,
      gender,
    })
    setForm(null)
    setLinkModal({ name: created.name, link: created.link })
    toast.success('Le bénévole a été ajouté.')
    await load()
  }

  const copyModalLink = async () => {
    if (!linkModal) return
    try {
      await navigator.clipboard.writeText(linkModal.link)
      toast.success('Lien copié.')
    } catch {
      toast.error('La copie automatique a échoué. Sélectionnez le lien manuellement.')
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Bénévoles"
        description="Gérez les fiches, les liens personnels et les accès."
        actions={
          <Button
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={() => setForm({ mode: 'create' })}
          >
            Ajouter un bénévole
          </Button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-sm">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400"
            aria-hidden
          />
          <input
            type="search"
            className="input bg-white pl-9"
            placeholder="Rechercher un nom ou un courriel"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label="Rechercher un bénévole"
          />
        </div>
        <p className="text-xs text-stone-500">
          {active.length} actif{active.length > 1 ? 's' : ''}
          {inactive.length > 0 &&
            ` · ${inactive.length} désactivé${inactive.length > 1 ? 's' : ''}`}
        </p>
      </div>

      {error && (
        <Card className="flex items-start gap-3 p-4 text-sm text-red-800">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
          <div>
            <p>{error}</p>
            <Button variant="secondary" size="sm" className="mt-3" onClick={() => void load()}>
              Réessayer
            </Button>
          </div>
        </Card>
      )}

      {loading ? (
        <div className="space-y-3" aria-busy="true">
          {[0, 1, 2].map((index) => (
            <div key={index} className="h-[4.5rem] animate-pulse rounded-2xl bg-stone-200/70" />
          ))}
        </div>
      ) : volunteers.length === 0 ? (
        <EmptyState
          icon={Users}
          title="Aucun bénévole pour le moment"
          description="Ajoutez votre premier bénévole : un lien personnel sécurisé sera créé automatiquement."
          action={
            <Button
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => setForm({ mode: 'create' })}
            >
              Ajouter un bénévole
            </Button>
          }
        />
      ) : filtered.active.length === 0 && filtered.inactive.length === 0 ? (
        <Card className="p-8 text-center text-sm text-stone-500">
          Aucun bénévole ne correspond à « {search} ».
        </Card>
      ) : (
        <>
          <div className="space-y-3">
            {filtered.active.map((volunteer) => (
              <VolunteerCard
                key={volunteer.id}
                volunteer={volunteer}
                onCopy={copyLink}
                onSend={sendLink}
                onEdit={(item) => setForm({ mode: 'edit', volunteer: item })}
                onToggleActive={toggleActive}
                onRevoke={revoke}
                onRegenerate={regenerate}
                onDelete={remove}
                busy={busyId === volunteer.id}
              />
            ))}
          </div>

          {filtered.inactive.length > 0 && (
            <details className="group rounded-2xl border border-stone-200 bg-stone-50/60 p-1">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-stone-600 hover:bg-stone-100/60">
                <span className="inline-flex items-center gap-2">
                  <UserRoundX className="h-4 w-4" aria-hidden />
                  Bénévoles désactivés ({filtered.inactive.length})
                </span>
                <span className="text-xs font-normal text-stone-400 group-open:hidden">
                  Afficher
                </span>
                <span className="hidden text-xs font-normal text-stone-400 group-open:inline">
                  Masquer
                </span>
              </summary>
              <div className="space-y-2 p-2">
                {filtered.inactive.map((volunteer) => (
                  <VolunteerCard
                    key={volunteer.id}
                    volunteer={volunteer}
                    onCopy={copyLink}
                    onSend={sendLink}
                    onEdit={(item) => setForm({ mode: 'edit', volunteer: item })}
                    onToggleActive={toggleActive}
                    onRevoke={revoke}
                    onRegenerate={regenerate}
                    onDelete={remove}
                    busy={busyId === volunteer.id}
                  />
                ))}
              </div>
            </details>
          )}
        </>
      )}

      <VolunteerFormModal
        key={form?.mode === 'edit' ? form.volunteer.id : 'create'}
        open={form !== null}
        initial={form?.mode === 'edit' ? form.volunteer : null}
        onClose={() => setForm(null)}
        onSubmit={handleFormSubmit}
      />

      <Modal
        open={linkModal !== null}
        onClose={() => setLinkModal(null)}
        title="Lien personnel"
        description={
          linkModal
            ? `Transmettez ce lien à ${linkModal.name}. Il est personnel et ne doit pas être partagé.`
            : undefined
        }
        footer={
          <Button variant="secondary" onClick={() => setLinkModal(null)}>
            Fermer
          </Button>
        }
      >
        {linkModal && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 rounded-xl border border-stone-200 bg-stone-50 p-2">
              <input
                readOnly
                value={linkModal.link}
                onFocus={(event) => event.currentTarget.select()}
                className="min-w-0 flex-1 bg-transparent px-2 py-1.5 font-mono text-xs text-stone-700 outline-none"
                aria-label="Lien personnel du bénévole"
              />
              <Button
                size="sm"
                variant="secondary"
                onClick={() => void copyModalLink()}
                leftIcon={<Copy className="h-3.5 w-3.5" />}
              >
                Copier
              </Button>
            </div>
            <p className="flex items-start gap-2 text-xs text-amber-800">
              <Check className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              Le lien reste stable lors d'un renvoi. Pour l'invalider, révoquez-le puis
              générez-en un nouveau.
            </p>
          </div>
        )}
      </Modal>

      <ConfirmDialog
        open={confirm !== null}
        title={confirm?.title ?? ''}
        description={confirm?.description ?? ''}
        confirmLabel={confirm?.confirmLabel ?? 'Confirmer'}
        tone={confirm?.tone}
        onConfirm={() => void executeConfirm()}
        onClose={() => setConfirm(null)}
        loading={confirmLoading}
      />
    </div>
  )
}
