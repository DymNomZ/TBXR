import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import AnnotationReviewPage from './AnnotationReviewPage'

// T05 regression — F-2.2.2 (C-01 conflict banner, C-02 read-only gate)
// plus F-02 follow-up: the owner releases the lock on the way out.

// jsdom lacks these browser APIs used by the heatmap/overlay components.
globalThis.ResizeObserver = globalThis.ResizeObserver ?? class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const TX_ID = '123e4567-e89b-12d3-a456-426614174000'
const DETAIL_URL = `/api/imaging/xray/${TX_ID}/`
const RELEASE_URL = `/api/imaging/xray/${TX_ID}/release/`

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

const BASE_BODY = {
  transaction_id: TX_ID,
  patient: { patient_id: 101, first_name: 'Juan', last_name: 'Dela Cruz' },
  status: 'IN_REVIEW',
  display_image: null,
  ai_result: null,
  annotations: [],
}

const LOCKED_BODY = {
  ...BASE_BODY,
  detail: 'This case is currently locked by another radiologist.',
  active_reviewer: 't05-rad-a',
  lock_timestamp: '2026-10-13T02:00:00Z',
}

function renderPage({ detailStatus = 409, detailBody = LOCKED_BODY } = {}) {
  localStorage.setItem('user', JSON.stringify({ role: 'RADIOLOGIST' }))
  const fetchMock = vi.fn((url) => {
    const u = String(url)
    if (u === DETAIL_URL) return jsonResponse(detailBody, detailStatus)
    if (u.includes('/history/') || u.includes('/progression/')) return jsonResponse([])
    if (u === RELEASE_URL) return jsonResponse(null, 204)
    return jsonResponse({})
  })
  vi.stubGlobal('fetch', fetchMock)

  const utils = render(
    <MemoryRouter initialEntries={[`/radiologist/review/${TX_ID}`]}>
      <AuthProvider>
        <Routes>
          <Route path="/radiologist/review/:transactionId" element={<AnnotationReviewPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
  return { ...utils, fetchMock }
}

function calledWith(fetchMock, urlFragment) {
  return fetchMock.mock.calls.some(([url]) => String(url).includes(urlFragment))
}

describe('AnnotationReviewPage (T05)', () => {
  it('C-01 shows the active-reviewer warning in read-only mode on 409', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Read-only mode')).toBeInTheDocument()
    })
    expect(screen.getByText('t05-rad-a')).toBeInTheDocument()
    expect(screen.getByText(/currently locked by another radiologist/i)).toBeInTheDocument()
  })

  it('C-02 disables save controls for the non-owner', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Locked by another reviewer' })).toBeDisabled()
    })
    const notes = screen.getByPlaceholderText('This case is locked by another reviewer.')
    expect(notes).toBeDisabled()
  })

  it('does not release the lock when the viewer is not the owner', async () => {
    const { fetchMock, unmount } = renderPage()
    await waitFor(() => {
      expect(screen.getByText('Read-only mode')).toBeInTheDocument()
    })
    unmount()
    expect(calledWith(fetchMock, '/release/')).toBe(false)
  })

  it('releases the lock when the owner leaves the page', async () => {
    const { fetchMock, unmount } = renderPage({
      detailStatus: 200,
      detailBody: { ...BASE_BODY, status: 'PENDING' },
    })
    await waitFor(() => {
      expect(screen.getByText('Juan Dela Cruz')).toBeInTheDocument()
    })
    unmount()
    expect(calledWith(fetchMock, '/release/')).toBe(true)
  })
})
