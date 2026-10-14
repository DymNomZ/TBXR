import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { useState } from 'react'
import { render, screen, fireEvent, within } from '@testing-library/react'
import AnnotationCanvas from './AnnotationCanvas'

// T06 regression — F-2.3.1 (draw rectangle/circle/freehand with labels),
// F-2.3.2 (normalized coordinates), F-2.3.3 (delete + undo, 20-step limit).

// ── jsdom has no layout engine: give every element a stable size so the
//    canvas can convert between screen and element space deterministically.
const CANVAS_W = 200
const CANVAS_H = 100

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

// ── Harness that mirrors how AnnotationReviewPage owns the box state ─────────

function Harness({ initial = [] }) {
  const [boxes, setBoxes] = useState(initial)
  return (
    <div>
      <AnnotationCanvas boxes={boxes} onBoxesChange={setBoxes} />
      <pre data-testid="boxes">{JSON.stringify(boxes)}</pre>
    </div>
  )
}

function readBoxes() {
  return JSON.parse(screen.getByTestId('boxes').textContent)
}

function canvasRoot() {
  // The Rectangle tool button lives inside the canvas root's toolbar.
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

function confirmLabel(label) {
  const input = screen.getByPlaceholderText('Enter label…')
  fireEvent.change(input, { target: { value: label } })
  fireEvent.click(within(input.parentElement).getByText('Add'))
}

function drawRectangle(from, to, label) {
  selectTool('Rectangle')
  drag(from, to)
  confirmLabel(label)
}

function badgeButtons() {
  return [...canvasRoot().querySelectorAll('button')].filter((b) => b.className.includes('rounded-full'))
}

function shapeElements() {
  return [
    ...canvasRoot().querySelectorAll('svg.overflow-visible rect, svg.overflow-visible ellipse, svg.overflow-visible polyline'),
  ]
}

describe('AnnotationCanvas (T06 — F-2.3.1/2/3)', () => {
  it('F-2.3.1 draws a rectangle and prompts for a label', () => {
    render(<Harness />)

    selectTool('Rectangle')
    drag({ x: 20, y: 10 }, { x: 70, y: 40 })

    // The label popup is the "prompt for a label" requirement.
    expect(screen.getByPlaceholderText('Enter label…')).toBeInTheDocument()
    confirmLabel('nodule')

    const boxes = readBoxes()
    expect(boxes).toHaveLength(1)
    expect(boxes[0].label).toBe('nodule')
    expect(boxes[0].shape === undefined || boxes[0].shape === 'rectangle').toBe(true)
  })

  it('F-2.3.1 draws a circle with a label', () => {
    render(<Harness />)
    selectTool('Circle')
    drag({ x: 20, y: 10 }, { x: 70, y: 50 })
    confirmLabel('cavity')

    const [box] = readBoxes()
    expect(box.shape).toBe('circle')
    expect(box.label).toBe('cavity')
  })

  it('F-2.3.1 draws a freehand line with a label and keeps its points', () => {
    render(<Harness />)
    selectTool('Freehand')
    drag({ x: 20, y: 20 }, { x: 90, y: 60 }, { steps: 6 })
    confirmLabel('opacity')

    const [box] = readBoxes()
    expect(box.shape).toBe('freehand')
    expect(Array.isArray(box.points)).toBe(true)
    expect(box.points.length).toBeGreaterThanOrEqual(2)
    expect(box.label).toBe('opacity')
  })

  it('F-2.3.2 stores multiple ROIs with normalized coordinates', () => {
    render(<Harness />)
    drawRectangle({ x: 0, y: 0 }, { x: 100, y: 50 }, 'roi-1')
    drawRectangle({ x: 50, y: 25 }, { x: 150, y: 75 }, 'roi-2')

    const boxes = readBoxes()
    expect(boxes).toHaveLength(2)
    for (const box of boxes) {
      expect(box.x).toBeGreaterThanOrEqual(0)
      expect(box.x).toBeLessThanOrEqual(1)
      expect(box.width).toBeGreaterThan(0)
      expect(box.width).toBeLessThanOrEqual(1)
    }
    // (100-0)/200 = 0.5 wide, (50-0)/100 = 0.5 tall for the first box.
    expect(boxes[0].width).toBeCloseTo(0.5, 5)
    expect(boxes[0].height).toBeCloseTo(0.5, 5)
  })

  it('F-2.3.3 clicking a shape selects it, and toolbar delete removes it', () => {
    render(<Harness />)
    drawRectangle({ x: 20, y: 10 }, { x: 70, y: 40 }, 'keep-me')
    drawRectangle({ x: 100, y: 10 }, { x: 150, y: 40 }, 'delete-me')
    expect(readBoxes()).toHaveLength(2)

    // Shapes are hit-testable: clicking one selects it for the toolbar delete.
    fireEvent.click(shapeElements()[0])
    const deleteBtn = screen.getByTitle('Delete selected')
    expect(deleteBtn).toBeEnabled()
    fireEvent.click(deleteBtn)
    expect(readBoxes()).toHaveLength(1)

    // Undo restores the removed shape.
    fireEvent.click(screen.getByTitle('Undo'))
    expect(readBoxes()).toHaveLength(2)
  })

  it('F-2.3.3 the per-shape X control deletes the shape and undo restores it', () => {
    render(<Harness />)
    drawRectangle({ x: 20, y: 10 }, { x: 70, y: 40 }, 'roi-1')
    drawRectangle({ x: 100, y: 10 }, { x: 150, y: 40 }, 'roi-2')
    expect(readBoxes()).toHaveLength(2)

    // The red X on the box must actually remove it (not just select it).
    fireEvent.click(badgeButtons()[0])
    expect(readBoxes()).toHaveLength(1)
    expect(readBoxes()[0].label).toBe('roi-2')

    fireEvent.click(screen.getByTitle('Undo'))
    expect(readBoxes()).toHaveLength(2)
  })

  it('F-2.3.3 undo stack is capped at 20 steps and never crashes', () => {
    render(<Harness />)

    for (let i = 0; i < 25; i += 1) {
      const x = 5 + i
      drawRectangle({ x, y: 5 }, { x: x + 20, y: 25 }, `roi-${i}`)
    }
    expect(readBoxes()).toHaveLength(25)

    const undo = screen.getByTitle('Undo')
    for (let i = 0; i < 25; i += 1) {
      if (undo.disabled) break
      fireEvent.click(undo)
    }

    // 20 undos were available, so 5 shapes remain (25 - 20) and the control
    // is disabled rather than throwing.
    expect(readBoxes()).toHaveLength(5)
    expect(screen.getByTitle('Undo')).toBeDisabled()
  })

  it('drawing a shape ignores non-primary mouse buttons (pan must not annotate)', () => {
    render(<Harness />)
    selectTool('Rectangle')
    // Right-button drag is the viewer's pan gesture; it must not open the
    // label prompt or create a region of interest.
    drag({ x: 20, y: 10 }, { x: 70, y: 40 }, { button: 2 })
    expect(screen.queryByPlaceholderText('Enter label…')).not.toBeInTheDocument()
    expect(readBoxes()).toHaveLength(0)
  })
})
