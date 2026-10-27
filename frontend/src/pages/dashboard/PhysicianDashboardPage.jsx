import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Activity, AlertTriangle, FileCheck2, RefreshCcw } from 'lucide-react'
import AppLayout from '../../components/layout/AppLayout'
import StatCard from '../../components/ui/StatCard'
import Button from '../../components/ui/Button'
import { useAuth } from '../../context/AuthContext'

const DASHBOARD_ENDPOINT = '/api/physician/dashboard'
const SEVERITY_OPTIONS = ['', 'NORMAL', 'MILD', 'MODERATE', 'SEVERE', 'CRITICAL']

function formatDateTime(value) {
  if (!value) return 'N/A'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('en-PH')
}

function normalize(value) {
  return String(value ?? '').trim().toLowerCase()
}

function getCsrfToken() {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith('csrftoken='))
    ?.split('=')[1] ?? ''
}

function extractCaseIdFromAlert(message = '') {
  const match = String(message).match(/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/)
  return match ? match[1] : null
}

function withDefaultPayload(payload) {
  return {
    filters: payload?.filters ?? { severity: null, date_from: null, date_to: null },
    summary: payload?.summary ?? {
      finalized_report_count: 0,
      recent_report_count: 0,
      pending_alert_count: 0,
      report_ready_count: 0,
      patient_progress_count: 0,
    },
    finalized_cases: Array.isArray(payload?.finalized_cases) ? payload.finalized_cases : [],
    recent_reports: Array.isArray(payload?.recent_reports) ? payload.recent_reports : [],
    report_ready_items: Array.isArray(payload?.report_ready_items) ? payload.report_ready_items : [],
    pending_alerts: Array.isArray(payload?.pending_alerts) ? payload.pending_alerts : [],
    patient_progress: Array.isArray(payload?.patient_progress) ? payload.patient_progress : [],
  }
}

