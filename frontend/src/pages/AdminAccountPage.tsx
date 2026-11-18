import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  KeyRound,
  LogOut,
  Mail,
  ShieldCheck,
  UserCog,
  UserPlus,
} from 'lucide-react'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input, Select } from '../components/ui/Input'
import { PageHeader } from '../components/ui/PageHeader'
import { useToast } from '../toast'
import type { AdminUser } from '../types'

export function AdminAccountPage() {
  const { user, signIn, signOut } = useAuth()
  const toast = useToast()
  const [admins, setAdmins] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [newGender, setNewGender] = useState<'homme' | 'femme' | ''>('')
  const [formError, setFormError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [gender, setGender] = useState<'homme' | 'femme' | ''>(
    user?.gender ?? '',
  )
  const [savingGender, setSavingGender] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setListError(null)
    try {
      setAdmins(await api.listAdministrators())
    } catch (caught) {
      setListError(
        caught instanceof ApiError
          ? caught.message
          : 'Les comptes administrateurs n’ont pas pu être chargés.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    setGender(user?.gender ?? '')
  }, [user?.gender])

  const saveGender = async () => {
    if (!gender) {
      toast.error('Sélectionnez un genre.')
      return
    }
    setSavingGender(true)
    try {
      const updated = await api.updateMe(gender)
      signIn(updated)
      toast.success('Le genre du compte a été mis à jour.')
    } catch (caught) {
      toast.error(
        caught instanceof ApiError
          ? caught.message
          : 'Le genre du compte n’a pas pu être enregistré.',
      )
    } finally {
      setSavingGender(false)
    }
  }

  const create = async (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)
    if (password.length < 12) {
      setFormError('Le mot de passe doit contenir au moins 12 caractères.')
      return
    }
    if (password !== confirmation) {
      setFormError('Les deux mots de passe ne correspondent pas.')
      return
    }
    if (!newGender) {
      setFormError('Le genre est obligatoire.')
      return
    }
    setCreating(true)
    try {
      await api.createAdministrator(email.trim(), password, newGender)
      toast.success('Le compte administrateur a été créé.')
      setEmail('')
      setPassword('')
      setConfirmation('')
      setNewGender('')
      await load()
    } catch (caught) {
      setFormError(
        caught instanceof ApiError ? caught.message : 'La création du compte a échoué.',
      )
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Compte et administrateurs"
        description="Gérez votre session et les comptes ayant accès à l'administration."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
              <UserCog className="h-5 w-5" aria-hidden />
            </span>
            <div>
              <h2 className="font-semibold text-stone-900">Mon compte</h2>
              <p className="mt-0.5 text-sm text-stone-500">
                {user?.gender === 'femme'
                  ? 'Vous êtes connectée'
                  : 'Vous êtes connecté'}{' '}
                avec un compte administrateur.
              </p>
            </div>
          </div>

          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex items-center justify-between gap-3 rounded-xl bg-stone-50 px-3.5 py-3">
              <dt className="text-stone-500">Adresse courriel</dt>
              <dd className="truncate font-medium text-stone-900">{user?.email}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 rounded-xl bg-stone-50 px-3.5 py-3">
              <dt className="text-stone-500">Rôle</dt>
              <dd>
                <Badge tone="green">
                  <ShieldCheck className="h-3 w-3" aria-hidden />
                  Administrateur
                </Badge>
              </dd>
            </div>
          </dl>

          <div className="mt-4 rounded-xl bg-stone-50 px-3.5 py-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div className="w-full sm:max-w-[12rem]">
                <label htmlFor="account-gender" className="field-label">
                  Genre
                </label>
                <select
                  id="account-gender"
                  className="input bg-white"
                  value={gender}
                  onChange={(event) =>
                    setGender(event.target.value as 'homme' | 'femme' | '')
                  }
                  disabled={savingGender}
                >
                  <option value="">Non renseigné</option>
                  <option value="homme">Homme</option>
                  <option value="femme">Femme</option>
                </select>
              </div>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => void saveGender()}
                loading={savingGender}
                disabled={!gender || gender === user?.gender}
              >
                Enregistrer
              </Button>
            </div>
            <p className="mt-1 text-[11px] text-stone-400">
              Utilisé pour l’affichage « Connecté » / « Connectée ».
            </p>
          </div>

          <div className="mt-5 flex flex-col gap-2 sm:flex-row">
            <Link
              to="/admin/mot-de-passe-oublie"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-stone-300 bg-white px-4 py-2.5 text-sm font-semibold text-stone-800 transition hover:bg-stone-50"
            >
              <KeyRound className="h-4 w-4" aria-hidden />
              Changer mon mot de passe
            </Link>
            <Button
              variant="ghost"
              onClick={() => void signOut()}
              leftIcon={<LogOut className="h-4 w-4" />}
            >
              Se déconnecter
            </Button>
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-stone-100 text-stone-600">
              <UserPlus className="h-5 w-5" aria-hidden />
            </span>
            <div>
              <h2 className="font-semibold text-stone-900">Ajouter un administrateur</h2>
              <p className="mt-0.5 text-sm text-stone-500">
                Tous les comptes ont les mêmes droits en V1.
              </p>
            </div>
          </div>

          <form className="mt-4 space-y-3" onSubmit={create}>
            {formError && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
                {formError}
              </div>
            )}
            <Input
              label="Adresse courriel"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="collegue@exemple.fr"
            />
            <Select
              label="Genre"
              required
              value={newGender}
              onChange={(event) =>
                setNewGender(event.target.value as 'homme' | 'femme' | '')
              }
            >
              <option value="">Sélectionner…</option>
              <option value="homme">Homme</option>
              <option value="femme">Femme</option>
            </Select>
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Mot de passe"
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                hint="12 caractères minimum."
              />
              <Input
                label="Confirmation"
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                value={confirmation}
                onChange={(event) => setConfirmation(event.target.value)}
              />
            </div>
            <Button type="submit" loading={creating} leftIcon={<UserPlus className="h-4 w-4" />}>
              Créer le compte
            </Button>
          </form>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-stone-100 px-5 py-4">
          <div>
            <h2 className="font-semibold text-stone-900">Comptes administrateurs</h2>
            <p className="mt-0.5 text-xs text-stone-500">
              Chaque compte peut réinitialiser son mot de passe par courriel.
            </p>
          </div>
          <Badge tone="stone">{admins.length}</Badge>
        </div>

        {listError && (
          <div className="flex items-start gap-2 px-5 py-4 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span>{listError}</span>
          </div>
        )}

        {loading ? (
          <div className="space-y-2 p-5" aria-busy="true">
            {[0, 1].map((index) => (
              <div key={index} className="h-12 animate-pulse rounded-xl bg-stone-100" />
            ))}
          </div>
        ) : (
          <ul className="divide-y divide-stone-100">
            {admins.map((admin) => (
              <li key={admin.id} className="flex items-center gap-3 px-5 py-3.5">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-stone-100 text-stone-500">
                  <Mail className="h-4 w-4" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-stone-900">
                    {admin.email}
                  </p>
                  <p className="text-xs text-stone-400">
                    {admin.id === user?.id ? 'Vous' : 'Administrateur'}
                  </p>
                </div>
                {admin.id === user?.id && <Badge tone="green">Compte actuel</Badge>}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <p className="text-xs text-stone-400">
        Une réinitialisation de mot de passe déconnecte immédiatement les sessions ouvertes
        avec l'ancien mot de passe.
      </p>
    </div>
  )
}
