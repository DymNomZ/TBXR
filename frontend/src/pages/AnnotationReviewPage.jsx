import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, User, Hash } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import XrayViewer from '../components/imaging/XrayViewer'
import AnnotationCanvas from '../components/imaging/AnnotationCanvas'
import AnnotationPanel from '../components/imaging/AnnotationPanel'
import LongitudinalPanel from '../components/imaging/LongitudinalPanel'
import HeatmapViewer from '../components/imaging/HeatmapViewer'
import AIRiskBadge from '../components/ui/AIRiskBadge'
import StaticAnnotationOverlay from '../components/imaging/StaticAnnotationOverlay'

export default function AnnotationReviewPage() {
  const { transactionId } = useParams()
  const navigate          = useNavigate()

  // Shared canvas state
  const [transform, setTransform] = useState({ scale: 1, translate: { x: 0, y: 0 } })
  const [boxes,     setBoxes]     = useState([])

  // Xray detail — drives header, HeatmapViewer URLs, and LongitudinalPanel
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
    : null

  const handleDeleteBox = (index) => {
    setBoxes((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">

        {/* ── Page header ── */}
        <div className="flex items-center gap-4 shrink-0">
          <button
            onClick={() => navigate('/dashboard/radiologist')}
            className="w-9 h-9 flex items-center justify-center rounded-xl border border-[var(--border)] hover:bg-[var(--surface-soft)] transition-colors shrink-0"
          >
            <ArrowLeft size={16} className="text-[var(--text-muted)]" />
          </button>

          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-[var(--deep-navy)] tracking-tight leading-none">
                Annotation Review
              </h1>
              {/* AI risk badge in header — shows as soon as xray loads */}
              {xray?.ai_result && (
                <AIRiskBadge
                  label={xray.ai_result.risk_label}
                  score={xray.ai_result.risk_score}
                />
              )}
            </div>

            {loading ? (
              <div className="h-4 w-56 bg-[var(--surface-soft)] rounded animate-pulse mt-0.5" />
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
                {xray?.ai_result?.model_version && (
                  <>
                    <span className="text-[var(--border)]">·</span>
                    <span className="text-xs">{xray.ai_result.model_version}</span>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Two-column: viewer + annotation panel ── */}
        <div className="flex gap-6 items-start">

          {/* Left — HeatmapViewer with AnnotationCanvas overlay */}
          <div className="flex-1 min-w-0">
            <HeatmapViewer
              rawImageUrl={xray?.display_image ?? null}
              heatmapUrl={xray?.ai_result?.heatmap_url ?? null}
              // aiResult intentionally omitted — badge is in the header, not duplicated here
              onTransformChange={setTransform}
              overlay={
                xray?.status === 'COMPLETED'
                  ? <StaticAnnotationOverlay
                      annotations={xray.annotations ?? []}
                      scale={transform.scale}
                      translate={transform.translate}
                    />
                  : <AnnotationCanvas
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
            isCompleted={xray?.status === 'COMPLETED'}
            existingAnnotation={xray?.annotations?.[0] ?? null}
          />

        </div>

        {/* ── Longitudinal panel — full width below ── */}
        {xray?.patient?.patient_id && (
          <LongitudinalPanel
            patientId={xray.patient.patient_id}
            currentTransactionId={transactionId}
          />
        )}

      </div>
    </AppLayout>
  )
}