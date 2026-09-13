import { useState, useEffect } from 'react'
import { ArrowLeftRight, X } from 'lucide-react'
import Modal from '../ui/Modal'
import HeatmapViewer from './HeatmapViewer'
import StaticAnnotationOverlay from './StaticAnnotationOverlay'
import AIRiskBadge from '../ui/AIRiskBadge'
import StatusBadge from '../ui/StatusBadge'

const PROGRESSION_META = {
  no_prior: { label: 'No prior', color: '#94a3b8', soft: 'bg-slate-100 text-slate-700' },
  stable: { label: 'Stable', color: '#22c55e', soft: 'bg-green-100 text-green-700' },
  decreased_risk: { label: 'Improvement', color: '#3b82f6', soft: 'bg-blue-100 text-blue-700' },
  increased_risk: { label: 'Deterioration', color: '#ef4444', soft: 'bg-red-100 text-red-700' },
}

function formatDisplayDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('en-PH', { month: 'short', day: 'numeric', year: 'numeric' })
}

function TrendTooltip({ point }) {
  if (!point) return null
  const meta = PROGRESSION_META[point.status] ?? PROGRESSION_META.no_prior

  return (
    <div className="rounded-xl border border-[var(--border)] bg-white px-3 py-2 shadow-lg text-left min-w-[160px]">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--text-muted)]">AI trend</span>
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${meta.soft}`}>
          {meta.label}
        </span>
      </div>
      <div className="mt-2 text-sm font-semibold text-[var(--deep-navy)]">
        {typeof point.score === 'number' ? `${(point.score * 100).toFixed(0)}% risk` : 'No score'}
      </div>
      <div className="mt-1 text-[11px] text-[var(--text-muted)]">{formatDisplayDate(point.timestamp)}</div>
      {point.delta !== null && point.delta !== undefined && (
        <div className="mt-2 text-[11px] text-[var(--text-muted)]">
          Δ {Number(point.delta).toFixed(3)} vs prior
        </div>
      )}
    </div>
  )
}

function ProgressionTrendChart({ points }) {
  const [hoveredPoint, setHoveredPoint] = useState(null)
  const validPoints = Array.isArray(points) ? points.filter((point) => Number.isFinite(Number(point.score))) : []
  const pointsWithCoords = validPoints.map((point, index) => {
    const width = 640
    const height = 210
    const padding = { top: 18, right: 18, bottom: 28, left: 32 }
    const minScore = 0
    const maxScore = 1
    const xStep = validPoints.length > 1 ? (width - padding.left - padding.right) / (validPoints.length - 1) : 0
    const x = padding.left + index * xStep
    const y = padding.top + (1 - (Number(point.score) - minScore) / (maxScore - minScore || 1)) * (height - padding.top - padding.bottom)
    return { ...point, x, y }
  })

  useEffect(() => {
    if (!hoveredPoint && pointsWithCoords.length > 0) {
      setHoveredPoint(pointsWithCoords[pointsWithCoords.length - 1])
    }
  }, [hoveredPoint, pointsWithCoords])

  if (!points || points.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--surface-soft)] p-4 text-sm text-[var(--text-muted)]">
        No progression history is available yet.
      </div>
    )
  }

  if (!validPoints.length) {
    return (
      <div className="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--surface-soft)] p-4 text-sm text-[var(--text-muted)]">
        AI risk score is not available for these scans yet.
      </div>
    )
  }

  const width = 640
  const height = 210
  const padding = { top: 18, right: 18, bottom: 28, left: 32 }
  const path = pointsWithCoords
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ')

  const areaPath = `${path} L ${pointsWithCoords[pointsWithCoords.length - 1].x} ${height - padding.bottom} L ${pointsWithCoords[0].x} ${height - padding.bottom} Z`
  const activePoint = hoveredPoint ?? pointsWithCoords[pointsWithCoords.length - 1]

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-[var(--deep-navy)]">AI risk trend</h3>
          <p className="text-xs text-[var(--text-muted)]">Longitudinal risk score across scans</p>
        </div>
        {activePoint && (
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--text-muted)]">Latest</div>
            <div className="text-sm font-bold text-[var(--deep-navy)]">
              {(Number(activePoint.score) * 100).toFixed(0)}%
            </div>
          </div>
        )}
      </div>

      <div className="overflow-x-auto">
        <div className="min-w-[400px]">
          <svg viewBox={`0 0 ${width} ${height}`} className="h-52 w-full" role="img" aria-label="AI risk trend over time">
            <defs>
              <linearGradient id="progression-fill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#6ea8fe" stopOpacity="0.28" />
                <stop offset="100%" stopColor="#6ea8fe" stopOpacity="0.02" />
              </linearGradient>
            </defs>

            {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
              const y = padding.top + (1 - tick) * (height - padding.top - padding.bottom)
              return (
                <g key={tick}>
                  <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#e5e7eb" strokeDasharray="3 5" />
                  <text x={8} y={y + 4} fontSize="10" fill="#64748b">{tick * 100}%</text>
                </g>
              )
            })}

            <path d={areaPath} fill="url(#progression-fill)" />
            <path d={path} fill="none" stroke="#5b8def" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />

            {pointsWithCoords.map((point) => {
              const meta = PROGRESSION_META[point.status] ?? PROGRESSION_META.no_prior
              return (
                <g key={`${point.transaction_id}-${point.timestamp}`}>
                  <circle
                    cx={point.x}
                    cy={point.y}
                    r={activePoint?.transaction_id === point.transaction_id ? 7 : 5}
                    fill={meta.color}
                    stroke="white"
                    strokeWidth="2"
                    onMouseEnter={() => setHoveredPoint(point)}
                    onFocus={() => setHoveredPoint(point)}
                    onMouseLeave={() => setHoveredPoint(pointsWithCoords[pointsWithCoords.length - 1])}
                    tabIndex={0}
                    className="cursor-pointer outline-none"
                  />
                </g>
              )
            })}
          </svg>
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {points.map((point) => {
          const meta = PROGRESSION_META[point.status] ?? PROGRESSION_META.no_prior
          const isActive = activePoint?.transaction_id === point.transaction_id
          return (
            <button
              key={`${point.transaction_id}-${point.timestamp}`}
              type="button"
              onMouseEnter={() => setHoveredPoint(point)}
              onFocus={() => setHoveredPoint(point)}
              onMouseLeave={() => setHoveredPoint(pointsWithCoords[pointsWithCoords.length - 1])}
              className={`rounded-xl border px-2.5 py-2 text-left transition ${isActive ? 'border-[var(--accent)] bg-[var(--accent-soft)]' : 'border-[var(--border)] bg-[var(--surface-soft)]'}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--text-muted)]">{formatDisplayDate(point.timestamp)}</span>
                <span className={`inline-flex h-2.5 w-2.5 rounded-full`} style={{ backgroundColor: meta.color }} />
              </div>
              <div className="mt-2 text-xs font-semibold text-[var(--deep-navy)]">{meta.label}</div>
              <div className="mt-1 text-[11px] text-[var(--text-muted)]">
                {typeof point.score === 'number' ? `${(point.score * 100).toFixed(0)}% risk` : 'No score'}
              </div>
            </button>
          )
        })}
      </div>

      {activePoint && (
        <div className="mt-4 flex justify-end">
          <TrendTooltip point={activePoint} />
        </div>
      )}
    </div>
  )
}

