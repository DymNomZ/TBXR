import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import AnnotationPanel from './AnnotationPanel'
import { AuthProvider } from '../../context/AuthContext'

// T06 regression — F-2.5.1 (submit completes + redirects) and
// F-2.5.2 (empty canvas blocked with HTTP 400).

const TX_ID = '123e4567-e89b-12d3-a456-426614174000'
const ANNOTATE_URL = `/api/imaging/xray/${TX_ID}/annotate/`

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

function LocationDisplay() {
  const { pathname } = useLocation()
  return <div data-testid="location-display">{pathname}</div>
}

const NORMALIZED_BOXES = [
  { id: 'a', x: 0.1, y: 0.12, width: 0.2, height: 0.18, label: 'nodule', shape: 'rectangle' },
  { id: 'b', x: 0.45, y: 0.3, width: 0.15, height: 0.2, label: 'cavity', shape: 'circle' },
]

function renderPanel({ boxes = [], onSubmitStatus = 201, onSubmitBody = null } = {}) {
  localStorage.setItem('user', JSON.stringify({ role: 'RADIOLOGIST' }))
  const fetchMock = vi.fn((url, options = {}) => {
    if (String(url) === ANNOTATE_URL) {
      const payload = JSON.parse(options.body)
      return jsonResponse(
        onSubmitBody ?? { transaction_id: TX_ID, annotation_id: 1, status: 'COMPLETED', _echo: payload },
        onSubmitStatus,
      )
    }
    return jsonResponse({})
  })
  vi.stubGlobal('fetch', fetchMock)

  const utils = render(
    <MemoryRouter initialEntries={[`/radiologist/review/${TX_ID}`]}>
      <AuthProvider>
        <Routes>
          <Route
            path="/radiologist/review/:transactionId"
            element={
              <AnnotationPanel
                transactionId={TX_ID}
                boxes={boxes}
                onDeleteBox={() => {}}
                isCompleted={false}
                readOnly={false}
              />
            }
          />
        </Routes>
        <LocationDisplay />
      </AuthProvider>
    </MemoryRouter>,
  )
  return { ...utils, fetchMock }
}

describe('AnnotationPanel (T06 — F-2.5.1/F-2.5.2)', () => {
  it('F-2.5.1 posts ROIs with labels + clinical note and redirects to the queue', async () => {
    vi.useFakeTimers()
    const { fetchMock } = renderPanel({ boxes: NORMALIZED_BOXES })

    fireEvent.change(
      screen.getByPlaceholderText('Enter your findings, observations, and recommendations…'),
      { target: { value: 'Left upper lobe opacity.' } },
    )
    fireEvent.click(screen.getByRole('button', { name: /Submit Findings/i }))
    await act(async () => {})

    const call = fetchMock.mock.calls.find(([url]) => String(url) === ANNOTATE_URL)
    expect(call).toBeDefined()
    const body = JSON.parse(call[1].body)
    expect(body.notes).toBe('Left upper lobe opacity.')
    expect(body.bounding_boxes).toHaveLength(2)
    expect(body.bounding_boxes[0]).toMatchObject({ label: 'nodule', shape: 'rectangle' })
    expect(body.bounding_boxes[1]).toMatchObject({ label: 'cavity', shape: 'circle' })

    expect(screen.getByText('Findings submitted. Redirecting…')).toBeInTheDocument()
    expect(screen.getByTestId('location-display')).toHaveTextContent(`/radiologist/review/${TX_ID}`)
    act(() => vi.advanceTimersByTime(1200))
    expect(screen.getByTestId('location-display')).toHaveTextContent('/dashboard/radiologist')
  })

  it('F-2.5.2 surfaces the HTTP 400 when submitting an empty canvas', async () => {
    const { fetchMock } = renderPanel({
      boxes: [],
      onSubmitStatus: 400,
      onSubmitBody: { errors: { bounding_boxes: 'At least one annotation is required.' } },
    })

    fireEvent.click(screen.getByRole('button', { name: /Submit Findings/i }))

    expect(
      await screen.findByText('At least one annotation is required.'),
    ).toBeInTheDocument()

    const call = fetchMock.mock.calls.find(([url]) => String(url) === ANNOTATE_URL)
    expect(JSON.parse(call[1].body).bounding_boxes).toEqual([])
  })

  it('does not redirect when the submit fails', async () => {
    renderPanel({
      boxes: [],
      onSubmitStatus: 400,
      onSubmitBody: { errors: { bounding_boxes: 'At least one annotation is required.' } },
    })
    fireEvent.click(screen.getByRole('button', { name: /Submit Findings/i }))
    await waitFor(() =>
      expect(screen.getByText('At least one annotation is required.')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('location-display')).toHaveTextContent(`/radiologist/review/${TX_ID}`)
  })
})
