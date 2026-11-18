import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, HeartHandshake, ShieldCheck, Sparkles } from 'lucide-react'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Logo } from '../components/ui/Logo'

export function AdminLoginPage() {
  const { user, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (user) {
    return <Navigate to="/admin/semaine" replace />
  }

  const from = (location.state as { from?: string } | null)?.from ?? '/admin/semaine'

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const admin = await api.login(email.trim(), password)
      signIn(admin)
      navigate(from, { replace: true })
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : 'La connexion a échoué. Réessayez.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-stone-100 lg:grid lg:grid-cols-[1.05fr_1fr]">
      <section className="relative hidden overflow-hidden bg-brand-950 px-12 py-14 lg:flex lg:flex-col lg:justify-between">
        <div
          className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-brand-500/20 blur-3xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -bottom-40 -left-24 h-96 w-96 rounded-full bg-emerald-400/10 blur-3xl"
          aria-hidden
        />
        <div className="relative">
          <Logo />
        </div>
        <div className="relative max-w-lg">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-brand-300">
            Espace administration
          </p>
          <h1 className="mt-4 text-4xl font-bold leading-tight text-white">
            Les disponibilités de vos bénévoles, simplement.
          </h1>
          <p className="mt-5 text-base leading-relaxed text-brand-100/80">
            Gérez les liens personnels, consultez la semaine et gardez une vue claire
            entre les jours indisponibles et les réponses manquantes.
          </p>
          <ul className="mt-8 space-y-4 text-sm text-brand-100/90">
            <li className="flex items-start gap-3">
              <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-brand-300" aria-hidden />
              Des propositions fidèles aux habitudes de chaque bénévole.
            </li>
            <li className="flex items-start gap-3">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-brand-300" aria-hidden />
              Des liens personnels sans compte, révocables à tout moment.
            </li>
            <li className="flex items-start gap-3">
              <HeartHandshake className="mt-0.5 h-4 w-4 shrink-0 text-brand-300" aria-hidden />
              Une interface pensée pour le téléphone comme pour l'ordinateur.
            </li>
          </ul>
        </div>
        <p className="relative text-xs text-brand-200/50">
          Application locale — Emmaüs
        </p>
      </section>

      <section className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <div className="mb-8 flex justify-center lg:hidden">
            <Logo variant="dark" />
          </div>
          <div className="card p-6 sm:p-8">
            <p className="text-sm font-semibold text-brand-700">Connexion</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-stone-900">
              Espace administration
            </h2>
            <p className="mt-1.5 text-sm text-stone-500">
              Connectez-vous avec votre compte administrateur.
            </p>

            {error && (
              <div
                className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
                role="alert"
              >
                {error}
              </div>
            )}

            <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
              <Input
                label="Adresse courriel"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="vous@exemple.fr"
              />
              <div>
                <label htmlFor="mot-de-passe" className="field-label">
                  Mot de passe
                </label>
                <div className="relative">
                  <input
                    id="mot-de-passe"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="input pr-11"
                    placeholder="Votre mot de passe"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-stone-400 transition hover:text-stone-700"
                    aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              <div className="flex justify-end">
                <Link
                  to="/admin/mot-de-passe-oublie"
                  className="text-sm font-medium text-brand-700 hover:text-brand-800 hover:underline"
                >
                  Mot de passe oublié ?
                </Link>
              </div>

              <Button type="submit" className="w-full" size="lg" loading={loading}>
                Se connecter
              </Button>
            </form>
          </div>
          <p className="mt-6 text-center text-xs text-stone-400">
            Les bénévoles n'ont pas besoin de compte : ils utilisent leur lien personnel.
          </p>
        </div>
      </section>
    </div>
  )
}
