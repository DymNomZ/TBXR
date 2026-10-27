import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../../context/AuthContext'
import AnalyticsDashboardPage from './AnalyticsDashboardPage'

const SUMMARY_URL = '/api/analytics/summary/'
const EXPORT_URL = '/api/analytics/export/'

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    blob: () => Promise.resolve(new Blob(['ok'], { type: 'text/plain' })),
  })
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/dashboard/analytics']}>
      <AuthProvider>
        <Routes>
          <Route path="/dashboard/analytics" element={<AnalyticsDashboardPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('AnalyticsDashboardPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.setItem('user', JSON.stringify({ role: 'RADIOLOGIST' }))
    vi.stubGlobal('fetch', vi.fn((url, options = {}) => {
      if (String(url).startsWith(SUMMARY_URL)) {
        return jsonResponse({
          filters: {
            date_from: null,
            date_to: null,
            severity: null,
          },
          cases: {
            total: 8,
            by_status: { COMPLETED: 5, PENDING: 3 },
            by_ai_risk_label: { LOW: 2, MODERATE: 3, HIGH: 3 },
          },
          reports: {
            total: 6,
            by_severity: { MODERATE: 2, CRITICAL: 4 },
            by_status: { DRAFT: 1, FINALIZED: 5 },
          },
        })
      }

      if (String(url) === EXPORT_URL && options.method === 'POST') {
        return jsonResponse({}, 200)
      }

      return jsonResponse({}, 404)
    }))

    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test-url')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  })

  it('renders analytics summary, applies filters, and posts CSV/PDF exports', async () => {
    renderPage()

    expect(await screen.findByText('Analytics Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Case Status Distribution')).toBeInTheDocument()
    expect(screen.getByText('Report Severity Breakdown')).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Severity'), 'CRITICAL')
    await userEvent.type(screen.getByLabelText('Date from'), '2026-09-01')
    await userEvent.type(screen.getByLabelText('Date to'), '2026-09-15')
    await userEvent.click(screen.getByRole('button', { name: /apply/i }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/analytics/summary/?date_from=2026-09-01&date_to=2026-09-15&severity=CRITICAL',
        { credentials: 'include' },
      )
    })

    await userEvent.click(screen.getByRole('button', { name: /export csv/i }))
    await userEvent.click(screen.getByRole('button', { name: /export pdf/i }))

    await waitFor(() => {
      const exportCalls = fetch.mock.calls.filter((call) => call[0] === EXPORT_URL)
      expect(exportCalls).toHaveLength(2)

      const csvBody = JSON.parse(exportCalls[0][1].body)
      const pdfBody = JSON.parse(exportCalls[1][1].body)

      expect(csvBody.format).toBe('csv')
      expect(pdfBody.format).toBe('pdf')
      expect(csvBody.filters.severity).toBe('CRITICAL')
      expect(csvBody.filters.date_from).toBe('2026-09-01')
      expect(csvBody.filters.date_to).toBe('2026-09-15')
    })
  })
})