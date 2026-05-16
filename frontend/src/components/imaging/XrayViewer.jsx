import { useState, useRef, useEffect, useCallback } from 'react'
import { ZoomIn, ZoomOut, RotateCcw, AlertCircle } from 'lucide-react'

const MIN_SCALE = 1
const MAX_SCALE = 8
const SCROLL_SENSITIVITY = 0.001
const BUTTON_ZOOM_STEP = 0.5

// ─── Skeleton ────────────────────────────────────────────────────────────────

function XrayViewerSkeleton() {
  return (
    <div className="w-full h-full absolute inset-0 bg-black flex items-center justify-center">
      <div className="flex flex-col items-center gap-3 animate-pulse">
        {/* Fake X-ray ribcage outline using concentric divs */}
        <div className="w-32 h-40 rounded-t-full border-2 border-white/10 flex items-end justify-center pb-2">
          <div className="w-20 h-28 rounded-t-full border-2 border-white/10 flex items-end justify-center pb-2">
            <div className="w-10 h-16 rounded-t-full border-2 border-white/10" />
          </div>
        </div>
        <span className="text-white/20 text-xs tracking-widest uppercase">Loading image…</span>
      </div>
    </div>
  )
}

// ─── Error state ─────────────────────────────────────────────────────────────

function XrayViewerError({ message }) {
  return (
    <div className="w-full h-full absolute inset-0 bg-black flex flex-col items-center justify-center gap-3">
      <AlertCircle size={32} className="text-red-400" />
      <p className="text-white/60 text-sm">{message}</p>
    </div>
  )
}

// ─── Toolbar button ───────────────────────────────────────────────────────────