// ─── Thumbnail card ───────────────────────────────────────────────────────────

function ThumbnailCard({ record, slot, onClick }) {
  const slotStyle = {
    A: 'ring-2 ring-[var(--accent)] border-[var(--accent)]',
    B: 'ring-2 ring-orange-400 border-orange-400',
  }
  const slotBadgeColor = {
    A: 'bg-[var(--accent)]',
    B: 'bg-orange-400',
  }

  return (
    <div
      onClick={onClick}
      className={`
        shrink-0 w-28 flex flex-col gap-1.5 rounded-xl border-2 overflow-hidden
        cursor-pointer transition-all duration-150
        ${slot ? slotStyle[slot] : 'border-[var(--border)] hover:border-[var(--accent)]'}
      `}
    >
      <div className="w-full aspect-square bg-black relative overflow-hidden">
        {record.display_image ? (
          <img src={record.display_image} alt={record.transaction_id} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-white/20 text-[10px]">No image</span>
          </div>
        )}
        {slot && (
          <span className={`absolute top-1.5 left-1.5 w-5 h-5 rounded-full text-white text-[10px] font-bold flex items-center justify-center ${slotBadgeColor[slot]}`}>
            {slot}
          </span>
        )}
      </div>
      <div className="px-2 pb-2 flex flex-col gap-1 min-w-0">
        <span className="text-[10px] text-[var(--text-muted)] truncate">
          {new Date(record.upload_timestamp).toLocaleDateString('en-PH')}
        </span>
        {record.ai_result
          ? <AIRiskBadge label={record.ai_result.risk_label} score={record.ai_result.risk_score} />
          : <StatusBadge status={record.status} />
        }
      </div>
    </div>
  )
}

