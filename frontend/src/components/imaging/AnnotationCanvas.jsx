import { useState, useRef, useCallback, useEffect } from 'react'
import { X } from 'lucide-react'

// ─── Label input popup ────────────────────────────────────────────────────────

function LabelPopup({ position, value, onChange, onConfirm, onCancel, inputRef }) {
  return (
    <div
      style={{ position: 'absolute', left: position.x, top: position.y + 8, zIndex: 20 }}
      className="bg-white border border-[var(--border)] rounded-xl shadow-lg p-3 flex items-center gap-2 min-w-52"
      // Prevent mouse events from bubbling into the canvas and cancelling the box
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
    >
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter')  onConfirm()
          if (e.key === 'Escape') onCancel()
        }}
        placeholder="Enter label…"
        className="flex-1 text-sm outline-none text-[var(--text)] placeholder:text-[var(--text-muted)]"
      />
      <button
        onClick={onConfirm}
        className="text-xs px-2.5 py-1 bg-[var(--accent)] text-white rounded-lg hover:opacity-90 transition-opacity shrink-0"
      >
        Add
      </button>
      <button
        onClick={onCancel}
        className="text-xs text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
      >
        ✕
      </button>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function AnnotationCanvas({
  scale     = 1,
  translate = { x: 0, y: 0 },
  onBoxesChange,
  disabled  = false,
}) {
  const selfRef     = useRef(null)   // the absolute inset-0 wrapper
  const labelRef    = useRef(null)

  const [boxes,      setBoxes]      = useState([])
  const [drawing,    setDrawing]    = useState(null)   // {startX,startY,currentX,currentY}
  const [pendingBox, setPending]    = useState(null)   // box awaiting label entry
  const [draft,      setDraft]      = useState('')

  // ── Coordinate helpers ──────────────────────────────────────────────────────

  // Screen coords (clientX/Y) → element space (pre-transform)
  const toElementSpace = useCallback((clientX, clientY) => {
    const el = selfRef.current
    if (!el) return { x: 0, y: 0 }
    const rect = el.getBoundingClientRect()
    const W = rect.width
    const H = rect.height
    const mx = clientX - rect.left
    const my = clientY - rect.top
    return {
      x: (mx - translate.x - W / 2) / scale + W / 2,
      y: (my - translate.y - H / 2) / scale + H / 2,
    }
  }, [scale, translate])

  // Element space → container-relative screen coords (for positioned HTML overlays)
  const toScreenSpace = useCallback((ex, ey) => {
    const el = selfRef.current
    if (!el) return { x: 0, y: 0 }
    const W = el.offsetWidth
    const H = el.offsetHeight
    return {
      x: (ex - W / 2) * scale + W / 2 + translate.x,
      y: (ey - H / 2) * scale + H / 2 + translate.y,
    }
  }, [scale, translate])

  // ── Drawing handlers ────────────────────────────────────────────────────────

  const handleMouseDown = useCallback((e) => {
    if (disabled || pendingBox) return
    e.preventDefault()
    const pt = toElementSpace(e.clientX, e.clientY)
    setDrawing({ startX: pt.x, startY: pt.y, currentX: pt.x, currentY: pt.y })
  }, [disabled, pendingBox, toElementSpace])

  const handleMouseMove = useCallback((e) => {
    if (!drawing) return
    const pt = toElementSpace(e.clientX, e.clientY)
    setDrawing((prev) => ({ ...prev, currentX: pt.x, currentY: pt.y }))
  }, [drawing, toElementSpace])

  const handleMouseUp = useCallback(() => {
    if (!drawing) return
    const { startX, startY, currentX, currentY } = drawing
    const w = currentX - startX
    const h = currentY - startY

    // Ignore accidental tiny clicks
    if (Math.abs(w) < 8 / scale || Math.abs(h) < 8 / scale) {
      setDrawing(null)
      return
    }

    const box = {
      id:     crypto.randomUUID(),
      x:      w < 0 ? startX + w : startX,
      y:      h < 0 ? startY + h : startY,
      width:  Math.abs(w),
      height: Math.abs(h),
      label:  '',
    }

    setDrawing(null)
    setPending(box)
    setDraft('')
    setTimeout(() => labelRef.current?.focus(), 40)
  }, [drawing, scale])

  // Helper — normalizes element-space box to 0-1 using current container dims
  const normalize = useCallback((box) => {
    const el = selfRef.current
    const W  = el?.offsetWidth  ?? 1
    const H  = el?.offsetHeight ?? 1
    return {
      x:      box.x      / W,
      y:      box.y      / H,
      width:  box.width  / W,
      height: box.height / H,
      label:  box.label,
    }
  }, [])

  const confirmLabel = useCallback(() => {
    if (!pendingBox) return
    const confirmed = { ...pendingBox, label: draft.trim() }
    setBoxes((prev) => {
      const next = [...prev, confirmed]
      onBoxesChange?.(next.map(({ id, ...box }) => normalize(box)))  // ← normalized, no id
      return next
    })
    setPending(null)
    setDraft('')
  }, [pendingBox, draft, onBoxesChange, normalize])

  const deleteBox = useCallback((id) => {
    setBoxes((prev) => {
      const next = prev.filter((b) => b.id !== id)
      onBoxesChange?.(next.map(({ id, ...box }) => normalize(box)))  // ← normalized, no id
      return next
    })
  }, [onBoxesChange, normalize])

  const cancelPending = useCallback(() => {
    setPending(null)
    setDraft('')
  }, [])

  // ── SVG visual helpers ──────────────────────────────────────────────────────

  // Stroke/font scale inversely so visuals stay constant size on screen
  const sw    = 2 / scale       // stroke width
  const dash  = `${6/scale} ${3/scale}`
  const fSize = 11 / scale

  const transformStyle = {
    transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
    transformOrigin: 'center center',
    pointerEvents: 'none',   // SVG is display-only; events go to the wrapper div
  }

  // Label popup position: below the pending box's bottom-left
  const labelPos = pendingBox
    ? toScreenSpace(pendingBox.x, pendingBox.y + pendingBox.height)
    : null

  return (
    <div
      ref={selfRef}
      className="absolute inset-0"
      style={{ cursor: disabled ? 'default' : pendingBox ? 'default' : 'crosshair' }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* ── SVG overlay — same transform as XrayViewer image ── */}
      <svg
        className="absolute inset-0 w-full h-full overflow-visible"
        style={transformStyle}
      >
        {/* Confirmed boxes */}
        {boxes.map((box) => (
          <g key={box.id}>
            <rect
              x={box.x} y={box.y}
              width={box.width} height={box.height}
              fill="rgba(91,101,220,0.12)"
              stroke="#5b65dc"
              strokeWidth={sw}
              strokeDasharray={dash}
            />
            {box.label && (
              <text
                x={box.x + 4 / scale}
                y={box.y - 5 / scale}
                fontSize={fSize}
                fill="#5b65dc"
                fontWeight="600"
                fontFamily="ui-monospace, monospace"
              >
                {box.label}
              </text>
            )}
          </g>
        ))}

        {/* Pending box (awaiting label) */}
        {pendingBox && (
          <rect
            x={pendingBox.x} y={pendingBox.y}
            width={pendingBox.width} height={pendingBox.height}
            fill="rgba(91,101,220,0.15)"
            stroke="#5b65dc"
            strokeWidth={sw}
          />
        )}

        {/* In-progress drawing */}
        {drawing && (
          <rect
            x={Math.min(drawing.startX, drawing.currentX)}
            y={Math.min(drawing.startY, drawing.currentY)}
            width={Math.abs(drawing.currentX - drawing.startX)}
            height={Math.abs(drawing.currentY - drawing.startY)}
            fill="rgba(91,101,220,0.08)"
            stroke="#5b65dc"
            strokeWidth={sw}
            strokeDasharray={dash}
          />
        )}
      </svg>

      {/* ── Delete buttons — screen space, no SVG transform ── */}
      {boxes.map((box) => {
        const pos = toScreenSpace(box.x, box.y)
        return (
          <button
            key={`del-${box.id}`}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => { e.stopPropagation(); deleteBox(box.id) }}
            style={{ position: 'absolute', left: pos.x - 8, top: pos.y - 8, zIndex: 10 }}
            className="w-5 h-5 rounded-full bg-red-500 hover:bg-red-600 text-white flex items-center justify-center shadow-md transition-colors"
          >
            <X size={9} />
          </button>
        )
      })}

      {/* ── Label input popup ── */}
      {pendingBox && labelPos && (
        <LabelPopup
          position={labelPos}
          value={draft}
          onChange={setDraft}
          onConfirm={confirmLabel}
          onCancel={cancelPending}
          inputRef={labelRef}
        />
      )}
    </div>
  )
}