function ToolbarButton({ onClick, title, children, active = false }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`
        w-8 h-8 flex items-center justify-center rounded-lg transition-colors
        ${active
          ? 'bg-white/20 text-white'
          : 'text-white/50 hover:text-white hover:bg-white/10'}
      `}
    >
      {children}
    </button>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function XrayViewer({ transactionId }) {
  const [xray, setXray]           = useState(null)
  const [fetchLoading, setFetchLoading] = useState(true)
  const [fetchError, setFetchError]     = useState(null)
  const [imageReady, setImageReady]     = useState(false)

  // Transform state
  const [scale, setScale]         = useState(1)
  const [translate, setTranslate] = useState({ x: 0, y: 0 })

  // Panning refs — using refs instead of state avoids re-renders mid-drag
  const containerRef      = useRef(null)
  const isPanning         = useRef(false)
  const lastPointer       = useRef({ x: 0, y: 0 })
  const lastPinchDist     = useRef(null)
  const currentScale      = useRef(1)   // mirror of scale for use inside event handlers
  const currentTranslate  = useRef({ x: 0, y: 0 })

  // Keep refs in sync with state
  useEffect(() => { currentScale.current = scale }, [scale])
  useEffect(() => { currentTranslate.current = translate }, [translate])

  // ── Fetch ───────────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!transactionId) return
    setFetchLoading(true)
    setFetchError(null)
    setImageReady(false)
    resetTransform()

    fetch(`/api/imaging/xray/${transactionId}/`, { credentials: 'include' })
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load record (${r.status})`)
        return r.json()
      })
      .then(setXray)
      .catch((err) => setFetchError(err.message))
      .finally(() => setFetchLoading(false))
  }, [transactionId])

  // ── Transform helpers ───────────────────────────────────────────────────────

  const resetTransform = () => {
    setScale(1)
    setTranslate({ x: 0, y: 0 })
  }

  const clampScale = (next) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, next))

  const applyScale = useCallback((next) => {
    const clamped = clampScale(next)
    setScale(clamped)
    // Reset pan when fully zoomed out
    if (clamped === MIN_SCALE) setTranslate({ x: 0, y: 0 })
  }, [])

  // ── Scroll zoom ─────────────────────────────────────────────────────────────

  const handleWheel = useCallback((e) => {
    e.preventDefault()
    // deltaY > 0 = scroll down = zoom out
    const delta = -e.deltaY * SCROLL_SENSITIVITY
    applyScale(currentScale.current + delta * currentScale.current)
  }, [applyScale])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    // passive: false required to call preventDefault inside wheel
    el.addEventListener('wheel', handleWheel, { passive: false })
    return () => el.removeEventListener('wheel', handleWheel)
  }, [handleWheel])

  // ── Mouse pan ───────────────────────────────────────────────────────────────

  const handleMouseDown = useCallback((e) => {
    if (currentScale.current <= 1) return
    isPanning.current = true
    lastPointer.current = { x: e.clientX, y: e.clientY }
  }, [])

  const handleMouseMove = useCallback((e) => {
    if (!isPanning.current) return
    const dx = e.clientX - lastPointer.current.x
    const dy = e.clientY - lastPointer.current.y
    lastPointer.current = { x: e.clientX, y: e.clientY }
    setTranslate((prev) => ({ x: prev.x + dx, y: prev.y + dy }))
  }, [])

  const handleMouseUp = useCallback(() => {
    isPanning.current = false
  }, [])

  // ── Pinch zoom ──────────────────────────────────────────────────────────────

  const getPinchDist = (touches) => {
    const dx = touches[0].clientX - touches[1].clientX
    const dy = touches[0].clientY - touches[1].clientY
    return Math.sqrt(dx * dx + dy * dy)
  }

  const handleTouchStart = useCallback((e) => {
    if (e.touches.length === 2) {
      lastPinchDist.current = getPinchDist(e.touches)
    } else if (e.touches.length === 1 && currentScale.current > 1) {
      isPanning.current = true
      lastPointer.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }
    }
  }, [])

  const handleTouchMove = useCallback((e) => {
    e.preventDefault()
    if (e.touches.length === 2) {
      const dist = getPinchDist(e.touches)
      if (lastPinchDist.current !== null) {
        const ratio = dist / lastPinchDist.current
        applyScale(currentScale.current * ratio)
      }
      lastPinchDist.current = dist
    } else if (e.touches.length === 1 && isPanning.current) {
      const dx = e.touches[0].clientX - lastPointer.current.x
      const dy = e.touches[0].clientY - lastPointer.current.y
      lastPointer.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }
      setTranslate((prev) => ({ x: prev.x + dx, y: prev.y + dy }))
    }
  }, [applyScale])

  const handleTouchEnd = useCallback(() => {
    lastPinchDist.current = null
    isPanning.current = false
  }, [])

  // ── Render ──────────────────────────────────────────────────────────────────

  const isLoading = fetchLoading || (!imageReady && !fetchError)
  const canPan = scale > 1

  return (
    <div className="flex flex-col gap-2 w-full">

      {/* Toolbar */}
      <div className="flex items-center gap-1 px-3 py-2 bg-[#0e0e0e] rounded-xl border border-white/5 w-fit self-end">
        <ToolbarButton
          title="Zoom in"
          onClick={() => applyScale(currentScale.current + BUTTON_ZOOM_STEP)}
        >
          <ZoomIn size={15} />
        </ToolbarButton>

        <span className="text-white/40 text-xs font-mono w-10 text-center select-none">
          {Math.round(scale * 100)}%
        </span>

        <ToolbarButton
          title="Zoom out"
          onClick={() => applyScale(currentScale.current - BUTTON_ZOOM_STEP)}
        >
          <ZoomOut size={15} />
        </ToolbarButton>

        <div className="w-px h-4 bg-white/10 mx-1" />

        <ToolbarButton title="Reset view" onClick={resetTransform}>
          <RotateCcw size={15} />
        </ToolbarButton>
      </div>

      {/* Viewer canvas */}
      <div
        ref={containerRef}
        className="relative w-full overflow-hidden rounded-2xl bg-black select-none"
        style={{
          aspectRatio: '4 / 3',
          cursor: canPan ? (isPanning.current ? 'grabbing' : 'grab') : 'default',
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Skeleton — shown until image fires onLoad */}
        {isLoading && !fetchError && <XrayViewerSkeleton />}

        {/* Error */}
        {fetchError && <XrayViewerError message={fetchError} />}

        {/* Image */}
        {xray?.display_image && (
          <img
            key={xray.display_image}   // remount if URL changes
            src={xray.display_image}
            alt={`X-Ray ${transactionId}`}
            onLoad={() => setImageReady(true)}
            draggable={false}
            className="absolute inset-0 w-full h-full object-contain transition-opacity duration-300"
            style={{
              opacity: imageReady ? 1 : 0,
              transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
              transformOrigin: 'center center',
              // Only smooth for button-driven zoom, not scroll/pinch (avoids lag)
              transition: isPanning.current
                ? 'none'
                : 'transform 0.12s ease, opacity 0.3s ease',
            }}
          />
        )}

        {/* Zoom level pill — visible when zoomed */}
        {scale > 1 && (
          <div className="absolute bottom-3 right-3 bg-black/60 text-white/70 text-xs font-mono px-2.5 py-1 rounded-full pointer-events-none backdrop-blur-sm">
            {Math.round(scale * 100)}%
          </div>
        )}
      </div>
    </div>
  )
}