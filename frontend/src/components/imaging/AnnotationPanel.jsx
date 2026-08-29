import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Tag, Trash2, FileText, CheckCircle, AlertCircle, FileDown } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import Button from '../ui/Button'

// ─── CSRF helper ─────────────────────────────────────────────────────────────

function getCsrfToken() {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith('csrftoken='))
    ?.split('=')[1] ?? ''
}

// ─── Box list item ────────────────────────────────────────────────────────────

function BoxItem({ box, index, onDelete }) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl bg-[var(--surface-soft)] border border-[var(--border)]">
      <div className="w-6 h-6 rounded-lg bg-[var(--accent-soft)] flex items-center justify-center shrink-0 mt-0.5">
        <Tag size={12} className="text-[var(--accent)]" />
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-[var(--text)] truncate">
          {box.label || <span className="text-[var(--text-muted)] font-normal italic">Unlabeled</span>}
        </p>
        <p className="text-xs text-[var(--text-muted)] mt-0.5 font-mono">
          {Math.round(box.x)},{Math.round(box.y)} · {Math.round(box.width)}×{Math.round(box.height)}
        </p>
      </div>

      <button
        onClick={() => onDelete(index)}
        className="w-7 h-7 flex items-center justify-center rounded-lg text-[var(--text-muted)] hover:text-[var(--danger)] hover:bg-red-50 transition-colors shrink-0"
      >
        <Trash2 size={13} />
      </button>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function AnnotationPanel({
  transactionId,
  boxes = [],
  onDeleteBox,       // (index) => void — lets panel delete from canvas state
  isCompleted = false,
  existingAnnotation = null,
}) {
  const navigate = useNavigate()
  const [notes,   setNotes]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [success, setSuccess] = useState(false)
  const { user } = useAuth()
  const canDownload = isCompleted && (user?.role === 'RADIOLOGIST' || user?.role === 'RADIOLOGIC_TECH')

  useEffect(() => {
    if (isCompleted && existingAnnotation?.notes) {
      setNotes(existingAnnotation.notes)
    }
  }, [isCompleted, existingAnnotation])

  const handleSubmit = async () => {
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`/api/imaging/xray/${transactionId}/annotate/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({
          bounding_boxes: boxes,
          notes: notes.trim(),
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data?.errors?.bounding_boxes ?? data?.detail ?? `Server error (${res.status})`)
      }

      setSuccess(true)
      // Brief success flash, then navigate back
      setTimeout(() => navigate('/dashboard/radiologist'), 1200)

    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const displayBoxes = isCompleted
    ? (existingAnnotation?.bounding_boxes ?? [])
    : boxes

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="w-80 shrink-0 flex flex-col gap-4 h-full">

      {/* Bounding boxes */}
      <div className="bg-white rounded-2xl border border-[var(--border)] shadow-sm flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
          <h3 className="text-sm font-bold text-[var(--deep-navy)]">Bounding Boxes</h3>
          {displayBoxes.length > 0 && (
            <span className="text-xs font-semibold bg-[var(--accent-soft)] text-[var(--accent)] px-2 py-0.5 rounded-full">
              {displayBoxes.length}
            </span>
          )}
        </div>

        <div className="p-4 flex flex-col gap-2 max-h-64 overflow-y-auto">
          {displayBoxes.length > 0 ? (
            displayBoxes.map((box, i) => (
              <BoxItem
                key={i}
                box={box}
                index={i}
                onDelete={isCompleted ? () => {} : onDeleteBox}  // no-op when completed
              />
            ))
          ) : (
            <div className="py-8 text-center">
              <p className="text-sm text-[var(--text-muted)]">No boxes drawn yet.</p>
              <p className="text-xs text-[var(--text-muted)] mt-1">
                Click and drag on the image to annotate.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Diagnostic notes */}
      <div className="bg-white rounded-2xl border border-[var(--border)] shadow-sm flex flex-col">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-[var(--border)]">
          <FileText size={14} className="text-[var(--text-muted)]" />
          <h3 className="text-sm font-bold text-[var(--deep-navy)]">Diagnostic Notes</h3>
        </div>

        <div className="p-4">
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Enter your findings, observations, and recommendations…"
            rows={6}
            disabled={loading || success || isCompleted}
            className="w-full text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] bg-[var(--surface-soft)] border border-[var(--border)] rounded-xl px-4 py-3 resize-none outline-none focus:border-[var(--accent)] transition-colors disabled:opacity-60"
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
          <AlertCircle size={15} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Success */}
      {success && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-green-50 border border-green-200 text-sm text-green-700">
          <CheckCircle size={15} className="shrink-0" />
          <span>Findings submitted. Redirecting…</span>
        </div>
      )}

      {/* Submit */}
      <Button
        variant="primary"
        fullWidth
        disabled={loading || success || isCompleted}
        onClick={handleSubmit}
      >
        {loading ? 'Submitting…' : success ? 'Submitted ✓' : 'Submit Findings'}
      </Button>
      
      {/* Report actions */}
      {canDownload && (
        <>
          <Button
            variant="secondary"
            fullWidth
            onClick={() => navigate(`/radiologist/report/${transactionId}`)}
          >
            <FileText size={15} />
            Write Report
          </Button>

          <Button
            variant="secondary"
            fullWidth
            onClick={() => window.open(`/api/imaging/xray/${transactionId}/report/`, '_blank')}
          >
            <FileDown size={15} />
            Generate Report
          </Button>
        </>
      )}

    </div>
  )
}