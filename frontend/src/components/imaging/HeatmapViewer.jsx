import { useState, useRef, useEffect, useCallback } from 'react'
import { ZoomIn, ZoomOut, RotateCcw, Layers } from 'lucide-react'
import AIRiskBadge from '../ui/AIRiskBadge'

const MIN_SCALE = 1
const MAX_SCALE = 8
const SCROLL_SENSITIVITY = 0.001
const ZOOM_STEP = 0.5

// ─── Toolbar button (same pattern as XrayViewer) ─────────────────────────────

function ToolbarButton({ onClick, title, children }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="w-8 h-8 flex items-center justify-center rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-colors"
    >
      {children}
    </button>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function HeatmapViewer({
  rawImageUrl,
  heatmapUrl,
  aiResult,
  overlay,          // optional — e.g. StaticAnnotationOverlay
  autoShowHeatmap = false,
  onTransformChange,
}) {
  const [rawReady,     setRawReady]     = useState(false)
  const [heatmapReady, setHeatmapReady] = useState(false)
  const [showHeatmap,  setShowHeatmap]  = useState(false)

  const [scale,     setScale]     = useState(1)
  const [translate, setTranslate] = useState({ x: 0, y: 0 })

  const containerRef     = useRef(null)
  const rawImgRef        = useRef(null)
  const isPanning        = useRef(false)
  const lastPointer      = useRef({ x: 0, y: 0 })
  const lastPinchDist    = useRef(null)
  const currentScale     = useRef(1)
  const currentTranslate = useRef({ x: 0, y: 0 })

  useEffect(() => { currentScale.current = scale },     [scale])
  useEffect(() => { currentTranslate.current = translate }, [translate])
  useEffect(() => { onTransformChange?.({ scale, translate }) }, [scale, translate])

  // Reset when the raw image changes (new record)
  useEffect(() => {
    setRawReady(false)
    setHeatmapReady(false)
    setShowHeatmap(false)
    resetTransform()
  }, [rawImageUrl])

  // Reset only heatmap state when the heatmap URL changes
  useEffect(() => {
    setHeatmapReady(false)
    setShowHeatmap(false)
  }, [heatmapUrl])

  // If annotations exist, default the heatmap to on (without forcing it later)
  useEffect(() => {
    if (autoShowHeatmap && heatmapUrl) setShowHeatmap(true)
  }, [autoShowHeatmap, heatmapUrl])

  // checks if image is already cached in browser which causes onLoad() to not trigger
  useEffect(() => {
    const img = rawImgRef.current
    if (!img) return
    if (img.complete && img.naturalWidth > 0) setRawReady(true)
  }, [rawImageUrl])

  // ── Transform helpers ───────────────────────────────────────────────────────

  const clampScale   = (n) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, n))
  const resetTransform = () => { setScale(1); setTranslate({ x: 0, y: 0 }) }

  const applyScale = useCallback((next) => {
    const clamped = clampScale(next)
    setScale(clamped)
    if (clamped === MIN_SCALE) setTranslate({ x: 0, y: 0 })
  }, [])

  // ── Scroll zoom ─────────────────────────────────────────────────────────────

  const handleWheel = useCallback((e) => {
    e.preventDefault()
    applyScale(currentScale.current + (-e.deltaY * SCROLL_SENSITIVITY) * currentScale.current)
  }, [applyScale])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    el.addEventListener('wheel', handleWheel, { passive: false })
    return () => el.removeEventListener('wheel', handleWheel)
  }, [handleWheel])

  // ── Right-click pan ─────────────────────────────────────────────────────────

  const handleMouseDown = useCallback((e) => {
    if (e.button !== 2 || currentScale.current <= 1) return
    isPanning.current = true
    lastPointer.current = { x: e.clientX, y: e.clientY }
  }, [])

  const handleMouseMove = useCallback((e) => {
    if (!isPanning.current) return
    const dx = e.clientX - lastPointer.current.x
    const dy = e.clientY - lastPointer.current.y
    lastPointer.current = { x: e.clientX, y: e.clientY }
    setTranslate((p) => ({ x: p.x + dx, y: p.y + dy }))
  }, [])

  const handleMouseUp   = useCallback(() => { isPanning.current = false }, [])
  const handleContextMenu = useCallback((e) => e.preventDefault(), [])

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
      if (lastPinchDist.current) applyScale(currentScale.current * (dist / lastPinchDist.current))
      lastPinchDist.current = dist
    } else if (e.touches.length === 1 && isPanning.current) {
      const dx = e.touches[0].clientX - lastPointer.current.x
      const dy = e.touches[0].clientY - lastPointer.current.y
      lastPointer.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }
      setTranslate((p) => ({ x: p.x + dx, y: p.y + dy }))
    }
  }, [applyScale])

  const handleTouchEnd = useCallback(() => {
    lastPinchDist.current = null
    isPanning.current = false
  }, [])

  // ── Shared image transform ──────────────────────────────────────────────────

  const imgStyle = {
    transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
    transformOrigin: 'center center',
    transition: isPanning.current ? 'none' : 'transform 0.12s ease, opacity 0.3s ease',
  }

  const heatmapAvailable = !!heatmapUrl

  return (
    <div className="flex flex-col gap-3 w-full">

      {/* ── Toolbar ── */}
      <div className="flex items-center justify-between">

        {/* Zoom controls */}
        <div className="flex items-center gap-1 px-3 py-2 bg-[#0e0e0e] rounded-xl border border-white/5 w-fit">
          <ToolbarButton title="Zoom in"   onClick={() => applyScale(currentScale.current + ZOOM_STEP)}>
            <ZoomIn size={15} />
          </ToolbarButton>
          <span className="text-white/40 text-xs font-mono w-10 text-center select-none">
            {Math.round(scale * 100)}%
          </span>
          <ToolbarButton title="Zoom out"  onClick={() => applyScale(currentScale.current - ZOOM_STEP)}>
            <ZoomOut size={15} />
          </ToolbarButton>
          <div className="w-px h-4 bg-white/10 mx-1" />
          <ToolbarButton title="Reset view" onClick={resetTransform}>
            <RotateCcw size={15} />
          </ToolbarButton>
        </div>

        {/* Heatmap toggle — only shown when a heatmap is available */}
        {heatmapAvailable && (
          <button
            onClick={() => setShowHeatmap((v) => !v)}
            className={`
              flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold
              border transition-all duration-150
              ${showHeatmap
                ? 'bg-orange-500 border-orange-500 text-white'
                : 'bg-[#0e0e0e] border-white/10 text-white/50 hover:text-white hover:border-white/20'}
            `}
          >
            <Layers size={13} />
            {showHeatmap ? 'Heatmap On' : 'Heatmap Off'}
          </button>
        )}
      </div>

      {/* ── Viewer canvas ── */}
      <div
        ref={containerRef}
        className="relative w-full overflow-hidden rounded-2xl bg-black select-none"
        style={{ aspectRatio: '4 / 3' }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onContextMenu={handleContextMenu}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Loading skeleton */}
        {!rawReady && (
          <div className="absolute inset-0 flex items-center justify-center animate-pulse">
            <div className="w-32 h-40 rounded-t-full border-2 border-white/10 flex items-end justify-center pb-2">
              <div className="w-20 h-28 rounded-t-full border-2 border-white/10 flex items-end justify-center pb-2">
                <div className="w-10 h-16 rounded-t-full border-2 border-white/10" />
              </div>
            </div>
          </div>
        )}

        {/* Raw X-ray */}
        {rawImageUrl && (
          <img
            key={rawImageUrl}
            src={rawImageUrl}
            alt="X-Ray"
            onLoad={() => setRawReady(true)}
            ref={rawImgRef}
            draggable={false}
            className="absolute inset-0 w-full h-full object-contain"
            style={{ ...imgStyle, opacity: rawReady ? 1 : 0 }}
          />
        )}

        {/* Grad-CAM heatmap overlay */}
        {heatmapUrl && (
          <img
            key={heatmapUrl}
            src={heatmapUrl}
            alt="Heatmap"
            onLoad={() => setHeatmapReady(true)}
            draggable={false}
            className="absolute inset-0 w-full h-full object-contain"
            style={{
              ...imgStyle,
              opacity:       showHeatmap && heatmapReady ? 1 : 0,
              mixBlendMode:  'multiply',
              transition:    'opacity 0.25s ease, transform 0.12s ease',
            }}
          />
        )}

        {/* Optional overlay slot (e.g. StaticAnnotationOverlay) */}
        {overlay}

        {/* Zoom level pill */}
        {scale > 1 && (
          <div className="absolute bottom-3 right-3 bg-black/60 text-white/70 text-xs font-mono px-2.5 py-1 rounded-full pointer-events-none backdrop-blur-sm">
            {Math.round(scale * 100)}%
          </div>
        )}
      </div>

      {/* ── AI result badge ── */}
      {aiResult && (
        <div className="flex items-center gap-3">
          <AIRiskBadge label={aiResult.risk_label} score={aiResult.risk_score} />
          <span className="text-xs text-[var(--text-muted)]">
            Model: {aiResult.model_version}
          </span>
        </div>
      )}
    </div>
  )
}