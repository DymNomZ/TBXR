import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest'
import { render, screen, fireEvent, within, act } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AnnotationReviewPage from './AnnotationReviewPage'
import { AuthProvider } from '../context/AuthContext'

// T06 regression — integration of the annotation canvas, the bounding-box
// panel and the viewer controls on the review page.

const TX_ID = '123e4567-e89b-12d3-a456-426614174000'
const DETAIL_URL = `/api/imaging/xray/${TX_ID}/`
const ANNOTATE_URL = `/api/imaging/xray/${TX_ID}/annotate/`
const RELEASE_URL = `/api/imaging/xray/${TX_ID}/release/`

const CANVAS_W = 200
const CANVAS_H = 100

globalThis.ResizeObserver = globalThis.ResizeObserver ?? class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

let originalOffsetWidth
let originalOffsetHeight
let originalGetBoundingClientRect

beforeAll(() => {
  originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth')
  originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight')
  originalGetBoundingClientRect = HTMLElement.prototype.getBoundingClientRect
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
    configurable: true,
    get() { return CANVAS_W },
  })
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
    configurable: true,
    get() { return CANVAS_H },
  })
  HTMLElement.prototype.getBoundingClientRect = function () {
    return { width: CANVAS_W, height: CANVAS_H, left: 0, top: 0, right: CANVAS_W, bottom: CANVAS_H, x: 0, y: 0 }
  }
})

afterAll(() => {
  if (originalOffsetWidth) Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOffsetWidth)
  if (originalOffsetHeight) Object.defineProperty(HTMLElement.prototype, 'offsetHeight', originalOffsetHeight)
  HTMLElement.prototype.getBoundingClientRect = originalGetBoundingClientRect
})

const BASE_BODY = {
  transaction_id: TX_ID,
  patient: { patient_id: 101, first_name: 'T06', last_name: 'Patient' },
  status: 'PENDING',
  display_image: null,
  ai_result: null,
  annotations: [],
}

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

