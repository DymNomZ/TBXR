import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider } from '../../context/AuthContext'
import PhysicianDashboardPage from './PhysicianDashboardPage'

const DASHBOARD_URL = '/api/physician/dashboard'

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

function LocationDisplay() {
  const location = useLocation()
  return (
    <div data-testid="location-display">
      {location.pathname}
      {'|'}
      {JSON.stringify(location.state ?? {})}
    </div>
  )
}

function renderPage(initialEntry = '/dashboard/physician') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <AuthProvider>
        <Routes>
          <Route path="/dashboard/physician" element={<PhysicianDashboardPage />} />
          <Route path="/patients/:patientId" element={<LocationDisplay />} />
          <Route path="/radiologist/report/:transactionId" element={<LocationDisplay />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('PhysicianDashboardPage', () => {
  it('renders finalized and alert content from physician summary endpoint', async () => {
    localStorage.setItem('user', JSON.stringify({ role: 'PHYSICIAN' }))

    vi.stubGlobal('fetch', vi.fn((url) => {
      if (String(url).startsWith(DASHBOARD_URL)) {
        return jsonResponse({
          summary: {
            finalized_report_count: 2,
            recent_report_count: 2,
            pending_alert_count: 1,
            report_ready_count: 2,
            patient_progress_count: 1,
          },
          finalized_cases: [
            {
              report_id: 1,
              transaction_id: '123e4567-e89b-12d3-a456-426614174001',
              reported_at: '2026-09-06T08:00:00Z',
              severity: 'CRITICAL',
              patient: { patient_id: 101, first_name: 'Juan', last_name: 'Dela Cruz' },
            },
            {
              report_id: 2,
              transaction_id: '123e4567-e89b-12d3-a456-426614174002',
              reported_at: '2026-09-05T08:00:00Z',
              severity: 'MODERATE',
              patient: { patient_id: 102, first_name: 'Maria', last_name: 'Santos' },
            },
          ],
          recent_reports: [
            {
              report_id: 1,
              transaction_id: '123e4567-e89b-12d3-a456-426614174001',
              reported_at: '2026-09-06T08:00:00Z',
              severity: 'CRITICAL',
              patient: { patient_id: 101, first_name: 'Juan', last_name: 'Dela Cruz' },
            },
          ],
          report_ready_items: [
            {
              report_id: 1,
              transaction_id: '123e4567-e89b-12d3-a456-426614174001',
              reported_at: '2026-09-06T08:00:00Z',
              severity: 'CRITICAL',
              patient: { patient_id: 101, first_name: 'Juan', last_name: 'Dela Cruz' },
            },
          ],
          pending_alerts: [
            {
              id: 9,
              message: 'Report ready for Juan Dela Cruz (case 123e4567-e89b-12d3-a456-426614174001).',
              created_at: '2026-09-06T09:00:00Z',
              read_status: false,
              updated_at: '2026-09-06T09:00:00Z',
            },
          ],
          patient_progress: [
            {
              patient: { patient_id: 101, first_name: 'Juan', last_name: 'Dela Cruz' },
              total_finalized_reports: 2,
              latest_transaction_id: '123e4567-e89b-12d3-a456-426614174001',
              latest_reported_at: '2026-09-06T08:00:00Z',
              latest_severity: 'CRITICAL',
              latest_status: 'COMPLETED',
            },
          ],
        })
      }
      return jsonResponse({}, 404)
    }))

    renderPage()

    expect(await screen.findByText('Physician Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Finalized Cases')).toBeInTheDocument()
    expect(screen.getAllByText('Pending Alerts').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Juan Dela Cruz').length).toBeGreaterThan(0)
    expect(screen.getByText(/Report Status:\s*FINALIZED/i)).toBeInTheDocument()
  })

  it('filters by patient search and deep-links to patient case', async () => {
    localStorage.setItem('user', JSON.stringify({ role: 'PHYSICIAN' }))

    vi.stubGlobal('fetch', vi.fn((url) => {
      if (String(url).startsWith(DASHBOARD_URL)) {
        return jsonResponse({
          summary: {
            finalized_report_count: 2,
            recent_report_count: 2,
            pending_alert_count: 0,
            report_ready_count: 2,
            patient_progress_count: 2,
          },
          finalized_cases: [
            {
              report_id: 1,
              transaction_id: '123e4567-e89b-12d3-a456-426614174001',
              reported_at: '2026-09-06T08:00:00Z',
              severity: 'CRITICAL',
              patient: { patient_id: 101, first_name: 'Juan', last_name: 'Dela Cruz' },
            },
            {
              report_id: 2,
              transaction_id: '123e4567-e89b-12d3-a456-426614174002',
              reported_at: '2026-09-05T08:00:00Z',
              severity: 'MODERATE',
              patient: { patient_id: 102, first_name: 'Maria', last_name: 'Santos' },
            },
          ],
          recent_reports: [],
          report_ready_items: [],
          pending_alerts: [],
          patient_progress: [],
        })
      }
      return jsonResponse({}, 404)
    }))

    renderPage('/dashboard/physician?case=123e4567-e89b-12d3-a456-426614174001')

    await screen.findByText('Physician Dashboard')

    await userEvent.type(screen.getByPlaceholderText('Search patient or case ID'), 'Juan')

    expect(screen.getByText('Juan Dela Cruz')).toBeInTheDocument()
    expect(screen.queryByText('Maria Santos')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Open case' }))

    await waitFor(() => {
      expect(screen.getByTestId('location-display')).toHaveTextContent('/radiologist/report/123e4567-e89b-12d3-a456-426614174001')
    })
  })
})
