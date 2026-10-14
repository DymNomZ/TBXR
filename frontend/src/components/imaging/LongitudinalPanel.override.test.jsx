import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import LongitudinalPanel from './LongitudinalPanel'

const HISTORY_PAYLOAD = [
  {
    transaction_id: 'tx-001',
    upload_timestamp: '2024-01-01T00:00:00Z',
    display_image: '',
    status: 'PENDING',
    ai_result: { risk_label: 'LOW', risk_score: 0.2 },
  },
  {
    transaction_id: 'tx-002',
    upload_timestamp: '2024-02-01T00:00:00Z',
    display_image: '',
    status: 'COMPLETED',
    ai_result: { risk_label: 'MEDIUM', risk_score: 0.7 },
  },
]

const PROGRESSION_PAYLOAD = [
  {
    transaction_id: 'tx-001',
    timestamp: '2024-01-01T00:00:00Z',
    status: 'stable',
    score: 0.4,
    delta: 0.01,
  },
  {
    transaction_id: 'tx-002',
    timestamp: '2024-02-01T00:00:00Z',
    status: 'increased_risk',
    score: 0.72,
    delta: 0.3,
  },
]

const OVERRIDE_RESPONSE = {
  transaction_id: 'tx-001',
  timestamp: '2024-02-01T00:00:00Z',
  status: 'decreased_risk',
  source: 'manual_override',
  is_overridden: true,
  clinical_note: 'Clinical override based on review findings.',
  overridden_by: 7,
  override_timestamp: '2024-02-02T00:00:00Z',
  audit_log_id: 11,
}

const OVERRIDE_HISTORY_PAYLOAD = [
  {
    id: 11,
    transaction_id: 'tx-001',
    xray_timestamp: '2024-02-01T00:00:00Z',
    previous_status: 'increased_risk',
    new_status: 'decreased_risk',
    clinical_note: 'Clinical override based on review findings.',
    created_at: '2024-02-02T00:00:00Z',
    radiologist: {
      id: 7,
      username: 'rad1',
      first_name: 'Rad',
      last_name: 'One',
    },
  },
]

describe('LongitudinalPanel override UI', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.setItem('user', JSON.stringify({ role: 'RADIOLOGIST', id: 7, username: 'rad1' }))
  })

  it('opens an override modal, validates note, and submits the selected status', async () => {
    let overrideHistoryCalls = 0
    const fetchMock = vi.fn((url) => {
      if (url.includes('/history/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(HISTORY_PAYLOAD) })
      }
      if (url.includes('/progression/overrides/')) {
        overrideHistoryCalls += 1
        const payload = overrideHistoryCalls > 1 ? OVERRIDE_HISTORY_PAYLOAD : []
        return Promise.resolve({ ok: true, json: () => Promise.resolve(payload) })
      }
      if (url.includes('/progression/')) {
        if (url.includes('/override/')) {
          return Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve(OVERRIDE_RESPONSE) })
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(PROGRESSION_PAYLOAD) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<LongitudinalPanel patientId="PT-100" />)

    expect(await screen.findByText('AI risk trend')).toBeInTheDocument()

    fireEvent.click(screen.getByText('40% risk').closest('button'))
    
    fireEvent.click(screen.getByRole('button', { name: /override status/i }))
    expect(screen.getByLabelText(/Progression status/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /submit override/i }))
    expect(screen.getByText('Clinical note is required.')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/Clinical note/i), {
      target: { value: 'Clinical override based on review findings.' },
    })
    fireEvent.change(screen.getByLabelText(/Progression status/i), {
      target: { value: 'decreased_risk' },
    })

    fireEvent.click(screen.getByRole('button', { name: /submit override/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/imaging/cases/tx-001/progression/override/',
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
        }),
      )
    })

    expect(await screen.findByText('Clinical override based on review findings.')).toBeInTheDocument()
    expect(screen.getByText('Manual override')).toBeInTheDocument()
    expect(screen.getByText(/Case: tx-001/i)).toBeInTheDocument()
  })

  it('keeps the override target on the newest scan when only hovering an older scan', async () => {
    const fetchMock = vi.fn((url) => {
      if (url.includes('/history/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(HISTORY_PAYLOAD) })
      }
      if (url.includes('/progression/overrides/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
      }
      if (url.includes('/progression/')) {
        if (url.includes('/override/')) {
          return Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve(OVERRIDE_RESPONSE) })
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(PROGRESSION_PAYLOAD) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<LongitudinalPanel patientId="PT-100" />)

    expect(await screen.findByText('AI risk trend')).toBeInTheDocument()

    // Hover an older scan without clicking it. This must NOT retarget the override.
    fireEvent.mouseEnter(screen.getByText('40% risk').closest('button'))

    fireEvent.click(screen.getByRole('button', { name: /override status/i }))
    fireEvent.change(screen.getByLabelText(/Clinical note/i), {
      target: { value: 'Hover-only should not retarget.' },
    })
    fireEvent.change(screen.getByLabelText(/Progression status/i), {
      target: { value: 'decreased_risk' },
    })
    fireEvent.click(screen.getByRole('button', { name: /submit override/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/imaging/cases/tx-002/progression/override/',
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
        }),
      )
    })

    expect(fetchMock).not.toHaveBeenCalledWith(
      '/api/imaging/cases/tx-001/progression/override/',
      expect.anything(),
    )
  })
})
