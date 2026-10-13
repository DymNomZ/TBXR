import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../../context/AuthContext'
import RadiologistDashboardPage from './RadiologistDashboardPage'

// T05 regression — F-2.1.1 (Q-02 queue rendering) and F-2.1.3 (E-01 empty state).

const QUEUE_URL = '/api/imaging/queue/'

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

const RECORD = {
  transaction_id: '123e4567-e89b-12d3-a456-426614174000',
  patient: { patient_id: 101, first_name: 'Juan', last_name: 'Dela Cruz' },
  uploader: { username: 'tech-one' },
  upload_timestamp: '2026-10-01T08:00:00Z',
  status: 'AI_REVIEWED',
  file_format: 'png',
  ai_result: { risk_score: 0.91, risk_label: 'HIGH', model_version: 'v-t05' },
}

// The page issues 5 stat-count calls and one paginated record call. Only the
// record call carries `page=`, so route on that.
function stubFetch(results) {
  vi.stubGlobal('fetch', vi.fn((url) => {
    const u = String(url)
    if (u.includes('/notifications/')) return jsonResponse([])
    if (u.includes(QUEUE_URL)) {
      if (u.includes('page=')) {
        return jsonResponse({ count: results.length, next: null, previous: null, results })
      }
      return jsonResponse({ count: results.length, results: [] })
    }
    return jsonResponse({})
  }))
}

function renderPage() {
  localStorage.setItem('user', JSON.stringify({ role: 'RADIOLOGIST' }))
  return render(
    <MemoryRouter initialEntries={['/dashboard/radiologist']}>
      <AuthProvider>
        <RadiologistDashboardPage />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('RadiologistDashboardPage (T05)', () => {
  it('Q-02 renders transaction ID, patient, status and AI score columns', async () => {
    stubFetch([RECORD])
    renderPage()

    await waitFor(() => {
      expect(screen.getByText(RECORD.transaction_id)).toBeInTheDocument()
    })
    expect(screen.getByText('Juan')).toBeInTheDocument()
    expect(screen.getByText('Dela Cruz')).toBeInTheDocument()
    expect(screen.getByText('AI Reviewed')).toBeInTheDocument()
    const riskBadge = screen.getByText(/91%/)
    expect(riskBadge.textContent).toContain('HIGH')
    expect(screen.getByText('tech-one')).toBeInTheDocument()
  })

  it('E-01 shows the empty state when a filter has zero matches', async () => {
    stubFetch([])
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('No records found.')).toBeInTheDocument()
    })
  })
})
