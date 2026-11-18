import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

type Tone = 'green' | 'amber' | 'stone' | 'blue' | 'red' | 'white'

const tones: Record<Tone, string> = {
  green: 'bg-brand-50 text-brand-800 ring-brand-600/20',
  amber: 'bg-amber-50 text-amber-800 ring-amber-600/20',
  stone: 'bg-stone-100 text-stone-600 ring-stone-500/20',
  blue: 'bg-sky-50 text-sky-800 ring-sky-600/20',
  red: 'bg-red-50 text-red-700 ring-red-600/20',
  white: 'bg-white/15 text-white ring-white/25 backdrop-blur',
}

export function Badge({
  tone = 'stone',
  children,
  className,
}: {
  tone?: Tone
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}
