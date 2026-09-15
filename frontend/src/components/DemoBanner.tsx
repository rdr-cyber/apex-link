import { AlertTriangle } from 'lucide-react'

export function DemoBanner() {
  return (
    <div className="flex items-center justify-center gap-2 bg-dossier/8 border-b border-dossier/15 px-4 py-1">
      <AlertTriangle className="h-3 w-3 text-dossier shrink-0" />
      <span className="text-[10px] font-mono font-bold text-dossier tracking-widest uppercase">Public Demo</span>
      <span className="text-dossier/30">·</span>
      <span className="text-[10px] text-dossier-dim font-mono">All data is synthetic. No real investigation data.</span>
    </div>
  )
}
