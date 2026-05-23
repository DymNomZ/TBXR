import { useState, useEffect } from 'react'
import { ArrowLeftRight, X } from 'lucide-react'
import Modal from '../ui/Modal'
import HeatmapViewer from './HeatmapViewer'
import StaticAnnotationOverlay from './StaticAnnotationOverlay'
import AIRiskBadge from '../ui/AIRiskBadge'
import StatusBadge from '../ui/StatusBadge'

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
  const [xrayData, setXrayData]   = useState(null)

  useEffect(() => {
    if (!record) return
    setXrayData(null)
    fetch(`/api/imaging/xray/${record.transaction_id}/`, { credentials: 'include' })
      .then((r) => r.json())
      .then(setXrayData)
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
  const [records,     setRecords]     = useState([])
  const [loading,     setLoading]     = useState(true)
  const [compareOpen, setCompareOpen] = useState(false)

  // Slots store full record objects — annotations travel with them
  const [slotA, setSlotA] = useState(null)
  const [slotB, setSlotB] = useState(null)

  // ── Fetch history ───────────────────────────────────────────────────────────

  useEffect(() => {
    if (!patientId) return
    setLoading(true)
    fetch(`/api/imaging/patients/${patientId}/history/`, { credentials: 'include' })
      .then((r) => r.json())
      .then((data) => {
        setRecords(data)
        // Pre-fill slot A if currentTransactionId provided
        if (currentTransactionId) {
          const match = data.find((r) => r.transaction_id === currentTransactionId)
          if (match) setSlotA(match)
        }
      })
      .finally(() => setLoading(false))
  }, [patientId, currentTransactionId, refreshKey])

  // ── Slot helpers ────────────────────────────────────────────────────────────

  const getSlot = (txId) => {
    if (slotA?.transaction_id === txId) return 'A'
    if (slotB?.transaction_id === txId) return 'B'
    return null
  }

  // Main strip: always opens modal with clicked record as A
  const handleMainStripClick = (record) => {
    setSlotA(record)
    setSlotB(null)
    setCompareOpen(true)
  }

  // Modal strip: toggle/assign slots
  const handleModalStripClick = (record) => {
    const txId = record.transaction_id
    if (slotA?.transaction_id === txId) {
      // Clicking A: promote B to A, clear B
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

  const handleSwap = () => { setSlotA(slotB); setSlotB(slotA) }

  // ← Clears both slots so thumbnail highlights reset on close
  const handleClose = () => {
    setCompareOpen(false)
    setSlotA(null)
    setSlotB(null)
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <>
      {/* Main timeline strip */}
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

      {/* Comparison modal */}
      <Modal isOpen={compareOpen} onClose={handleClose} title="" hideClose noPadding size="4xl">
        <div className="flex flex-col gap-5 p-6">

          {/* Header */}
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

          {/* Side-by-side viewers */}
          <div className="flex gap-4 items-start">
            <ViewerSlot record={slotA} label="A" labelColor="bg-[var(--accent)]" />
            <ViewerSlot record={slotB} label="B" labelColor="bg-orange-400" />
          </div>

          {/* Timeline strip inside modal */}
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