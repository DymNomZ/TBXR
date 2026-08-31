import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import ReportWritePage from './ReportWritePage'
import { AuthProvider } from '../context/AuthContext'

const TX_ID = 'xray-123'
const REPORT_URL = `/api/imaging/xray/${TX_ID}/report/`

// Verbatim placeholders from ReportWritePage.jsx (textareas have no aria-labels).
const PLACEHOLDERS = {
  findings: 'e.g., Right upper lobe opacity with cavitation and surrounding consolidation.',
  impression: 'e.g., Suspicious for active pulmonary tuberculosis requiring urgent follow-up.',
  recommendation: 'e.g., Recommend sputum AFB and GeneXpert testing with specialist review.',
}

const TEXT_FIELDS = ['findings', 'impression', 'recommendation']

const REPORT_DATA = {
  findings: 'Right upper lobe opacity with cavitation.',
  impression: 'Suspicious for active pulmonary tuberculosis.',
  recommendation: 'Recommend sputum AFB and GeneXpert testing.',
  severity: 'MODERATE',
}

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

// Mount GET is dispatched on reportExists; save calls echo the request JSON back.
function stubFetch({ reportExists = false, saveStatus = 200, saveBody = null } = {}) {
  const fetchMock = vi.fn((url, options = {}) => {
    const method = String(options.method || 'GET').toUpperCase()
    if (method === 'GET') {
      return reportExists
        ? jsonResponse(REPORT_DATA, 200)
        : jsonResponse({ detail: 'Report not found for this X-ray.' }, 404)
    }
    const payload = JSON.parse(options.body)
    return jsonResponse(saveBody ?? { ...payload, id: 1 }, saveStatus)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function seedUser() {
  localStorage.setItem('user', JSON.stringify({ role: 'RADIOLOGIST' }))
}

function LocationDisplay() {
  const { pathname } = useLocation()
  return <div data-testid="location-display">{pathname}</div>
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/radiologist/report/${TX_ID}`]}>
      <AuthProvider>
        <Routes>
          <Route path="/radiologist/report/:transactionId" element={<ReportWritePage />} />
        </Routes>
        <LocationDisplay />
      </AuthProvider>
    </MemoryRouter>,
  )
}

async function fillEveryField() {
  for (const field of TEXT_FIELDS) {
    await userEvent.type(screen.getByPlaceholderText(PLACEHOLDERS[field]), REPORT_DATA[field])
  }
  await userEvent.selectOptions(screen.getByLabelText('Severity classification'), REPORT_DATA.severity)
}

describe('ReportWritePage', () => {
  it('blocks an empty submit with validation errors and no save request', async () => {
    seedUser()
    const fetchMock = stubFetch()
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Submit Report/i }))

    expect(screen.getAllByText('Required.')).toHaveLength(4)
    expect(screen.getByText('Please complete all required fields before submitting.')).toBeInTheDocument()

    // Only the mount GET ran; the blocked submit issues no save request.
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe(REPORT_URL)
    expect(fetchMock.mock.calls[0][1]?.method ?? 'GET').toBe('GET')
  })

  it.each(TEXT_FIELDS)('flags only %s as required when the other fields are complete', async (missingField) => {
    seedUser()
    stubFetch()
    renderPage()
    await act(async () => {})

    for (const field of TEXT_FIELDS) {
      if (field !== missingField) {
        await userEvent.type(screen.getByPlaceholderText(PLACEHOLDERS[field]), REPORT_DATA[field])
      }
    }
    await userEvent.selectOptions(screen.getByLabelText('Severity classification'), REPORT_DATA.severity)

    fireEvent.click(screen.getByRole('button', { name: /Submit Report/i }))
    expect(screen.getAllByText('Required.')).toHaveLength(1)
  })

  it('flags severity as required when all text fields are complete', async () => {
    seedUser()
    stubFetch()
    renderPage()
    await act(async () => {})

    for (const field of TEXT_FIELDS) {
      await userEvent.type(screen.getByPlaceholderText(PLACEHOLDERS[field]), REPORT_DATA[field])
    }

    fireEvent.click(screen.getByRole('button', { name: /Submit Report/i }))
    expect(screen.getAllByText('Required.')).toHaveLength(1)
  })

  it('clears a field error once the user types into the flagged field', async () => {
    seedUser()
    stubFetch()
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Submit Report/i }))
    expect(screen.getAllByText('Required.')).toHaveLength(4)

    await userEvent.type(screen.getByPlaceholderText(PLACEHOLDERS.findings), REPORT_DATA.findings)

    expect(screen.getAllByText('Required.')).toHaveLength(3)
  })

  it('validates a field after it is blurred while empty', async () => {
    seedUser()
    stubFetch()
    renderPage()

    fireEvent.blur(screen.getByPlaceholderText(PLACEHOLDERS.findings))

    expect(screen.getAllByText('Required.')).toHaveLength(1)
  })

  it('saves a draft via PATCH when a report already exists, with CSRF header', async () => {
    seedUser()
    document.cookie = 'csrftoken=testtoken;'
    const fetchMock = stubFetch({ reportExists: true })
    renderPage()
    await screen.findByDisplayValue(REPORT_DATA.findings)

    fireEvent.click(screen.getByRole('button', { name: /Save Draft/i }))

    await waitFor(() => {
      const patchCall = fetchMock.mock.calls.find(
        ([url, options]) => url === REPORT_URL && options?.method === 'PATCH',
      )
      expect(patchCall).toBeDefined()
      expect(JSON.parse(patchCall[1].body)).toEqual({ ...REPORT_DATA, status: 'DRAFT' })
      expect(patchCall[1].headers['X-CSRFToken']).toBe('testtoken')
    })
    expect(await screen.findByText('Draft saved successfully.')).toBeInTheDocument()
  })

  it('creates a draft via POST when no report exists yet', async () => {
    seedUser()
    const fetchMock = stubFetch()
    renderPage()
    await act(async () => {})
    await fillEveryField()

    fireEvent.click(screen.getByRole('button', { name: /Save Draft/i }))

    await waitFor(() => {
      const postCall = fetchMock.mock.calls.find(
        ([url, options]) => url === REPORT_URL && options?.method === 'POST',
      )
      expect(postCall).toBeDefined()
      expect(JSON.parse(postCall[1].body)).toEqual({ ...REPORT_DATA, status: 'DRAFT' })
    })
    expect(await screen.findByText('Draft saved successfully.')).toBeInTheDocument()
  })

  it('submits with SUBMITTED status and navigates to the radiologist dashboard', async () => {
    seedUser()
    vi.useFakeTimers()
    const fetchMock = stubFetch()
    renderPage()
    await act(async () => {})

    fireEvent.change(screen.getByPlaceholderText(PLACEHOLDERS.findings), { target: { value: REPORT_DATA.findings } })
    fireEvent.change(screen.getByPlaceholderText(PLACEHOLDERS.impression), { target: { value: REPORT_DATA.impression } })
    fireEvent.change(screen.getByPlaceholderText(PLACEHOLDERS.recommendation), { target: { value: REPORT_DATA.recommendation } })
    fireEvent.change(screen.getByLabelText('Severity classification'), { target: { value: REPORT_DATA.severity } })

    fireEvent.click(screen.getByRole('button', { name: /Submit Report/i }))
    await act(async () => {})

    expect(screen.getByText('Report submitted successfully.')).toBeInTheDocument()
    const postCall = fetchMock.mock.calls.find(
      ([url, options]) => url === REPORT_URL && options?.method === 'POST',
    )
    expect(postCall).toBeDefined()
    expect(JSON.parse(postCall[1].body)).toEqual({ ...REPORT_DATA, status: 'SUBMITTED' })

    expect(screen.getByTestId('location-display')).toHaveTextContent(`/radiologist/report/${TX_ID}`)
    act(() => vi.advanceTimersByTime(1200))
    expect(screen.getByTestId('location-display')).toHaveTextContent('/dashboard/radiologist')
  })

  it('maps server-side field errors onto the form after a 400', async () => {
    seedUser()
    stubFetch({
      saveStatus: 400,
      saveBody: { findings: ['Findings text is invalid.'], severity: ['Severity is invalid.'] },
    })
    renderPage()
    await act(async () => {})
    await fillEveryField()

    fireEvent.click(screen.getByRole('button', { name: /Submit Report/i }))
    await act(async () => {})

    expect(screen.getByText('Findings text is invalid.')).toBeInTheDocument()
    expect(screen.getByText('Severity is invalid.')).toBeInTheDocument()
    expect(screen.getByText('Submission is incomplete.')).toBeInTheDocument()
  })

  it('pre-fills the form from an existing report on load', async () => {
    seedUser()
    stubFetch({ reportExists: true })
    renderPage()

    expect(await screen.findByDisplayValue(REPORT_DATA.findings)).toBeInTheDocument()
    expect(screen.getByDisplayValue(REPORT_DATA.impression)).toBeInTheDocument()
    expect(screen.getByDisplayValue(REPORT_DATA.recommendation)).toBeInTheDocument()
    expect(screen.getByLabelText('Severity classification')).toHaveValue('MODERATE')
    expect(screen.getByText('4/4 sections complete')).toBeInTheDocument()
  })

  it('shows an error banner when the report draft cannot be loaded', async () => {
    seedUser()
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({ detail: 'Server exploded.' }, 500)))
    renderPage()

    expect(await screen.findByText('Unable to load report draft.')).toBeInTheDocument()
  })

  it('shows a success banner after submitting', async () => {
    seedUser()
    stubFetch()
    renderPage()
    await act(async () => {})
    await fillEveryField()

    fireEvent.click(screen.getByRole('button', { name: /Submit Report/i }))

    expect(await screen.findByText('Report submitted successfully.')).toBeInTheDocument()
  })
})