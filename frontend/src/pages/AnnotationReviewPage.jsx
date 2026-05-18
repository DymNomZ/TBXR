import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, User, Hash } from 'lucide-react'
import AppLayout from '@/components/layout/AppLayout'
import XrayViewer from '@/components/imaging/XrayViewer'
import AnnotationCanvas from '@/components/imaging/AnnotationCanvas'
import AnnotationPanel from '@/components/imaging/AnnotationPanel'

export default function AnnotationReviewPage() {
  const { transactionId } = useParams()
  const navigate          = useNavigate()

  // Shared state between canvas and panel
  const [transform, setTransform] = useState({ scale: 1, translate: { x: 0, y: 0 } })
  const [boxes,     setBoxes]     = useState([])

  // Header info — fetched separately from what XrayViewer fetches internally
  // Browser caches the identical GET so this is not a second network call
  const [xray,    setXray]    = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!transactionId) return
    setLoading(true)
    fetch(`/api/imaging/xray/${transactionId}/`, { credentials: 'include' })
      .then((r) => r.json())
      .then(setXray)
      .finally(() => setLoading(false))
  }, [transactionId])

  const patientName = xray
    ? `${xray.patient.first_name} ${xray.patient.last_name}`
    : '—'

  const handleDeleteBox = (index) => {
    setBoxes((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <AppLayout>
      <div className="flex flex-col gap-5 h-full">

        {/* ── Page header ── */}
        <div className="flex items-center gap-4 shrink-0">
          <button
            onClick={() => navigate('/dashboard/radiologist')}
            className="w-9 h-9 flex items-center justify-center rounded-xl border border-[var(--border)] hover:bg-[var(--surface-soft)] transition-colors shrink-0"
          >
            <ArrowLeft size={16} className="text-[var(--text-muted)]" />
          </button>

          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl font-bold text-[var(--deep-navy)] tracking-tight leading-none">
              Annotation Review
            </h1>
            {loading ? (
              <div className="h-4 w-48 bg-[var(--surface-soft)] rounded animate-pulse mt-1" />
            ) : (
              <div className="flex items-center gap-3 text-sm text-[var(--text-muted)]">
                <span className="flex items-center gap-1.5">
                  <User size={12} />
                  {patientName}
                </span>
                <span className="text-[var(--border)]">·</span>
                <span className="flex items-center gap-1.5 font-mono">
                  <Hash size={12} />
                  {transactionId}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* ── Two-column layout ── */}
        <div className="flex gap-6 flex-1 min-h-0">

          {/* Left — viewer + canvas overlay */}
          <div className="flex-1 min-w-0">
            <XrayViewer
              transactionId={transactionId}
              onTransformChange={setTransform}
              overlay={
                <AnnotationCanvas
                  scale={transform.scale}
                  translate={transform.translate}
                  onBoxesChange={setBoxes}
                />
              }
            />
          </div>

          {/* Right — annotation panel */}
          <AnnotationPanel
            transactionId={transactionId}
            boxes={boxes}
            onDeleteBox={handleDeleteBox}
          />

        </div>
      </div>
    </AppLayout>
  )
}