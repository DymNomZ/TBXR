import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, User, Hash, AlertTriangle } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import AnnotationCanvas from '../components/imaging/AnnotationCanvas'
import AnnotationPanel from '../components/imaging/AnnotationPanel'
import LongitudinalPanel from '../components/imaging/LongitudinalPanel'
import HeatmapViewer from '../components/imaging/HeatmapViewer'
import AIRiskBadge from '../components/ui/AIRiskBadge'
import StaticAnnotationOverlay from '../components/imaging/StaticAnnotationOverlay'

function getCsrfToken() {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith('csrftoken='))
    ?.split('=')[1] ?? ''
}

export default function AnnotationReviewPage() {
  const { transactionId } = useParams()
  const navigate = useNavigate()

  const [transform, setTransform] = useState({ scale: 1, translate: { x: 0, y: 0 } })
  const [boxes, setBoxes] = useState([])
  const [draftNotes, setDraftNotes] = useState('')
  const [xray, setXray] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lockInfo, setLockInfo] = useState(null)
  const [lockAcquired, setLockAcquired] = useState(false)
  const readOnly = Boolean(lockInfo)

  useEffect(() => {
    if (!transactionId) return

    const loadXray = async () => {
      setLoading(true)
      setLockInfo(null)
      setLockAcquired(false)

      try {
        const response = await fetch(`/api/imaging/xray/${transactionId}/`, { credentials: 'include' })
        const data = await response.json()

        if (response.status === 409) {
          setLockInfo({
            active_reviewer: data.active_reviewer,
            lock_timestamp: data.lock_timestamp,
            detail: data.detail,
          })
        } else if (response.ok) {
          setLockAcquired(true)
        }

        setXray(data)
      } catch {
        setXray(null)
      } finally {
        setLoading(false)
      }
    }

    loadXray()
  }, [transactionId])

  useEffect(() => {
    if (!transactionId || !lockAcquired || !xray || xray.status === 'COMPLETED' || readOnly) return

    let ignore = false
    fetch(`/api/imaging/xray/${transactionId}/draft/`, {
      credentials: 'include',
    })
      .then((response) => {
        if (!response.ok) {
          if (response.status === 404) {
            setBoxes([])
            setDraftNotes('')
          }
          return
        }
        return response.json()
      })
      .then((draft) => {
        if (!draft || ignore) return
        setBoxes(Array.isArray(draft.bounding_boxes) ? draft.bounding_boxes : [])
        setDraftNotes(draft.notes ?? '')
      })
      .catch(() => {})

    return () => {
      ignore = true
    }
  }, [transactionId, lockAcquired, xray, readOnly])

  useEffect(() => {
    if (!transactionId || !lockAcquired || !xray || xray.status === 'COMPLETED' || readOnly) return

    const timer = setTimeout(() => {
      fetch(`/api/imaging/xray/${transactionId}/draft/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({
          bounding_boxes: boxes,
          notes: draftNotes,
        }),
      }).catch(() => {})
    }, 400)

    return () => clearTimeout(timer)
  }, [transactionId, lockAcquired, xray, boxes, draftNotes, readOnly])

  // While this radiologist holds the lock: renew it on a heartbeat and release it
  // on the way out (in-app navigation, tab close/reload) so cases are not left blocked.
  useEffect(() => {
    if (!transactionId || !lockAcquired) return

    const release = (keepalive = false) =>
      fetch(`/api/imaging/xray/${transactionId}/release/`, {
        method: 'POST',
        credentials: 'include',
        keepalive,
        headers: { 'X-CSRFToken': getCsrfToken() },
      }).catch(() => {})

    const onPageHide = () => release(true)
    window.addEventListener('pagehide', onPageHide)

    const interval = setInterval(() => {
      if (document.visibilityState !== 'visible') return
      fetch(`/api/imaging/xray/${transactionId}/lock/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRFToken': getCsrfToken() },
      }).catch(() => {})
    }, 120000)

    return () => {
      window.removeEventListener('pagehide', onPageHide)
      clearInterval(interval)
      release()
    }
  }, [transactionId, lockAcquired])

  const patientName = xray ? `${xray.patient.first_name} ${xray.patient.last_name}` : null

  // Deletes from the bounding-box panel must run through the canvas's history
  // so Undo restores them; fall back to a direct filter when the canvas is not
  // mounted (e.g. read-only / completed views where deletes are disabled).
  const canvasDeleteRef = useRef(null)
  const registerCanvasDelete = useCallback((fn) => {
    canvasDeleteRef.current = fn
  }, [])

  const handleDeleteBox = useCallback((id) => {
    if (canvasDeleteRef.current) {
      canvasDeleteRef.current(id)
    } else {
      setBoxes((prev) => prev.filter((box) => box.id !== id))
    }
  }, [])

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
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

        {lockInfo && (
          <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">Read-only mode</p>
              <p>
                {lockInfo.detail} Active reviewer: <span className="font-semibold">{lockInfo.active_reviewer}</span>
                {lockInfo.lock_timestamp && (
                  <span> at {new Date(lockInfo.lock_timestamp).toLocaleString()}</span>
                )}
              </p>
            </div>
          </div>
        )}

        <div className="flex gap-6 items-start">
          <div className="flex-1 min-w-0">
            <HeatmapViewer
              rawImageUrl={xray?.display_image ?? null}
              heatmapUrl={xray?.ai_result?.heatmap_url ?? null}
              onTransformChange={setTransform}
              overlay={
                xray?.status === 'COMPLETED' || readOnly
                  ? <StaticAnnotationOverlay
                      annotations={xray?.annotations ?? []}
                      scale={transform.scale}
                      translate={transform.translate}
                    />
                  : <AnnotationCanvas
                      scale={transform.scale}
                      translate={transform.translate}
                      boxes={boxes}
                      onBoxesChange={setBoxes}
                      disabled={readOnly}
                      onDeleteBoxReady={registerCanvasDelete}
                    />
              }
            />
          </div>

          <AnnotationPanel
            transactionId={transactionId}
            boxes={boxes}
            draftNotes={draftNotes}
            onDraftNotesChange={setDraftNotes}
            onDeleteBox={handleDeleteBox}
            isCompleted={xray?.status === 'COMPLETED'}
            existingAnnotation={xray?.annotations?.[0] ?? null}
            readOnly={readOnly}
          />
        </div>

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