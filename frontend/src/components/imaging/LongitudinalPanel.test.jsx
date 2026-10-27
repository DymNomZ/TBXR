import { render, screen, waitFor } from '@testing-library/react'
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
    score: 0.42,
    delta: 0.01,
  },
  {
    transaction_id: 'tx-002',
    timestamp: '2024-02-01T00:00:00Z',
    status: 'increased_risk',
    score: 0.72,
    delta: 0.3,
  },
  {
    transaction_id: 'tx-003',
    timestamp: '2024-03-01T00:00:00Z',
    status: 'decreased_risk',
    score: 0.38,
    delta: -0.34,
  },
]

describe('LongitudinalPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the AI progression trend and status labels', async () => {
    const fetchMock = vi.fn((url) => {
      if (url.includes('/history/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(HISTORY_PAYLOAD) })
      }
      if (url.includes('/progression/overrides/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
      }
      if (url.includes('/progression/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(PROGRESSION_PAYLOAD) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<LongitudinalPanel patientId="PT-100" />)

    expect(await screen.findByText('AI risk trend')).toBeInTheDocument()
    expect(screen.getAllByText('Stable').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Deterioration').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Improvement').length).toBeGreaterThan(0)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/imaging/patients/PT-100/progression/', { credentials: 'include' })
    })
  })
})
