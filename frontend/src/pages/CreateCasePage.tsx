import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { casesApi } from '@/api'
import { ArrowLeft, Save, FileText, MapPin, Calendar, Tag, AlertTriangle, Loader2 } from 'lucide-react'

const CATEGORIES = [
  { value: 'CYBER_FRAUD', label: 'Cyber Fraud' },
  { value: 'WIRE_FRAUD', label: 'Wire Fraud' },
  { value: 'EXTORTION', label: 'Extortion' },
  { value: 'DRUG_TRAFFICKING', label: 'Drug Trafficking' },
  { value: 'MONEY_LAUNDERING', label: 'Money Laundering' },
  { value: 'IDENTITY_THEFT', label: 'Identity Theft' },
  { value: 'PHISHING', label: 'Phishing' },
  { value: 'DATA_BREACH', label: 'Data Breach' },
  { value: 'HUMAN_TRAFFICKING', label: 'Human Trafficking' },
  { value: 'TERRORISM', label: 'Terrorism' },
  { value: 'CORRUPTION', label: 'Corruption' },
  { value: 'THEFT', label: 'Theft' },
  { value: 'FRAUD', label: 'General Fraud' },
  { value: 'OTHER', label: 'Other' },
]

const PRIORITIES = [
  { value: 'LOW', label: 'Low', color: 'text-field' },
  { value: 'MEDIUM', label: 'Medium', color: 'text-dossier-dim' },
  { value: 'HIGH', label: 'High', color: 'text-dossier' },
  { value: 'CRITICAL', label: 'Critical', color: 'text-alert' },
]

interface CaseFormData {
  title: string
  description: string
  category: string
  priority: string
  incident_date: string
  location: string
}

export default function CreateCasePage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<CaseFormData>({
    title: '',
    description: '',
    category: 'CYBER_FRAUD',
    priority: 'MEDIUM',
    incident_date: '',
    location: '',
  })
  const [errors, setErrors] = useState<Partial<Record<keyof CaseFormData, string>>>({})

  const createMutation = useMutation({
    mutationFn: (data: CaseFormData) => {
      const payload: Record<string, unknown> = {
        title: data.title,
        description: data.description,
        category: data.category,
        priority: data.priority,
      }
      if (data.incident_date) {
        payload.incident_date = new Date(data.incident_date).toISOString()
      }
      if (data.location.trim()) {
        payload.location = data.location.trim()
      }
      return casesApi.create(payload as any)
    },
    onSuccess: (res) => {
      navigate(`/cases/${res.data.id}`)
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail || 'Failed to create case.'
      setErrors({ title: detail })
    },
  })

  const validate = (): boolean => {
    const e: Partial<Record<keyof CaseFormData, string>> = {}
    if (!form.title.trim()) e.title = 'Case title is required'
    if (form.title.length > 500) e.title = 'Title must be under 500 characters'
    if (form.description.length > 10000) e.description = 'Description must be under 10,000 characters'
    if (form.location.length > 500) e.location = 'Location must be under 500 characters'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validate()) createMutation.mutate(form)
  }

  const updateField = (field: keyof CaseFormData, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }))
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }))
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div className="flex items-center gap-3 border-b border-mist-dark pb-3">
        <button
          onClick={() => navigate('/cases')}
          className="rounded p-1 hover:bg-cream-dark transition-colors"
        >
          <ArrowLeft className="h-4 w-4 text-gray-500" />
        </button>
        <div>
          <h1 className="text-lg font-bold text-ink font-mono tracking-wide">NEW CASE</h1>
          <p className="text-xs text-gray-400">Open a new investigation case.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="h-4 w-4 text-dossier" />
            <h2 className="text-sm font-bold font-mono text-ink">CASE INFORMATION</h2>
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-label text-gray-500">Case Title <span className="text-alert">*</span></label>
              <input
                type="text"
                value={form.title}
                onChange={(e) => updateField('title', e.target.value)}
                className={`input-field ${errors.title ? 'border-alert' : ''}`}
                placeholder="e.g. Cyber Fraud Ring — Andheri Operations"
                autoFocus
              />
              {errors.title && <p className="mt-1 text-xs text-alert">{errors.title}</p>}
              <p className="mt-0.5 text-[10px] text-gray-400 font-mono">{form.title.length}/500</p>
            </div>
            <div>
              <label className="text-label text-gray-500">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => updateField('description', e.target.value)}
                className={`input-field min-h-[100px] resize-y ${errors.description ? 'border-alert' : ''}`}
                placeholder="Detailed description of the case..."
              />
              {errors.description && <p className="mt-1 text-xs text-alert">{errors.description}</p>}
              <p className="mt-0.5 text-[10px] text-gray-400 font-mono">{form.description.length}/10,000</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Tag className="h-4 w-4 text-dossier" />
            <h2 className="text-sm font-bold font-mono text-ink">CLASSIFICATION</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-label text-gray-500">Category <span className="text-alert">*</span></label>
              <select value={form.category} onChange={(e) => updateField('category', e.target.value)} className="input-field text-xs">
                {CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>{cat.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-label text-gray-500">Priority <span className="text-alert">*</span></label>
              <select value={form.priority} onChange={(e) => updateField('priority', e.target.value)} className="input-field text-xs">
                {PRIORITIES.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2 p-2 rounded bg-cream-dark border border-mist-dark">
            <AlertTriangle className={`h-3.5 w-3.5 ${
              form.priority === 'CRITICAL' ? 'text-alert' :
              form.priority === 'HIGH' ? 'text-dossier' :
              form.priority === 'MEDIUM' ? 'text-dossier-dim' :
              'text-field'
            }`} />
            <span className="text-xs text-gray-500">
              {form.priority === 'CRITICAL' && 'Immediate attention required.'}
              {form.priority === 'HIGH' && 'Urgent investigation. Prioritize over routine cases.'}
              {form.priority === 'MEDIUM' && 'Standard investigation priority.'}
              {form.priority === 'LOW' && 'Low priority. Handle when higher priority cases are addressed.'}
            </span>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <MapPin className="h-4 w-4 text-dossier" />
            <h2 className="text-sm font-bold font-mono text-ink">INCIDENT DETAILS</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-label text-gray-500"><Calendar className="inline h-3 w-3 mr-1" />Incident Date</label>
              <input type="date" value={form.incident_date} onChange={(e) => updateField('incident_date', e.target.value)} className="input-field text-xs" />
            </div>
            <div>
              <label className="text-label text-gray-500"><MapPin className="inline h-3 w-3 mr-1" />Location</label>
              <input
                type="text"
                value={form.location}
                onChange={(e) => updateField('location', e.target.value)}
                className={`input-field ${errors.location ? 'border-alert' : ''}`}
                placeholder="e.g. Andheri West, Mumbai"
              />
              {errors.location && <p className="mt-1 text-xs text-alert">{errors.location}</p>}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2">
          <button type="button" onClick={() => navigate('/cases')} className="btn-secondary text-xs">Cancel</button>
          <button type="submit" disabled={createMutation.isPending} className="btn-primary text-xs">
            {createMutation.isPending ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Creating...
              </span>
            ) : (
              <span className="flex items-center gap-1.5"><Save className="h-3.5 w-3.5" /> Create Case</span>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
