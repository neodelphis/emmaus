import { useState, type FormEvent } from 'react'
import { ArrowLeft, MailCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Logo } from '../components/ui/Logo'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await api.forgotPassword(email.trim())
      setSent(true)
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "La demande n'a pas pu être traitée.",
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
          {sent ? (
            <div className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-700">
                <MailCheck className="h-6 w-6" aria-hidden />
              </div>
              <h1 className="mt-4 text-xl font-bold text-stone-900">Demande envoyée</h1>
              <p className="mt-2 text-sm leading-relaxed text-stone-500">
                Si un compte existe pour <span className="font-medium text-stone-700">{email}</span>,
                un courriel contenant un lien de réinitialisation vient d'être envoyé. Le lien
                est valable une heure.
              </p>
              <p className="mt-3 text-xs text-stone-400">
                En développement local, consultez MailHog pour lire le message.
              </p>
              <Link
                to="/admin/connexion"
                className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-brand-700 hover:underline"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden />
                Retour à la connexion
              </Link>
            </div>
          ) : (
            <>
              <h1 className="text-xl font-bold text-stone-900">Mot de passe oublié</h1>
              <p className="mt-1.5 text-sm text-stone-500">
                Indiquez l'adresse de votre compte administrateur. Nous vous enverrons un lien
                pour choisir un nouveau mot de passe.
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
                  label="Adresse courriel"
                  type="email"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="vous@exemple.fr"
                />
                <Button type="submit" className="w-full" loading={loading}>
                  Envoyer le lien
                </Button>
              </form>
              <Link
                to="/admin/connexion"
                className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-stone-500 hover:text-stone-800"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden />
                Retour à la connexion
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