export default function PhysicianDashboardPage({ viewerRole = null }) {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { user } = useAuth()

  const effectiveRole = viewerRole || user?.role || 'PHYSICIAN'
  const isPatientViewer = effectiveRole === 'PATIENT'

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [patientSearch, setPatientSearch] = useState('')
  const [serverFilters, setServerFilters] = useState({
    severity: '',
    date_from: '',
    date_to: '',
  })
  const [data, setData] = useState(withDefaultPayload(null))

  const highlightedCaseId = searchParams.get('case') ?? ''

  const fetchDashboard = async (activeFilters) => {
    setLoading(true)
    setError('')

    const params = new URLSearchParams()
    if (activeFilters.severity) params.set('severity', activeFilters.severity)
    if (activeFilters.date_from) params.set('date_from', activeFilters.date_from)
    if (activeFilters.date_to) params.set('date_to', activeFilters.date_to)

    try {
      const response = await fetch(`${DASHBOARD_ENDPOINT}${params.toString() ? `?${params}` : ''}`, {
        credentials: 'include',
      })
      const payload = await response.json().catch(() => null)

      if (!response.ok) {
        const message = payload?.detail ?? `Unable to load physician dashboard (HTTP ${response.status}).`
        setError(message)
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
    fetchDashboard(serverFilters)
  }, [serverFilters])

  const transactionToCase = useMemo(() => {
    const map = new Map()
    for (const item of data.finalized_cases) {
      map.set(item.transaction_id, item)
    }
    return map
  }, [data.finalized_cases])

  const searchTerm = normalize(patientSearch)

  const finalizedCases = useMemo(() => {
    if (!searchTerm) return data.finalized_cases
    return data.finalized_cases.filter((item) => {
      const fullName = `${item.patient?.first_name ?? ''} ${item.patient?.last_name ?? ''}`
      return (
        normalize(fullName).includes(searchTerm)
        || normalize(item.patient?.patient_id).includes(searchTerm)
        || normalize(item.transaction_id).includes(searchTerm)
      )
    })
  }, [data.finalized_cases, searchTerm])

  const recentReports = useMemo(() => {
    if (!searchTerm) return data.recent_reports
    return data.recent_reports.filter((item) => {
      const fullName = `${item.patient?.first_name ?? ''} ${item.patient?.last_name ?? ''}`
      return normalize(fullName).includes(searchTerm) || normalize(item.patient?.patient_id).includes(searchTerm)
    })
  }, [data.recent_reports, searchTerm])

  const pendingAlerts = useMemo(() => {
    if (!searchTerm) return data.pending_alerts
    return data.pending_alerts.filter((item) => normalize(item.message).includes(searchTerm))
  }, [data.pending_alerts, searchTerm])

  const patientProgress = useMemo(() => {
    if (!searchTerm) return data.patient_progress
    return data.patient_progress.filter((item) => {
      const fullName = `${item.patient?.first_name ?? ''} ${item.patient?.last_name ?? ''}`
      return normalize(fullName).includes(searchTerm) || normalize(item.patient?.patient_id).includes(searchTerm)
    })
  }, [data.patient_progress, searchTerm])

  const openCase = (item) => {
    if (!item?.transaction_id) return
    if (isPatientViewer && item?.patient?.patient_id) {
      navigate(`/patients/${item.patient.patient_id}`, {
        state: { openXray: item.transaction_id },
      })
      return
    }
    navigate(`/radiologist/report/${item.transaction_id}`)
  }

  const openAlertCase = async (alert) => {
    const caseId = extractCaseIdFromAlert(alert.message)
    if (!caseId) return

    if (alert?.id) {
      try {
        await fetch(`/api/imaging/notifications/${alert.id}/mark-read/`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'X-CSRFToken': getCsrfToken() },
        })
      } catch {
        // continue with navigation even if read-state update fails
      }

      setData((previous) => ({
        ...previous,
        pending_alerts: previous.pending_alerts.filter((item) => item.id !== alert.id),
        summary: {
          ...previous.summary,
          pending_alert_count: Math.max(0, (previous.summary.pending_alert_count || 0) - 1),
        },
      }))
    }

    const item = transactionToCase.get(caseId)
    if (!item) {
      setSearchParams({ case: caseId })
      return
    }
    openCase(item)
  }

  const clearFilters = () => {
    setPatientSearch('')
    setSearchParams({})
    setServerFilters({ severity: '', date_from: '', date_to: '' })
  }

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--deep-navy)] tracking-tight">
            {isPatientViewer ? 'Patient Validation Dashboard' : 'Physician Dashboard'}
          </h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            {isPatientViewer
              ? 'Read-only access to finalized radiologist outputs and case context for validation review.'
              : 'Finalized radiologist outputs and patient follow-up context for clinical decision support.'}
          </p>
        </div>

        <div className="flex gap-4 flex-wrap">
          <StatCard label="Finalized Reports" value={data.summary.finalized_report_count} />
          <StatCard label="Pending Alerts" value={data.summary.pending_alert_count} highlight />
          <StatCard label="Latest Finalized Reports" value={data.summary.recent_report_count} />
          <StatCard label="Tracked Patients" value={data.summary.patient_progress_count} />
        </div>

        <div className="bg-white rounded-2xl border border-[var(--border)] p-4 shadow-sm flex flex-col gap-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <input
              type="text"
              value={patientSearch}
              onChange={(event) => setPatientSearch(event.target.value)}
              placeholder="Search patient or case ID"
              className="w-full rounded-xl border border-[var(--border)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
            />

            <select
              value={serverFilters.severity}
              onChange={(event) => setServerFilters((prev) => ({ ...prev, severity: event.target.value }))}
              className="w-full rounded-xl border border-[var(--border)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
            >
              {SEVERITY_OPTIONS.map((option) => (
                <option key={option || 'ALL'} value={option}>
                  {option || 'All severities'}
                </option>
              ))}
            </select>

            <input
              type="date"
              value={serverFilters.date_from}
              onChange={(event) => setServerFilters((prev) => ({ ...prev, date_from: event.target.value }))}
              className="w-full rounded-xl border border-[var(--border)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
              aria-label="From date"
            />

            <input
              type="date"
              value={serverFilters.date_to}
              onChange={(event) => setServerFilters((prev) => ({ ...prev, date_to: event.target.value }))}
              className="w-full rounded-xl border border-[var(--border)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)]"
              aria-label="To date"
            />

            <Button type="button" variant="secondary" onClick={clearFilters}>
              <RefreshCcw size={15} />
              Clear
            </Button>
          </div>

          <p className="text-xs text-[var(--text-muted)]">
            Filters apply to finalized report datasets. Patient search narrows visible dashboard cards and tables.
          </p>
        </div>

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {highlightedCaseId && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {isPatientViewer ? 'Record' : 'Case'} {highlightedCaseId} is not visible in the current filter window. Adjust date or severity filters.
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-2xl border border-[var(--border)] p-10 text-sm text-[var(--text-muted)] text-center">
            Loading physician dashboard...
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
              <section className="bg-white rounded-2xl border border-[var(--border)] p-4 shadow-sm flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle size={16} className="text-[var(--danger)]" />
                  <h2 className="text-base font-semibold text-[var(--deep-navy)]">Pending Alerts</h2>
                </div>
                {pendingAlerts.length === 0 ? (
                  <p className="text-sm text-[var(--text-muted)]">No pending alerts.</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {pendingAlerts.map((alert) => (
                      <div key={alert.id} className="rounded-xl border border-[var(--border)] p-3 bg-[var(--surface-soft)]">
                        <p className="text-sm text-[var(--text)] leading-relaxed">{alert.message}</p>
                        <div className="mt-2 flex items-center justify-between gap-3">
                          <span className="text-xs text-[var(--text-muted)]">{formatDateTime(alert.created_at)}</span>
                          <Button
                            type="button"
                            size="sm"
                            variant="secondary"
                            onClick={() => openAlertCase(alert)}
                            disabled={!extractCaseIdFromAlert(alert.message)}
                          >
                            {isPatientViewer ? 'Open record' : 'Open case'}
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="bg-white rounded-2xl border border-[var(--border)] p-4 shadow-sm flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <FileCheck2 size={16} className="text-[var(--accent)]" />
                  <h2 className="text-base font-semibold text-[var(--deep-navy)]">Latest Finalized Reports</h2>
                </div>
                {recentReports.length === 0 ? (
                  <p className="text-sm text-[var(--text-muted)]">No recent finalized reports in this view.</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {recentReports.map((report) => (
                      <button
                        key={`recent-${report.report_id}`}
                        type="button"
                        className="text-left rounded-xl border border-[var(--border)] p-3 hover:bg-[var(--surface-soft)] transition-colors"
                        onClick={() => openCase(report)}
                      >
                        <p className="text-sm font-semibold text-[var(--deep-navy)]">
                          {report.patient.first_name} {report.patient.last_name}
                        </p>
                        <p className="text-xs text-[var(--text-muted)] mt-0.5">
                          Severity: {report.severity} · Report Status: FINALIZED
                        </p>
                        <p className="text-xs text-[var(--text-muted)] mt-1">
                          {formatDateTime(report.reported_at)}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </section>
            </div>

            <section className="bg-white rounded-2xl border border-[var(--border)] p-4 shadow-sm overflow-x-auto">
              <div className="flex items-center gap-2 mb-3">
                <Activity size={16} className="text-[var(--accent)]" />
                <h2 className="text-base font-semibold text-[var(--deep-navy)]">Finalized Cases</h2>
              </div>

              {finalizedCases.length === 0 ? (
                <p className="text-sm text-[var(--text-muted)]">No finalized cases match the current filters.</p>
              ) : (
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-[var(--text-muted)] border-b border-[var(--border)]">
                      <th className="py-2 pr-3 font-medium">Patient</th>
                      <th className="py-2 pr-3 font-medium">Severity</th>
                      <th className="py-2 pr-3 font-medium">Report Status</th>
                      <th className="py-2 pr-3 font-medium">Updated</th>
                      <th className="py-2 pr-3 font-medium">Case Link</th>
                    </tr>
                  </thead>
                  <tbody>
                    {finalizedCases.map((item) => (
                      <tr
                        key={item.report_id}
                        className={`border-b border-[var(--border)] ${highlightedCaseId === item.transaction_id ? 'bg-amber-50' : ''}`}
                      >
                        <td className="py-3 pr-3">
                          <p className="font-medium text-[var(--deep-navy)]">
                            {item.patient.first_name} {item.patient.last_name}
                          </p>
                          <p className="text-xs text-[var(--text-muted)]">ID: {item.patient.patient_id}</p>
                        </td>
                        <td className="py-3 pr-3 text-[var(--text)]">{item.severity}</td>
                        <td className="py-3 pr-3 text-[var(--text)]">FINALIZED</td>
                        <td className="py-3 pr-3 text-[var(--text-muted)]">{formatDateTime(item.reported_at)}</td>
                        <td className="py-3 pr-3">
                          <Button type="button" size="sm" variant="secondary" onClick={() => openCase(item)}>
                            {isPatientViewer ? 'Open record' : 'Open case'}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            <section className="bg-white rounded-2xl border border-[var(--border)] p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-3">
                <Activity size={16} className="text-[var(--deep-navy)]" />
                <h2 className="text-base font-semibold text-[var(--deep-navy)]">Patient Progress</h2>
              </div>

              {patientProgress.length === 0 ? (
                <p className="text-sm text-[var(--text-muted)]">No patient progress records in this view.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {patientProgress.map((item) => (
                    <div key={`progress-${item.patient.patient_id}`} className="rounded-xl border border-[var(--border)] p-3">
                      <p className="text-sm font-semibold text-[var(--deep-navy)]">
                        {item.patient.first_name} {item.patient.last_name}
                      </p>
                      <p className="text-xs text-[var(--text-muted)] mt-1">
                        Finalized reports: {item.total_finalized_reports}
                      </p>
                      <p className="text-xs text-[var(--text-muted)] mt-1">
                        Latest severity: {item.latest_severity}
                      </p>
                      <p className="text-xs text-[var(--text-muted)] mt-1">
                        Last update: {formatDateTime(item.latest_reported_at)}
                      </p>
                      <div className="mt-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          onClick={() => openCase({
                            patient: item.patient,
                            transaction_id: item.latest_transaction_id,
                          })}
                        >
                          {isPatientViewer ? 'Open latest record' : 'Open latest case'}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </AppLayout>
  )
}
