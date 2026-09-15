import { useEffect, useMemo, useState } from 'react'
import { BarChart3, Download, FileText, PieChart, RefreshCcw } from 'lucide-react'
import AppLayout from '../../components/layout/AppLayout'
import StatCard from '../../components/ui/StatCard'
import Button from '../../components/ui/Button'

const SUMMARY_ENDPOINT = '/api/analytics/summary/'
const EXPORT_ENDPOINT = '/api/analytics/export/'
const SEVERITY_OPTIONS = ['', 'NORMAL', 'MILD', 'MODERATE', 'SEVERE', 'CRITICAL']

const STATUS_COLORS = {
  PENDING: '#f59e0b',
  COMPLETED: '#22c55e',
  FAILED: '#ef4444',
  DRAFT: '#64748b',
  SUBMITTED: '#2563eb',
  FINALIZED: '#0ea5e9',
}

const RISK_COLORS = {
  LOW: '#22c55e',
  MODERATE: '#f59e0b',
  HIGH: '#ef4444',
  NORMAL: '#22c55e',
  MILD: '#fde047',
  SEVERE: '#f97316',
  CRITICAL: '#dc2626',
}

function withDefaultPayload(payload) {
  return {
    filters: payload?.filters ?? {
      date_from: null,
      date_to: null,
      severity: null,
    },
    cases: {
      total: payload?.cases?.total ?? 0,
      by_status: payload?.cases?.by_status ?? {},
      by_ai_risk_label: payload?.cases?.by_ai_risk_label ?? {},
    },
    reports: {
      total: payload?.reports?.total ?? 0,
      by_severity: payload?.reports?.by_severity ?? {},
      by_status: payload?.reports?.by_status ?? {},
    },
  }
}

function titleize(value) {
  return String(value ?? '')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (match) => match.toUpperCase())
}

function mapEntries(source = {}, colorMap = {}) {
  return Object.entries(source)
    .map(([key, count]) => ({
      key,
      label: titleize(key),
      value: Number(count) || 0,
      color: colorMap[key] ?? '#64748b',
    }))
    .filter((item) => item.value > 0)
    .sort((a, b) => b.value - a.value)
}

function getConicGradient(entries) {
  const total = entries.reduce((sum, entry) => sum + entry.value, 0)
  if (!total) return 'conic-gradient(#e5e7eb 0deg 360deg)'

  let cursor = 0
  const segments = entries.map((entry) => {
    const start = cursor
    const end = cursor + (entry.value / total) * 360
    cursor = end
    return `${entry.color} ${start}deg ${end}deg`
  })

  return `conic-gradient(${segments.join(', ')})`
}