// ─── Viewer slot ──────────────────────────────────────────────────────────────
// Owns its own transform state so StaticAnnotationOverlay stays in sync

function ViewerSlot({ record, label, labelColor }) {
  const [transform, setTransform] = useState({ scale: 1, translate: { x: 0, y: 0 } })
  const [xrayData, setXrayData] = useState(null)

  useEffect(() => {
    if (!record) return
    const controller = new AbortController()
    setXrayData(null)
    fetch(`/api/imaging/xray/${record.transaction_id}/`, {
      credentials: 'include',
      signal: controller.signal,
    })
      .then((r) => r.json())
      .then(setXrayData)
      .catch((err) => {
        if (err.name !== 'AbortError') console.error(err)
      })
    return () => controller.abort()
  }, [record?.transaction_id])

  if (!record) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[var(--border)] min-h-48 text-[var(--text-muted)]">
        <span className={`text-xs font-bold px-2 py-0.5 rounded-full text-white ${labelColor}`}>
          {label}
        </span>
        <p className="text-sm">Click a scan below to load</p>
      </div>
    )
  }

  const annotations = xrayData?.annotations ?? []

  return (
    <div className="flex-1 flex flex-col gap-3 min-w-0 overflow-y-auto max-h-[65vh]">
      <span className={`self-start text-xs font-bold px-2 py-0.5 rounded-full text-white ${labelColor}`}>
        {label}
      </span>

      <HeatmapViewer
        rawImageUrl={xrayData?.display_image ?? null}
        heatmapUrl={xrayData?.ai_result?.heatmap_url ?? null}
        onTransformChange={setTransform}
        overlay={
          <StaticAnnotationOverlay
            annotations={annotations}
            scale={transform.scale}
            translate={transform.translate}
          />
        }
      />

      {annotations.filter((a) => a.notes).map((ann, i) => (
        <div key={i} className="flex flex-col gap-1.5 p-3 rounded-xl bg-[var(--surface-soft)] border border-[var(--border)] text-xs shrink-0">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-[var(--accent)]">
              {ann.radiologist
                ? `${ann.radiologist.first_name} ${ann.radiologist.last_name}`
                : 'Radiologist'}
            </span>
            <span className="text-[var(--text-muted)]">
              {new Date(ann.submitted_at).toLocaleDateString('en-PH')}
            </span>
          </div>
          <p className="text-[var(--text)] leading-relaxed">{ann.notes}</p>
        </div>
      ))}
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function LongitudinalPanel({
  patientId,
  currentTransactionId = null,
  refreshKey = 0,
}) {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [compareOpen, setCompareOpen] = useState(false)
  const [progression, setProgression] = useState([])
  const [progressionLoading, setProgressionLoading] = useState(true)

  // Slots store full record objects — annotations travel with them
  const [slotA, setSlotA] = useState(null)
  const [slotB, setSlotB] = useState(null)

  useEffect(() => {
    if (!patientId) return

    setLoading(true)
    fetch(`/api/imaging/patients/${patientId}/history/`, { credentials: 'include' })
      .then((r) => r.json())
      .then((data) => {
        setRecords(data)
        if (currentTransactionId) {
          const match = data.find((r) => r.transaction_id === currentTransactionId)
          if (match) setSlotA(match)
        }
      })
      .finally(() => setLoading(false))
  }, [patientId, currentTransactionId, refreshKey])

  useEffect(() => {
    if (!patientId) {
      setProgression([])
      setProgressionLoading(false)
      return
    }

    setProgressionLoading(true)
    fetch(`/api/imaging/patients/${patientId}/progression/`, { credentials: 'include' })
      .then((r) => r.json())
      .then((data) => {
        const list = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : []
        setProgression(list)
      })
      .catch(() => setProgression([]))
      .finally(() => setProgressionLoading(false))
  }, [patientId, refreshKey])

  const getSlot = (txId) => {
    if (slotA?.transaction_id === txId) return 'A'
    if (slotB?.transaction_id === txId) return 'B'
    return null
  }

  const handleMainStripClick = (record) => {
    setSlotA(record)
    setSlotB(null)
    setCompareOpen(true)
  }

  const handleModalStripClick = (record) => {
    const txId = record.transaction_id
    if (slotA?.transaction_id === txId) {
      setSlotA(slotB ?? null)
      setSlotB(null)
    } else if (slotB?.transaction_id === txId) {
      setSlotB(null)
    } else if (!slotA) {
      setSlotA(record)
    } else {
      setSlotB(record)
    }
  }

  const handleSwap = () => {
    setSlotA(slotB)
    setSlotB(slotA)
  }

  const handleClose = () => {
    setCompareOpen(false)
    setSlotA(null)
    setSlotB(null)
  }

  return (
    <>
      <div className="bg-white rounded-2xl border border-[var(--border)] shadow-sm p-5 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-[var(--deep-navy)]">X-Ray History</h3>
          {records.length > 0 && (
            <span className="text-xs font-semibold bg-[var(--accent-soft)] text-[var(--accent)] px-2 py-0.5 rounded-full">
              {records.length} scan{records.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {loading ? (
          <div className="flex gap-3 overflow-x-auto pb-1">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="shrink-0 w-28 aspect-square rounded-xl bg-[var(--surface-soft)] animate-pulse" />
            ))}
          </div>
        ) : records.length === 0 ? (
          <p className="text-sm text-[var(--text-muted)] text-center py-6">No scan history yet.</p>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-1">
            {records.map((record) => (
              <ThumbnailCard
                key={record.transaction_id}
                record={record}
                slot={getSlot(record.transaction_id)}
                onClick={() => handleMainStripClick(record)}
              />
            ))}
          </div>
        )}
      </div>

      <div className="mt-6">
        {progressionLoading ? (
          <div className="rounded-2xl border border-[var(--border)] bg-white p-4 shadow-sm">
            <div className="h-8 w-40 rounded-full bg-[var(--surface-soft)] animate-pulse" />
            <div className="mt-4 h-52 w-full rounded-2xl bg-[var(--surface-soft)] animate-pulse" />
          </div>
        ) : (
          <ProgressionTrendChart points={progression} />
        )}
      </div>

      <Modal isOpen={compareOpen} onClose={handleClose} title="" hideClose noPadding size="3xl">
        <div className="flex flex-col gap-5 p-6">
          <div className="flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <span className="text-sm font-bold text-[var(--deep-navy)]">Scan Comparison</span>
              {slotA && slotB && (
                <button
                  onClick={handleSwap}
                  title="Swap A and B"
                  className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-[var(--surface-soft)] transition-colors"
                >
                  <ArrowLeftRight size={14} className="text-[var(--text-muted)]" />
                </button>
              )}
            </div>
            <button
              onClick={handleClose}
              className="w-8 h-8 flex items-center justify-center rounded-xl hover:bg-[var(--surface-soft)] transition-colors"
            >
              <X size={15} className="text-[var(--text-muted)]" />
            </button>
          </div>

          <div className="flex gap-4 items-start">
            <ViewerSlot
              key={slotA?.transaction_id ?? 'slot-a-empty'}
              record={slotA}
              label="A"
              labelColor="bg-[var(--accent)]"
            />
            <ViewerSlot
              key={slotB?.transaction_id ?? 'slot-b-empty'}
              record={slotB}
              label="B"
              labelColor="bg-orange-400"
            />
          </div>

          <div className="border-t border-[var(--border)] pt-4 shrink-0">
            <p className="text-xs text-[var(--text-muted)] mb-3">
              {!slotA
                ? 'Click a scan to load it.'
                : !slotB
                  ? 'Click another scan to compare side by side.'
                  : 'Click a scan to swap it in.'}
            </p>
            <div className="flex gap-3 overflow-x-auto pb-1">
              {records.map((record) => (
                <ThumbnailCard
                  key={record.transaction_id}
                  record={record}
                  slot={getSlot(record.transaction_id)}
                  onClick={() => handleModalStripClick(record)}
                />
              ))}
            </div>
          </div>
        </div>
      </Modal>
    </>
  )
}