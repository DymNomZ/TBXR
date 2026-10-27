import { useRef, useState, useEffect } from 'react'

// Each annotation from the backend has { bounding_boxes: [{x,y,width,height,label}], notes, radiologist }
// Boxes are in element space — same coordinate system AnnotationCanvas used when drawing
export default function StaticAnnotationOverlay({ annotations = [], scale = 1, translate = { x: 0, y: 0 } }) {
  const selfRef = useRef(null)
  const [dims, setDims] = useState({ w: 1, h: 1 })

  const isNormalized = (value) => Number.isFinite(value) && value >= 0 && value <= 1

  // Track container size — updates whenever modal/layout resizes
  useEffect(() => {
    const el = selfRef.current
    if (!el) return

    const measure = () => {
      const { width, height } = el.getBoundingClientRect()
      if (width > 0 && height > 0) setDims({ w: width, h: height })
    }

    measure() // read immediately instead of waiting
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Re-measure when annotations first populate (race condition guard)
  useEffect(() => {
    if (!annotations.length) return
    const el = selfRef.current
    if (!el) return
    const { width, height } = el.getBoundingClientRect()
    if (width > 0 && height > 0) setDims({ w: width, h: height })
  }, [annotations.length])

  if (!annotations.length) return <div ref={selfRef} className="absolute inset-0 pointer-events-none" />

  // Convert both normalized and legacy pixel coordinates to canvas pixels.
  const px = (box) => {
    const useNormalizedRect = (
      isNormalized(box.x) &&
      isNormalized(box.y) &&
      isNormalized(box.width) &&
      isNormalized(box.height)
    )

    return {
      x: useNormalizedRect ? box.x * dims.w : box.x,
      y: useNormalizedRect ? box.y * dims.h : box.y,
      width: useNormalizedRect ? box.width * dims.w : box.width,
      height: useNormalizedRect ? box.height * dims.h : box.height,
    }
  }

  const pxPoint = (pt) => {
    if (!pt || !Number.isFinite(pt.x) || !Number.isFinite(pt.y)) return null
    const useNormalizedPoint = isNormalized(pt.x) && isNormalized(pt.y)
    return {
      x: useNormalizedPoint ? pt.x * dims.w : pt.x,
      y: useNormalizedPoint ? pt.y * dims.h : pt.y,
    }
  }

  const sw    = 2 / scale
  const dash  = `${6 / scale} ${3 / scale}`
  const fSize = 11 / scale

  const transformStyle = {
    transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
    transformOrigin: 'center center',
    pointerEvents: 'none',
  }

  const allBoxes = annotations.flatMap((ann, ai) =>
    (ann.bounding_boxes ?? []).map((box, bi) => ({ ...box, key: `${ai}-${bi}` }))
  )

  const renderShape = (box, p) => {
    const shape = box.shape === 'circle' || box.shape === 'freehand' ? box.shape : 'rectangle'

    if (shape === 'circle') {
      const cx = p.x + p.width / 2
      const cy = p.y + p.height / 2
      const rx = p.width / 2
      const ry = p.height / 2
      return (
        <ellipse
          cx={cx}
          cy={cy}
          rx={rx}
          ry={ry}
          fill="rgba(91,101,220,0.12)"
          stroke="#5b65dc"
          strokeWidth={sw}
        />
      )
    }

    if (shape === 'freehand' && Array.isArray(box.points)) {
      const points = box.points
        .map((pt) => pxPoint(pt))
        .filter(Boolean)
      if (points.length >= 2) {
        return (
          <polyline
            points={points.map((pt) => `${pt.x},${pt.y}`).join(' ')}
            fill="none"
            stroke="#5b65dc"
            strokeWidth={sw}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )
      }
    }

    return (
      <rect
        x={p.x}
        y={p.y}
        width={p.width}
        height={p.height}
        fill="rgba(91,101,220,0.12)"
        stroke="#5b65dc"
        strokeWidth={sw}
        strokeDasharray={dash}
      />
    )
  }

  return (
    <div ref={selfRef} className="absolute inset-0 pointer-events-none">
      <svg
        className="absolute inset-0 w-full h-full overflow-visible"
        style={transformStyle}
      >
        {allBoxes.map((box) => {
          const p = px(box)
          return (
            <g key={box.key}>
              {renderShape(box, p)}
              {box.label && (
                <text
                  x={p.x + 4 / scale}
                  y={p.y - 5 / scale}
                  fontSize={fSize}
                  fill="#5b65dc"
                  fontWeight="600"
                  fontFamily="ui-monospace, monospace"
                >
                  {box.label}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}