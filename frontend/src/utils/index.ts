import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function truncate(str: string, max: number): string {
  return str.length > max ? str.substring(0, max) + '...' : str
}

export function priorityColor(priority: string): string {
  switch (priority) {
    case 'CRITICAL': return 'text-red-600'
    case 'HIGH': return 'text-orange-600'
    case 'MEDIUM': return 'text-yellow-600'
    case 'LOW': return 'text-green-600'
    default: return 'text-gray-600'
  }
}
