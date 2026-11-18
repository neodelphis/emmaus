import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, ArrowLeft, CheckCircle2 } from 'lucide-react'
import { api, ApiError } from '../api'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Logo } from '../components/ui/Logo'
import { clearHash, useHashToken } from '../lib/token'

export function ResetPasswordPage() {
  const token = useHashToken()
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    if (!token) return
    if (password.length < 12) {
      setError('Le mot de passe doit contenir au moins 12 caractères.')
      return
    }
    if (password !== confirmation) {
      setError('Les deux mots de passe ne correspondent pas.')
      return
    }
    setLoading(true)
    try {
      await api.resetPassword(token, password)
      clearHash()
      setDone(true)
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : 'La réinitialisation a échoué. Demandez un nouveau lien.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-100 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Logo variant="dark" />
        </div>
        <div className="card p-6 sm:p-8">
          {!token ? (
            <div className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
                <AlertTriangle className="h-6 w-6" aria-hidden />
              </div>
              <h1 className="mt-4 text-xl font-bold text-stone-900">Lien incomplet</h1>
              <p className="mt-2 text-sm text-stone-500">
                Ce lien de réinitialisation est invalide. Demandez-en un nouveau depuis la page
                de connexion.
              </p>
              <Link
                to="/admin/mot-de-passe-oublie"
                className="mt-6 inline-flex text-sm font-semibold text-brand-700 hover:underline"
              >
                Demander un nouveau lien
              </Link>
            </div>
          ) : done ? (
            <div className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
                <CheckCircle2 className="h-6 w-6" aria-hidden />
              </div>
              <h1 className="mt-4 text-xl font-bold text-stone-900">Mot de passe modifié</h1>
              <p className="mt-2 text-sm text-stone-500">
                Votre mot de passe a bien été enregistré. Les sessions ouvertes auparavant ont
                été déconnectées.
              </p>
              <Link
                to="/admin/connexion"
                className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-brand-700 hover:underline"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden />
                Se connecter
              </Link>
            </div>
          ) : (
            <>
              <h1 className="text-xl font-bold text-stone-900">Nouveau mot de passe</h1>
              <p className="mt-1.5 text-sm text-stone-500">
                Choisissez un mot de passe d'au moins 12 caractères.
              </p>
              {error && (
                <div
                  className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
                  role="alert"
                >
                  {error}
                </div>
              )}
              <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
                <Input
                  label="Nouveau mot de passe"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={12}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
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
                <Button type="submit" className="w-full" loading={loading}>
                  Enregistrer le mot de passe
                </Button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
