import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { casesApi } from '@/api'
import {
  ArrowLeft,
  Save,
  FileText,
  MapPin,
  Calendar,
  Tag,
  AlertTriangle,
  Loader2,
} from 'lucide-react'

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
  { value: 'LOW', label: 'Low', color: 'text-green-600' },
  { value: 'MEDIUM', label: 'Medium', color: 'text-yellow-600' },
  { value: 'HIGH', label: 'High', color: 'text-orange-600' },
  { value: 'CRITICAL', label: 'Critical', color: 'text-red-600' },
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
      const detail = err.response?.data?.detail || 'Failed to create case. Please try again.'
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
    if (validate()) {
      createMutation.mutate(form)
    }
  }

  const updateField = (field: keyof CaseFormData, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }))
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }))
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/cases')}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <ArrowLeft className="h-5 w-5 text-gray-600 dark:text-gray-400" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Create New Case</h1>
          <p className="text-sm text-gray-500">
            Open a new investigation case. All fields can be updated after creation.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Case Title */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="h-5 w-5 text-trace-600" />
            <h2 className="text-lg font-semibold">Case Information</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Case Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={form.title}
                onChange={(e) => updateField('title', e.target.value)}
                className={`input-field ${errors.title ? 'border-red-500 focus:ring-red-500' : ''}`}
                placeholder="e.g. Cyber Fraud Ring — Andheri Operations"
                autoFocus
              />
              {errors.title && (
                <p className="mt-1 text-sm text-red-600">{errors.title}</p>
              )}
              <p className="mt-1 text-xs text-gray-400">
                {form.title.length}/500 characters
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Description
              </label>
              <textarea
                value={form.description}
                onChange={(e) => updateField('description', e.target.value)}
                className={`input-field min-h-[120px] resize-y ${errors.description ? 'border-red-500' : ''}`}
                placeholder="Provide a detailed description of the case, including initial observations, reported incidents, and scope of investigation..."
              />
              {errors.description && (
                <p className="mt-1 text-sm text-red-600">{errors.description}</p>
              )}
              <p className="mt-1 text-xs text-gray-400">
                {form.description.length}/10,000 characters
              </p>
            </div>
          </div>
        </div>

        {/* Classification */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Tag className="h-5 w-5 text-trace-600" />
            <h2 className="text-lg font-semibold">Classification</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Category <span className="text-red-500">*</span>
              </label>
              <select
                value={form.category}
                onChange={(e) => updateField('category', e.target.value)}
                className="input-field"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Priority <span className="text-red-500">*</span>
              </label>
              <select
                value={form.priority}
                onChange={(e) => updateField('priority', e.target.value)}
                className="input-field"
              >
                {PRIORITIES.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Priority indicator */}
          <div className="mt-3 flex items-center gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50">
            <AlertTriangle className={`h-4 w-4 ${
              form.priority === 'CRITICAL' ? 'text-red-500' :
              form.priority === 'HIGH' ? 'text-orange-500' :
              form.priority === 'MEDIUM' ? 'text-yellow-500' :
              'text-green-500'
            }`} />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {form.priority === 'CRITICAL' && 'Immediate attention required. All available resources should be allocated.'}
              {form.priority === 'HIGH' && 'Urgent investigation. Prioritize over routine cases.'}
              {form.priority === 'MEDIUM' && 'Standard investigation priority.'}
              {form.priority === 'LOW' && 'Low priority. Handle when higher priority cases are addressed.'}
            </span>
          </div>
        </div>

        {/* Incident Details */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <MapPin className="h-5 w-5 text-trace-600" />
            <h2 className="text-lg font-semibold">Incident Details</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                <Calendar className="inline h-3.5 w-3.5 mr-1" />
                Incident Date
              </label>
              <input
                type="date"
                value={form.incident_date}
                onChange={(e) => updateField('incident_date', e.target.value)}
                className="input-field"
              />
              <p className="mt-1 text-xs text-gray-400">
                When the incident was first reported or occurred.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                <MapPin className="inline h-3.5 w-3.5 mr-1" />
                Location
              </label>
              <input
                type="text"
                value={form.location}
                onChange={(e) => updateField('location', e.target.value)}
                className={`input-field ${errors.location ? 'border-red-500' : ''}`}
                placeholder="e.g. Andheri West, Mumbai"
              />
              {errors.location && (
                <p className="mt-1 text-sm text-red-600">{errors.location}</p>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate('/cases')}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="btn-primary"
          >
            {createMutation.isPending ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Creating...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Save className="h-4 w-4" />
                Create Case
              </span>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
