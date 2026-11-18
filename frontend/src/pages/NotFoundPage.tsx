import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Logo } from '../components/ui/Logo'

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-stone-100 px-4 text-center">
      <Logo variant="dark" />
      <p className="mt-8 text-sm font-semibold uppercase tracking-widest text-brand-700">
        Erreur 404
      </p>
      <h1 className="mt-2 text-2xl font-bold text-stone-900">Cette page n'existe pas</h1>
      <p className="mt-2 max-w-sm text-sm text-stone-500">
        Le lien est peut-être incomplet ou la page a été déplacée.
      </p>
      <Link
        to="/admin/semaine"
        className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-brand-700 hover:underline"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden />
        Retour à l'administration
      </Link>
    </div>
  )
}
