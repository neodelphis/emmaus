import { HeartHandshake } from 'lucide-react'
import { cn } from '../../lib/cn'

export function Logo({
  variant = 'light',
  compact = false,
}: {
  variant?: 'light' | 'dark'
  compact?: boolean
}) {
  return (
    <div className="flex items-center gap-3">
      <span
        className={cn(
          'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
          variant === 'light'
            ? 'bg-white/15 text-white ring-1 ring-white/25'
            : 'bg-brand-700 text-white',
        )}
      >
        <HeartHandshake className="h-5 w-5" aria-hidden />
      </span>
      {!compact && (
        <div>
          <p
            className={cn(
              'text-base font-bold leading-tight',
              variant === 'light' ? 'text-white' : 'text-stone-900',
            )}
          >
            Emmaüs
          </p>
          <p
            className={cn(
              'text-xs',
              variant === 'light' ? 'text-brand-100' : 'text-stone-500',
            )}
          >
            Disponibilités
          </p>
        </div>
      )}
    </div>
  )
}
