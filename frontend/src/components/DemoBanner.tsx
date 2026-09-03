import { Info } from 'lucide-react'

export function DemoBanner() {
  return (
    <div className="flex items-center justify-center gap-2 bg-amber-500/10 border-b border-amber-500/20 px-4 py-1.5 text-xs text-amber-300">
      <Info className="h-3 w-3 shrink-0" />
      <span className="font-medium">PUBLIC DEMO</span>
      <span className="text-amber-400/60">·</span>
      <span>All data is synthetic. No real investigation data.</span>
    </div>
  )
}
