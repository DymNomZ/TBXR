import { useRef, useState, useEffect } from 'react'

// Each annotation from the backend has { bounding_boxes: [{x,y,width,height,label}], notes, radiologist }
// Boxes are in element space — same coordinate system AnnotationCanvas used when drawing
export default function StaticAnnotationOverlay({ annotations = [], scale = 1, translate = { x: 0, y: 0 } }) {
  const selfRef = useRef(null)
  const [dims, setDims] = useState({ w: 1, h: 1 })

  // Track container size — updates whenever modal/layout resizes
  useEffect(() => {
    const el = selfRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      setDims({
        w: entry.contentRect.width,
        h: entry.contentRect.height,
      })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  if (!annotations.length) return <div ref={selfRef} className="absolute inset-0 pointer-events-none" />

  // Convert normalized (0-1) box back to pixel coords for the current container
  const px = (box) => ({
    x:      box.x      * dims.w,
    y:      box.y      * dims.h,
    width:  box.width  * dims.w,
    height: box.height * dims.h,
  })

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
              <rect
                x={p.x} y={p.y}
                width={p.width} height={p.height}
                fill="rgba(91,101,220,0.12)"
                stroke="#5b65dc"
                strokeWidth={sw}
                strokeDasharray={dash}
              />
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