function renderPage() {
  localStorage.setItem('user', JSON.stringify({ role: 'RADIOLOGIST' }))
  const fetchMock = vi.fn((url) => {
    const u = String(url)
    if (u === DETAIL_URL) return jsonResponse(BASE_BODY, 200)
    if (u === RELEASE_URL) return jsonResponse(null, 204)
    if (u === ANNOTATE_URL) {
      return jsonResponse({ transaction_id: TX_ID, annotation_id: 1, status: 'COMPLETED' }, 201)
    }
    if (u.includes('/history/') || u.includes('/progression/')) return jsonResponse([])
    return jsonResponse({})
  })
  vi.stubGlobal('fetch', fetchMock)

  const utils = render(
    <MemoryRouter initialEntries={[`/radiologist/review/${TX_ID}`]}>
      <AuthProvider>
        <Routes>
          <Route path="/radiologist/review/:transactionId" element={<AnnotationReviewPage />} />
          <Route path="/dashboard/radiologist" element={<div data-testid="queue-page">Queue</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
  return { ...utils, fetchMock }
}

function canvasRoot() {
  return screen.getByTitle('Rectangle').parentElement.parentElement
}

function selectTool(title) {
  fireEvent.click(screen.getByTitle(title))
}

function drag(from, to, { button = 0, steps = 1 } = {}) {
  const root = canvasRoot()
  fireEvent.mouseDown(root, { clientX: from.x, clientY: from.y, button })
  for (let i = 1; i <= steps; i += 1) {
    const x = from.x + ((to.x - from.x) * i) / steps
    const y = from.y + ((to.y - from.y) * i) / steps
    fireEvent.mouseMove(root, { clientX: x, clientY: y, button })
  }
  fireEvent.mouseUp(root, { clientX: to.x, clientY: to.y, button })
}

function drawRectangle(from, to, label) {
  selectTool('Rectangle')
  drag(from, to)
  const input = screen.getByPlaceholderText('Enter label…')
  fireEvent.change(input, { target: { value: label } })
  fireEvent.click(within(input.parentElement).getByText('Add'))
}

function boundingBoxCard() {
  return screen.getByText('Bounding Boxes').closest('.bg-white')
}

function panelBoxCount() {
  return within(boundingBoxCard()).queryAllByRole('button').length
}

function canvasShapeCount() {
  const svg = canvasRoot().querySelector('svg.overflow-visible')
  return svg ? svg.querySelectorAll('rect, ellipse, polyline').length : 0
}

function onCanvasShapeButtons() {
  return [...canvasRoot().querySelectorAll('button')].filter((b) => b.className.includes('rounded-full'))
}

describe('AnnotationReviewPage (T06 integration)', () => {
  it('panel delete is undoable: undo restores the deleted ROI without losing others', async () => {
    renderPage()
    await screen.findByTitle('Rectangle')

    drawRectangle({ x: 20, y: 10 }, { x: 70, y: 40 }, 'roi-1')
    drawRectangle({ x: 100, y: 10 }, { x: 150, y: 40 }, 'roi-2')
    expect(panelBoxCount()).toBe(2)

    // Delete the first ROI from the Bounding Boxes panel.
    fireEvent.click(within(boundingBoxCard()).getAllByRole('button')[0])
    expect(panelBoxCount()).toBe(1)

    // Undo must restore the panel-deleted ROI and keep the other one.
    fireEvent.click(screen.getByTitle('Undo'))
    expect(panelBoxCount()).toBe(2)
  })

  it('right-button drag pans without creating a region of interest', async () => {
    renderPage()
    await screen.findByTitle('Rectangle')

    // Zoom in so the viewer enables panning.
    fireEvent.click(screen.getByTitle('Zoom in'))

    drag({ x: 20, y: 10 }, { x: 70, y: 40 }, { button: 2 })

    expect(screen.queryByPlaceholderText('Enter label…')).not.toBeInTheDocument()
    expect(panelBoxCount()).toBe(0)
  })

  it('panel delete removes the drawn shape from the canvas, not just the list', async () => {
    renderPage()
    await screen.findByTitle('Rectangle')

    drawRectangle({ x: 20, y: 10 }, { x: 70, y: 40 }, 'roi-1')
    drawRectangle({ x: 100, y: 10 }, { x: 150, y: 40 }, 'roi-2')
    expect(canvasShapeCount()).toBe(2)

    fireEvent.click(within(boundingBoxCard()).getAllByRole('button')[0])

    expect(panelBoxCount()).toBe(1)
    expect(canvasShapeCount()).toBe(1)
  })

  it('on-canvas per-shape X control deletes the shape', async () => {
    renderPage()
    await screen.findByTitle('Rectangle')

    drawRectangle({ x: 20, y: 10 }, { x: 70, y: 40 }, 'roi-1')
    expect(canvasShapeCount()).toBe(1)

    fireEvent.click(onCanvasShapeButtons()[0])

    expect(canvasShapeCount()).toBe(0)
    expect(panelBoxCount()).toBe(0)
  })

  it('F-2.5.1 submitting a drawn ROI completes the case and returns to the queue', async () => {
    vi.useFakeTimers()
    const { fetchMock } = renderPage()
    await act(async () => {})

    drawRectangle({ x: 20, y: 10 }, { x: 70, y: 40 }, 'nodule')
    fireEvent.change(
      screen.getByPlaceholderText('Enter your findings, observations, and recommendations…'),
      { target: { value: 'Opacities noted.' } },
    )
    fireEvent.click(screen.getByRole('button', { name: /Submit Findings/i }))
    await act(async () => {})

    const call = fetchMock.mock.calls.find(([url]) => String(url) === ANNOTATE_URL)
    expect(call).toBeDefined()
    const body = JSON.parse(call[1].body)
    expect(body.bounding_boxes).toHaveLength(1)
    expect(body.bounding_boxes[0].label).toBe('nodule')
    expect(body.notes).toBe('Opacities noted.')

    act(() => vi.advanceTimersByTime(1200))
    expect(screen.getByTestId('queue-page')).toBeInTheDocument()
  })
})