function BarBreakdownCard({ title, subtitle, entries }) {
  const total = entries.reduce((sum, entry) => sum + entry.value, 0)

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-white p-4 shadow-sm">
      <h2 className="text-base font-semibold text-[var(--deep-navy)]">{title}</h2>
      <p className="mt-0.5 text-xs text-[var(--text-muted)]">{subtitle}</p>

      {entries.length === 0 ? (
        <p className="mt-4 text-sm text-[var(--text-muted)]">No data available for current filters.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {entries.map((entry) => {
            const percent = total > 0 ? (entry.value / total) * 100 : 0
            return (
              <div key={entry.key}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="font-medium text-[var(--text)]">{entry.label}</span>
                  <span className="text-[var(--text-muted)]">{entry.value}</span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${percent.toFixed(1)}%`, backgroundColor: entry.color }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

function DonutBreakdownCard({ title, subtitle, entries }) {
  const total = entries.reduce((sum, entry) => sum + entry.value, 0)

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-white p-4 shadow-sm">
      <h2 className="text-base font-semibold text-[var(--deep-navy)]">{title}</h2>
      <p className="mt-0.5 text-xs text-[var(--text-muted)]">{subtitle}</p>

      {entries.length === 0 ? (
        <p className="mt-4 text-sm text-[var(--text-muted)]">No data available for current filters.</p>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-[150px_1fr] sm:items-center">
          <div
            className="mx-auto h-36 w-36 rounded-full"
            style={{ background: getConicGradient(entries) }}
            aria-label="Distribution chart"
          >
            <div className="flex h-full w-full items-center justify-center rounded-full border-[12px] border-white">
              <div className="text-center">
                <div className="text-xs uppercase tracking-[0.12em] text-[var(--text-muted)]">Total</div>
                <div className="text-lg font-bold text-[var(--deep-navy)]">{total}</div>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            {entries.map((entry) => (
              <div key={entry.key} className="flex items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--surface-soft)] px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
                  <span className="text-sm text-[var(--text)]">{entry.label}</span>
                </div>
                <span className="text-sm font-semibold text-[var(--deep-navy)]">{entry.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

export default function AnalyticsDashboardPage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState('')
  const [filters, setFilters] = useState({ date_from: '', date_to: '', severity: '' })
  const [data, setData] = useState(withDefaultPayload(null))

  const loadSummary = async (activeFilters) => {
    setLoading(true)
    setError('')

    const params = new URLSearchParams()
    if (activeFilters.date_from) params.set('date_from', activeFilters.date_from)
    if (activeFilters.date_to) params.set('date_to', activeFilters.date_to)
    if (activeFilters.severity) params.set('severity', activeFilters.severity)

    try {
      const response = await fetch(`${SUMMARY_ENDPOINT}${params.toString() ? `?${params.toString()}` : ''}`, {
        credentials: 'include',
      })
      const payload = await response.json().catch(() => null)

      if (!response.ok) {
        setError(payload?.detail ?? `Unable to load analytics summary (HTTP ${response.status}).`)
        setData(withDefaultPayload(null))
        return
      }

      setData(withDefaultPayload(payload))
    } catch {
      setError('Unable to reach the server. Please try again.')
      setData(withDefaultPayload(null))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSummary(filters)
  }, [])

  const handleApplyFilters = () => {
    if (filters.date_from && filters.date_to && filters.date_from > filters.date_to) {
      setError('date_from cannot be later than date_to.')
      return
    }
    loadSummary(filters)
  }

  const handleClear = () => {
    const cleared = { date_from: '', date_to: '', severity: '' }
    setFilters(cleared)
    loadSummary(cleared)
  }

  const handleExport = async (format) => {
    setExporting(format)
    setError('')

    try {
      const response = await fetch(EXPORT_ENDPOINT, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          format,
          filters: {
            date_from: filters.date_from || null,
            date_to: filters.date_to || null,
            severity: filters.severity || null,
          },
        }),
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        throw new Error(payload?.detail ?? `Unable to export ${format.toUpperCase()} (HTTP ${response.status}).`)
      }

      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = downloadUrl
      anchor.download = `analytics_export.${format}`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.URL.revokeObjectURL(downloadUrl)
    } catch (err) {
      setError(err.message || 'Export failed. Please try again.')
    } finally {
      setExporting('')
    }
  }

  const caseStatusEntries = useMemo(
    () => mapEntries(data.cases.by_status, STATUS_COLORS),
    [data.cases.by_status],
  )
  const aiRiskEntries = useMemo(
    () => mapEntries(data.cases.by_ai_risk_label, RISK_COLORS),
    [data.cases.by_ai_risk_label],
  )
  const reportSeverityEntries = useMemo(
    () => mapEntries(data.reports.by_severity, RISK_COLORS),
    [data.reports.by_severity],
  )
  const reportStatusEntries = useMemo(
    () => mapEntries(data.reports.by_status, STATUS_COLORS),
    [data.reports.by_status],
  )

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--deep-navy)]">Analytics Dashboard</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Aggregate case and report metrics with filterable clinical distribution views.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Total Cases" value={data.cases.total} />
          <StatCard label="Total Reports" value={data.reports.total} />
          <StatCard label="AI-Scored Cases" value={aiRiskEntries.reduce((sum, item) => sum + item.value, 0)} />
          <StatCard label="Critical Reports" value={Number(data.reports.by_severity.CRITICAL) || 0} highlight />
        </div>

        <section className="rounded-2xl border border-[var(--border)] bg-white p-4 shadow-sm">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
            <div className="xl:col-span-2">
              <label className="mb-1 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]" htmlFor="analytics-severity">
                Severity
              </label>
              <select
                id="analytics-severity"
                value={filters.severity}
                onChange={(event) => setFilters((prev) => ({ ...prev, severity: event.target.value }))}
                className="w-full rounded-xl border border-[var(--border)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
              >
                {SEVERITY_OPTIONS.map((option) => (
                  <option key={option || 'ALL'} value={option}>
                    {option || 'All severities'}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]" htmlFor="analytics-date-from">
                Date from
              </label>
              <input
                id="analytics-date-from"
                type="date"
                value={filters.date_from}
                onChange={(event) => setFilters((prev) => ({ ...prev, date_from: event.target.value }))}
                className="w-full rounded-xl border border-[var(--border)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]" htmlFor="analytics-date-to">
                Date to
              </label>
              <input
                id="analytics-date-to"
                type="date"
                value={filters.date_to}
                onChange={(event) => setFilters((prev) => ({ ...prev, date_to: event.target.value }))}
                className="w-full rounded-xl border border-[var(--border)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
              />
            </div>

            <div className="flex items-end gap-2">
              <Button type="button" variant="accent" onClick={handleApplyFilters} className="w-full">
                <BarChart3 size={15} />
                Apply
              </Button>
            </div>

            <div className="flex items-end gap-2">
              <Button type="button" variant="secondary" onClick={handleClear} className="w-full">
                <RefreshCcw size={15} />
                Clear
              </Button>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleExport('csv')}
              disabled={exporting === 'csv'}
            >
              <Download size={15} />
              {exporting === 'csv' ? 'Exporting CSV...' : 'Export CSV'}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleExport('pdf')}
              disabled={exporting === 'pdf'}
            >
              <FileText size={15} />
              {exporting === 'pdf' ? 'Exporting PDF...' : 'Export PDF'}
            </Button>
          </div>
        </section>

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="rounded-2xl border border-[var(--border)] bg-white p-10 text-center text-sm text-[var(--text-muted)]">
            Loading analytics summary...
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <BarBreakdownCard
                title="Case Status Distribution"
                subtitle="Case processing state under current filters"
                entries={caseStatusEntries}
              />
              <DonutBreakdownCard
                title="AI Risk Label Distribution"
                subtitle="Model-assigned labels for filtered cases"
                entries={aiRiskEntries}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <BarBreakdownCard
                title="Report Severity Breakdown"
                subtitle="Radiologist severity labels for filtered reports"
                entries={reportSeverityEntries}
              />
              <DonutBreakdownCard
                title="Report Status Breakdown"
                subtitle="Lifecycle state of generated reports"
                entries={reportStatusEntries}
              />
            </div>

            <section className="rounded-2xl border border-[var(--border)] bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center gap-2">
                <PieChart size={16} className="text-[var(--accent)]" />
                <h2 className="text-base font-semibold text-[var(--deep-navy)]">Filter Echo</h2>
              </div>
              <div className="grid grid-cols-1 gap-2 text-sm text-[var(--text)] sm:grid-cols-3">
                <div className="rounded-xl bg-[var(--surface-soft)] px-3 py-2">
                  Date from: <span className="font-semibold">{data.filters.date_from || 'None'}</span>
                </div>
                <div className="rounded-xl bg-[var(--surface-soft)] px-3 py-2">
                  Date to: <span className="font-semibold">{data.filters.date_to || 'None'}</span>
                </div>
                <div className="rounded-xl bg-[var(--surface-soft)] px-3 py-2">
                  Severity: <span className="font-semibold">{data.filters.severity || 'All'}</span>
                </div>
              </div>
            </section>
          </>
        )}
      </div>
    </AppLayout>
  )
}