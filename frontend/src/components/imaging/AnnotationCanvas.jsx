import { useState, useRef, useCallback, useEffect } from 'react'
import { X, Square, Circle, PencilLine, Undo2, Trash2 } from 'lucide-react'

const TOOL_OPTIONS = [
  { value: 'rectangle', label: 'Rectangle', icon: Square },
  { value: 'circle', label: 'Circle', icon: Circle },
  { value: 'freehand', label: 'Freehand', icon: PencilLine },
]

// ─── Label input popup ────────────────────────────────────────────────────────

function LabelPopup({ position, value, onChange, onConfirm, onCancel, inputRef }) {
  return (
    <div
      style={{ position: 'absolute', left: position.x, top: position.y + 8, zIndex: 20 }}
      className="bg-white border border-[var(--border)] rounded-xl shadow-lg p-3 flex items-center gap-2 min-w-52"
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
    >
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onConfirm()
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
  scale = 1,
  translate = { x: 0, y: 0 },
  onBoxesChange,
  disabled = false,
}) {
  const selfRef = useRef(null)
  const labelRef = useRef(null)

  const [boxes, setBoxes] = useState([])
  const [drawing, setDrawing] = useState(null)
  const [pendingBox, setPending] = useState(null)
  const [draft, setDraft] = useState('')
  const [tool, setTool] = useState('rectangle')
  const [selectedId, setSelectedId] = useState(null)
  const [undoStack, setUndoStack] = useState([])

  const pushHistory = useCallback((snapshot) => {
    setUndoStack((prev) => [...prev.slice(-19), snapshot])
  }, [])

  const emitBoxes = useCallback((nextBoxes) => {
    const normalized = nextBoxes.map(({ id, ...box }) => {
      const normalizedBox = {
        x: box.x / (selfRef.current?.offsetWidth || 1),
        y: box.y / (selfRef.current?.offsetHeight || 1),
        width: box.width / (selfRef.current?.offsetWidth || 1),
        height: box.height / (selfRef.current?.offsetHeight || 1),
        label: box.label,
      }

      if (box.shape === 'circle') normalizedBox.shape = 'circle'
      if (box.shape === 'freehand' && box.points) {
        normalizedBox.shape = 'freehand'
        normalizedBox.points = box.points.map((pt) => ({
          x: pt.x / (selfRef.current?.offsetWidth || 1),
          y: pt.y / (selfRef.current?.offsetHeight || 1),
        }))
      }

      return normalizedBox
    })

    onBoxesChange?.(normalized)
  }, [onBoxesChange])

  const commitBoxes = useCallback((updater) => {
    setBoxes((prev) => {
      const snapshot = prev.map((box) => ({ ...box, points: box.points ? box.points.map((pt) => ({ ...pt })) : undefined }))
      const next = typeof updater === 'function' ? updater(prev) : updater
      pushHistory(snapshot)
      emitBoxes(next)
      return next
    })
  }, [emitBoxes, pushHistory])

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

  const handleMouseDown = useCallback((e) => {
    if (disabled || pendingBox) return
    e.preventDefault()

    const pt = toElementSpace(e.clientX, e.clientY)

    if (tool === 'freehand') {
      setDrawing({ type: 'freehand', points: [pt] })
      return
    }

    setDrawing({
      type: tool,
      startX: pt.x,
      startY: pt.y,
      currentX: pt.x,
      currentY: pt.y,
    })
  }, [disabled, pendingBox, tool, toElementSpace])

  const handleMouseMove = useCallback((e) => {
    if (!drawing) return

    const pt = toElementSpace(e.clientX, e.clientY)

    setDrawing((prev) => {
      if (!prev) return prev
      if (prev.type === 'freehand') {
        return { ...prev, points: [...prev.points, pt] }
      }
      return { ...prev, currentX: pt.x, currentY: pt.y }
    })
  }, [drawing, toElementSpace])

  const handleMouseUp = useCallback(() => {
    if (!drawing) return

    if (drawing.type === 'freehand') {
      const points = drawing.points
      if (points.length < 2) {
        setDrawing(null)
        return
      }

      const minX = Math.min(...points.map((pt) => pt.x))
      const maxX = Math.max(...points.map((pt) => pt.x))
      const minY = Math.min(...points.map((pt) => pt.y))
      const maxY = Math.max(...points.map((pt) => pt.y))
      const width = Math.max(maxX - minX, 10)
      const height = Math.max(maxY - minY, 10)

      const box = {
        id: crypto.randomUUID(),
        x: minX,
        y: minY,
        width,
        height,
        shape: 'freehand',
        points,
        label: '',
      }

      setDrawing(null)
      setPending(box)
      setDraft('')
      setTimeout(() => labelRef.current?.focus(), 40)
      return
    }

    const { startX, startY, currentX, currentY } = drawing
    const w = currentX - startX
    const h = currentY - startY

    if (Math.abs(w) < 8 / scale || Math.abs(h) < 8 / scale) {
      setDrawing(null)
      return
    }

    const box = {
      id: crypto.randomUUID(),
      x: w < 0 ? startX + w : startX,
      y: h < 0 ? startY + h : startY,
      width: Math.abs(w),
      height: Math.abs(h),
      shape: drawing.type === 'circle' ? 'circle' : 'rectangle',
      label: '',
    }

    setDrawing(null)
    setPending(box)
    setDraft('')
    setTimeout(() => labelRef.current?.focus(), 40)
  }, [drawing, scale])

  const confirmLabel = useCallback(() => {
    if (!pendingBox) return

    const confirmed = { ...pendingBox, label: draft.trim() }
    commitBoxes((prev) => [...prev, confirmed])
    setPending(null)
    setDraft('')
    setSelectedId(confirmed.id)
  }, [commitBoxes, draft, pendingBox])

  const deleteBox = useCallback((id) => {
    commitBoxes((prev) => prev.filter((box) => box.id !== id))
    if (selectedId === id) setSelectedId(null)
  }, [commitBoxes, selectedId])

  const deleteSelected = useCallback(() => {
    if (!selectedId) return
    deleteBox(selectedId)
  }, [deleteBox, selectedId])

  const undoLastAction = useCallback(() => {
    if (!undoStack.length) return
    const previous = undoStack[undoStack.length - 1]
    setUndoStack((prev) => prev.slice(0, -1))
    setBoxes(previous)
    emitBoxes(previous)
    setSelectedId(null)
  }, [emitBoxes, undoStack])

  const cancelPending = useCallback(() => {
    setPending(null)
    setDraft('')
  }, [])

  useEffect(() => {
    const onKeyDown = (event) => {
      if (disabled || pendingBox) return
      if ((event.key === 'Delete' || event.key === 'Backspace') && selectedId) {
        event.preventDefault()
        deleteSelected()
      }

      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
        event.preventDefault()
        undoLastAction()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [deleteSelected, disabled, pendingBox, selectedId, undoLastAction])

  const sw = 2 / scale
  const dash = `${6 / scale} ${3 / scale}`

  const transformStyle = {
    transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
    transformOrigin: 'center center',
    pointerEvents: 'none',
  }

  const labelPos = pendingBox
    ? toScreenSpace(pendingBox.x, pendingBox.y + pendingBox.height)
    : null

  const renderShape = (box) => {
    const commonProps = {
      stroke: selectedId === box.id ? '#ef4444' : '#5b65dc',
      strokeWidth: sw,
      fill: selectedId === box.id ? 'rgba(239,68,68,0.10)' : 'rgba(91,101,220,0.12)',
      vectorEffect: 'non-scaling-stroke',
      onClick: () => setSelectedId(box.id),
      className: 'cursor-pointer',
    }

    if (box.shape === 'circle') {
      const cx = box.x + box.width / 2
      const cy = box.y + box.height / 2
      const rx = box.width / 2
      const ry = box.height / 2
      return <ellipse key={box.id} cx={cx} cy={cy} rx={rx} ry={ry} {...commonProps} />
    }

    if (box.shape === 'freehand' && box.points) {
      const points = box.points.map((pt) => `${pt.x},${pt.y}`).join(' ')
      return <polyline key={box.id} points={points} {...commonProps} strokeLinejoin="round" strokeLinecap="round" fill="none" />
    }

    return (
      <rect
        key={box.id}
        x={box.x}
        y={box.y}
        width={box.width}
        height={box.height}
        fill={selectedId === box.id ? 'rgba(239,68,68,0.10)' : 'rgba(91,101,220,0.12)'}
        stroke={selectedId === box.id ? '#ef4444' : '#5b65dc'}
        strokeWidth={sw}
        strokeDasharray={dash}
        vectorEffect="non-scaling-stroke"
        onClick={() => setSelectedId(box.id)}
        className="cursor-pointer"
      />
    )
  }

  const renderPendingShape = (box) => {
    if (box.shape === 'circle') {
      const cx = box.x + box.width / 2
      const cy = box.y + box.height / 2
      const rx = box.width / 2
      const ry = box.height / 2
      return <ellipse key={box.id} cx={cx} cy={cy} rx={rx} ry={ry} fill="rgba(91,101,220,0.15)" stroke="#5b65dc" strokeWidth={sw} />
    }

    if (box.shape === 'freehand' && box.points) {
      const points = box.points.map((pt) => `${pt.x},${pt.y}`).join(' ')
      return <polyline key={box.id} points={points} fill="none" stroke="#5b65dc" strokeWidth={sw} strokeLinejoin="round" strokeLinecap="round" />
    }

    return (
      <rect
        key={box.id}
        x={box.x}
        y={box.y}
        width={box.width}
        height={box.height}
        fill="rgba(91,101,220,0.15)"
        stroke="#5b65dc"
        strokeWidth={sw}
      />
    )
  }

  const renderDrawingPreview = () => {
    if (!drawing) return null

    if (drawing.type === 'circle') {
      const x = Math.min(drawing.startX, drawing.currentX)
      const y = Math.min(drawing.startY, drawing.currentY)
      const width = Math.abs(drawing.currentX - drawing.startX)
      const height = Math.abs(drawing.currentY - drawing.startY)
      const cx = x + width / 2
      const cy = y + height / 2
      return <ellipse cx={cx} cy={cy} rx={width / 2} ry={height / 2} fill="rgba(91,101,220,0.08)" stroke="#5b65dc" strokeWidth={sw} strokeDasharray={dash} />
    }

    if (drawing.type === 'freehand') {
      const points = drawing.points.map((pt) => `${pt.x},${pt.y}`).join(' ')
      return <polyline points={points} fill="none" stroke="#5b65dc" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={dash} />
    }

    return (
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
    )
  }

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
      <div className="absolute left-3 top-3 z-20 flex gap-2 rounded-xl border border-[var(--border)] bg-white/90 p-1 shadow-sm backdrop-blur-sm">
        {TOOL_OPTIONS.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            type="button"
            title={label}
            onClick={() => setTool(value)}
            className={`flex h-8 w-8 items-center justify-center rounded-lg border transition-colors ${
              tool === value ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]' : 'border-transparent text-[var(--text-muted)] hover:bg-[var(--surface-soft)]'
            }`}
          >
            <Icon size={14} />
          </button>
        ))}

        <button
          type="button"
          title="Undo"
          onClick={undoLastAction}
          disabled={!undoStack.length}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-transparent text-[var(--text-muted)] hover:bg-[var(--surface-soft)] disabled:cursor-not-allowed disabled:opacity-30"
        >
          <Undo2 size={14} />
        </button>

        <button
          type="button"
          title="Delete selected"
          onClick={deleteSelected}
          disabled={!selectedId}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-transparent text-[var(--text-muted)] hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <Trash2 size={14} />
        </button>
      </div>

      <svg className="absolute inset-0 w-full h-full overflow-visible" style={transformStyle}>
        {boxes.map((box) => renderShape(box))}

        {pendingBox && renderPendingShape(pendingBox)}
        {drawing && renderDrawingPreview()}
      </svg>

      {boxes.map((box) => {
        const pos = toScreenSpace(box.x + (box.width || 0) / 2, box.y)
        return (
          <button
            key={`del-${box.id}`}
            type="button"
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation()
              setSelectedId(box.id)
            }}
            style={{ position: 'absolute', left: pos.x - 8, top: pos.y - 8, zIndex: 10 }}
            className={`w-5 h-5 rounded-full flex items-center justify-center shadow-md transition-colors ${
              selectedId === box.id ? 'bg-red-600 text-white' : 'bg-red-500 text-white hover:bg-red-600'
            }`}
          >
            <X size={9} />
          </button>
        )
      })}

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