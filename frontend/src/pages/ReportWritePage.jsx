import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, AlertCircle, CheckCircle, Save } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import Button from '../components/ui/Button'
import SelectField from '../components/ui/SelectField'

const EMPTY_FORM = {
  findings: '',
  impression: '',
  recommendation: '',
  severity: '',
}

const SEVERITY_OPTIONS = [
  { value: 'NORMAL', label: 'Normal' },
  { value: 'MILD', label: 'Mild' },
  { value: 'MODERATE', label: 'Moderate' },
  { value: 'SEVERE', label: 'Severe' },
  { value: 'CRITICAL', label: 'Critical' },
]

function getCsrfToken() {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith('csrftoken='))
    ?.split('=')[1] ?? ''
}

function validateField(field, value) {
  const trimmed = String(value ?? '').trim()
  if (!trimmed) return 'Required.'
  return ''
}

function validateForm(form) {
  const nextErrors = {}

  Object.entries(form).forEach(([field, value]) => {
    if (field === 'severity') {
      if (!String(value ?? '').trim()) nextErrors[field] = 'Required.'
      return
    }

    if (!String(value ?? '').trim()) nextErrors[field] = 'Required.'
  })

  return nextErrors
}

export default function ReportWritePage() {
  const { transactionId } = useParams()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [touched, setTouched] = useState({})
  const [reportExists, setReportExists] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [statusType, setStatusType] = useState('neutral')
  const hasLoadedReport = useRef(false)

  useEffect(() => {
    if (!transactionId || hasLoadedReport.current) return
    hasLoadedReport.current = true

    const loadReport = async () => {
      try {
        const response = await fetch(`/api/imaging/xray/${transactionId}/report/`, {
          credentials: 'include',
        })

        if (response.status === 404) {
          setForm(EMPTY_FORM)
          setReportExists(false)
          return
        }

        if (!response.ok) {
          throw new Error('Unable to load report draft.')
        }

        const data = await response.json()
        setReportExists(true)
        setForm({
          findings: data.findings ?? '',
          impression: data.impression ?? '',
          recommendation: data.recommendation ?? '',
          severity: data.severity ?? '',
        })
      } catch (error) {
        setStatusType('error')
        setStatusMessage(error.message || 'Unable to load the report draft.')
      }
    }

    loadReport()
  }, [transactionId])

  const requiredCount = useMemo(() => {
    return Object.keys(EMPTY_FORM).filter((key) => !!String(form[key] ?? '').trim()).length
  }, [form])

  const handleFieldChange = (field, value) => {
    const nextForm = { ...form, [field]: value }
    setForm(nextForm)

    if (touched[field]) {
      setErrors((prev) => ({
        ...prev,
        [field]: validateField(field, value),
      }))
    }
  }

  const handleBlur = (field) => {
    setTouched((prev) => ({ ...prev, [field]: true }))
    setErrors((prev) => ({
      ...prev,
      [field]: validateField(field, form[field]),
    }))
  }

  const persistDraft = async () => {
    setIsSaving(true)
    setStatusType('neutral')
    setStatusMessage('')

    const payload = { ...form, status: 'DRAFT' }
    const method = reportExists ? 'PATCH' : 'POST'
    const url = `/api/imaging/xray/${transactionId}/report/`

    try {
      const response = await fetch(url, {
        method,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(payload),
      })

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        const nextErrors = {}
        Object.entries(data).forEach(([key, value]) => {
          if (Array.isArray(value)) nextErrors[key] = value[0]
        })
        setErrors(nextErrors)
        throw new Error(data.detail || 'Unable to save draft.')
      }

      setReportExists(true)
      setStatusType('success')
      setStatusMessage('Draft saved successfully.')
      setForm({
        findings: data.findings ?? form.findings,
        impression: data.impression ?? form.impression,
        recommendation: data.recommendation ?? form.recommendation,
        severity: data.severity ?? form.severity,
      })
    } catch (error) {
      setStatusType('error')
      setStatusMessage(error.message || 'Unable to save draft.')
    } finally {
      setIsSaving(false)
    }
  }

  const handleSubmit = async () => {
    const nextErrors = validateForm(form)
    setErrors(nextErrors)
    setTouched({ findings: true, impression: true, recommendation: true, severity: true })

    if (Object.keys(nextErrors).length > 0) {
      setStatusType('error')
      setStatusMessage('Please complete all required fields before submitting.')
      return
    }

    setIsSubmitting(true)
    setStatusType('neutral')
    setStatusMessage('')

    try {
      const payload = { ...form, status: 'SUBMITTED' }
      const response = await fetch(`/api/imaging/xray/${transactionId}/report/`, {
        method: reportExists ? 'PATCH' : 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(payload),
      })

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        const nextErrors = {}
        Object.entries(data).forEach(([key, value]) => {
          if (Array.isArray(value)) nextErrors[key] = value[0]
        })
        setErrors(nextErrors)
        throw new Error(data.detail || 'Submission is incomplete.')
      }

      setStatusType('success')
      setStatusMessage('Report submitted successfully.')
      setTimeout(() => navigate('/dashboard/radiologist'), 1200)
    } catch (error) {
      setStatusType('error')
      setStatusMessage(error.message || 'Submission failed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-5xl flex flex-col gap-6">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => navigate('/dashboard/radiologist')}
            className="w-9 h-9 flex items-center justify-center rounded-xl border border-[var(--border)] bg-white hover:bg-[var(--surface-soft)] transition-colors"
          >
            <ArrowLeft size={16} className="text-[var(--text-muted)]" />
          </button>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Radiologist workflow</p>
            <h1 className="text-2xl font-bold text-[var(--deep-navy)]">Diagnostic Report</h1>
          </div>
        </div>

        <div className="rounded-2xl border border-[var(--border)] bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <p className="text-sm font-semibold text-[var(--deep-navy)]">Transaction</p>
              <p className="font-mono text-xs text-[var(--text-muted)]">{transactionId}</p>
            </div>
            <div className="text-sm text-[var(--text-muted)]">
              {requiredCount}/4 sections complete
            </div>
          </div>
        </div>

        {statusMessage && (
          <div
            className={`flex items-start gap-2 rounded-xl border px-4 py-3 text-sm ${
              statusType === 'success'
                ? 'border-green-200 bg-green-50 text-green-700'
                : statusType === 'error'
                  ? 'border-red-200 bg-red-50 text-red-700'
                  : 'border-slate-200 bg-slate-50 text-slate-700'
            }`}
          >
            {statusType === 'success' ? <CheckCircle size={16} className="mt-0.5" /> : <AlertCircle size={16} className="mt-0.5" />}
            <span>{statusMessage}</span>
          </div>
        )}

        <div className="space-y-5">
          <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm">
            <div className="mb-3">
              <h2 className="text-lg font-semibold text-[var(--deep-navy)]">1. Findings</h2>
              <p className="text-sm text-[var(--text-muted)]">Describe the key radiological observations.</p>
            </div>
            <textarea
              value={form.findings}
              onChange={(event) => handleFieldChange('findings', event.target.value)}
              onBlur={() => handleBlur('findings')}
              rows={6}
              placeholder="e.g., Right upper lobe opacity with cavitation and surrounding consolidation."
              className={`w-full resize-none rounded-xl border bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:ring-4 ${
                errors.findings ? 'border-red-400 focus:border-red-400 focus:ring-red-100' : 'border-slate-200 focus:border-slate-indigo-500 focus:ring-slate-100'
              }`}
            />
            {errors.findings && <span className="mt-2 block text-xs text-red-600">{errors.findings}</span>}
          </section>

          <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm">
            <div className="mb-3">
              <h2 className="text-lg font-semibold text-[var(--deep-navy)]">2. Impression</h2>
              <p className="text-sm text-[var(--text-muted)]">State the overall clinical interpretation.</p>
            </div>
            <textarea
              value={form.impression}
              onChange={(event) => handleFieldChange('impression', event.target.value)}
              onBlur={() => handleBlur('impression')}
              rows={5}
              placeholder="e.g., Suspicious for active pulmonary tuberculosis requiring urgent follow-up."
              className={`w-full resize-none rounded-xl border bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:ring-4 ${
                errors.impression ? 'border-red-400 focus:border-red-400 focus:ring-red-100' : 'border-slate-200 focus:border-slate-indigo-500 focus:ring-slate-100'
              }`}
            />
            {errors.impression && <span className="mt-2 block text-xs text-red-600">{errors.impression}</span>}
          </section>

          <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm">
            <div className="mb-3">
              <h2 className="text-lg font-semibold text-[var(--deep-navy)]">3. Recommendation</h2>
              <p className="text-sm text-[var(--text-muted)]">Record the next clinical step or recommended workup.</p>
            </div>
            <textarea
              value={form.recommendation}
              onChange={(event) => handleFieldChange('recommendation', event.target.value)}
              onBlur={() => handleBlur('recommendation')}
              rows={5}
              placeholder="e.g., Recommend sputum AFB and GeneXpert testing with specialist review."
              className={`w-full resize-none rounded-xl border bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:ring-4 ${
                errors.recommendation ? 'border-red-400 focus:border-red-400 focus:ring-red-100' : 'border-slate-200 focus:border-slate-indigo-500 focus:ring-slate-100'
              }`}
            />
            {errors.recommendation && <span className="mt-2 block text-xs text-red-600">{errors.recommendation}</span>}
          </section>

          <section className="rounded-2xl border border-[var(--border)] bg-white p-5 shadow-sm">
            <div className="mb-3">
              <h2 className="text-lg font-semibold text-[var(--deep-navy)]">4. Severity</h2>
              <p className="text-sm text-[var(--text-muted)]">Select the appropriate clinical severity classification.</p>
            </div>
            <div className="max-w-md">
              <SelectField
                id="severity"
                label="Severity classification"
                value={form.severity}
                onChange={(event) => handleFieldChange('severity', event.target.value)}
                options={SEVERITY_OPTIONS}
                error={errors.severity}
              />
            </div>
          </section>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <Button variant="secondary" onClick={persistDraft} disabled={isSaving || isSubmitting} className="flex-1">
            <Save size={15} />
            {isSaving ? 'Saving draft…' : 'Save Draft'}
          </Button>

          <Button variant="primary" onClick={handleSubmit} disabled={isSaving || isSubmitting} className="flex-1">
            {isSubmitting ? 'Submitting…' : 'Submit Report'}
          </Button>
        </div>
      </div>
    </AppLayout>
  )
}
