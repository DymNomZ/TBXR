import { useState, useRef } from 'react'
import { Upload, FileImage, X } from 'lucide-react'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import { AI_DISCLAIMER_TEXT } from '../ui/AIDisclaimer'

const ACCEPTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.dcm']
const MAX_SIZE_MB = 20

function getCsrfToken() {
  return document.cookie
    .split('; ')
    .find((c) => c.startsWith('csrftoken='))
    ?.split('=')[1]
}

function validateFile(file) {
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!ACCEPTED_EXTENSIONS.includes(ext)) {
    return `Unsupported format "${ext}". Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}`
  }
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    return `File exceeds the ${MAX_SIZE_MB}MB limit.`
  }
  return null
}

function readErrorMessage(data, fallback) {
  if (Array.isArray(data)) return data[0]
  return data?.error ?? data?.detail ?? data?.message ?? fallback
}

function isLowQualityResponse(data) {
  return (
    data?.status === 'quality_check_failed'
    && data?.requires_confirmation === true
    && data?.can_proceed === true
    && Boolean(data?.transaction_id)
  )
}

function isManualReviewResponse(data) {
  return data?.status === 'MANUAL_REVIEW' && Boolean(data?.record)
}

export default function XrayUploadForm({ patientId, patientName, onSuccess }) {
  const [file, setFile]                 = useState(null)
  const [preview, setPreview]           = useState(null)
  const [isDragging, setIsDragging]     = useState(false)
  const [error, setError]               = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isProceedingLowQuality, setIsProceedingLowQuality] = useState(false)
  const [qualityPrompt, setQualityPrompt] = useState(null)
  const inputRef = useRef(null)

  const applyFile = (selected) => {
    setError('')
    const validationError = validateFile(selected)
    if (validationError) { setError(validationError); return }
    setFile(selected)
    const ext = selected.name.split('.').pop().toLowerCase()
    setPreview(['jpg', 'jpeg', 'png'].includes(ext) ? URL.createObjectURL(selected) : null)
  }

  const handleFileInput  = (e) => { if (e.target.files?.[0]) applyFile(e.target.files[0]) }
  const handleDrop       = (e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files?.[0]) applyFile(e.dataTransfer.files[0]) }

  const handleClear = () => {
    setFile(null); setPreview(null); setError('')
    if (inputRef.current) inputRef.current.value = ''
  }

  const completeConfirmedUpload = async (transactionId) => {
    const response = await fetch(`/api/imaging/patients/${patientId}/xray/upload/confirm/${transactionId}/`, {
      method: 'GET',
      credentials: 'include',
    })
    const data = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(readErrorMessage(data, 'Unable to load uploaded case details.'))
    }

    onSuccess?.(data)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) { setError('Please select a file before uploading.'); return }
    setIsSubmitting(true)
    setError('')

    const formData = new FormData()
    formData.append('raw_image', file)

    try {
      const response = await fetch(`/api/imaging/patients/${patientId}/xray/upload/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRFToken': getCsrfToken() ?? '' },
        body: formData,
      })

      if (response.ok) {
        const data = await response.json()
        if (isLowQualityResponse(data)) {
          setQualityPrompt({
            transactionId: data.transaction_id,
            qualityScore: data.quality_score,
            message: data.message,
          })
          return
        }

        if (isManualReviewResponse(data)) {
          // Upload succeeded, but AI inference failed; the backend has already flagged
          // the case for radiologist-only workflow.
          setError(data.message ?? 'AI processing failed. Case flagged for manual review.')
          onSuccess?.(data.record)
          return
        }

        onSuccess?.(data)
        return
      }

      const data = await response.json().catch(() => null)
      const message = readErrorMessage(data, `Upload failed (HTTP ${response.status}).`)
      setError(message)
    } catch {
      setError('Unable to reach the server. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleProceedAnyway = async () => {
    if (!qualityPrompt?.transactionId) return

    setIsProceedingLowQuality(true)
    setError('')
    try {
      const analyseResponse = await fetch(`/api/imaging/xray/${qualityPrompt.transactionId}/analyse/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken() ?? '',
        },
        body: JSON.stringify({ force_proceed: true }),
      })
      const analyseData = await analyseResponse.json().catch(() => null)

      if (!analyseResponse.ok) {
        setError(readErrorMessage(analyseData, 'Unable to continue with this image right now.'))
        return
      }

      if (isLowQualityResponse(analyseData)) {
        setError('Unable to continue: image quality confirmation did not clear. Please re-upload a clearer image.')
        return
      }

      await completeConfirmedUpload(qualityPrompt.transactionId)
      setQualityPrompt(null)
    } catch {
      setError('Unable to continue with this image right now. Please try again.')
    } finally {
      setIsProceedingLowQuality(false)
    }
  }

  const handleReupload = () => {
    setQualityPrompt(null)
    handleClear()
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">

      {/* Patient confirmation label */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--surface-soft)] border border-[var(--border)]">
        <span className="text-xs text-[var(--text-muted)]">Uploading for</span>
        <span className="text-sm font-semibold text-[var(--deep-navy)]">{patientName}</span>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !file && inputRef.current?.click()}
        className={`
          relative rounded-2xl border-2 border-dashed transition-all duration-150
          ${file
            ? 'border-[var(--accent)] bg-[var(--accent-soft)]'
            : 'border-[var(--border)] bg-[var(--surface-soft)] cursor-pointer hover:border-[var(--accent)] hover:bg-[var(--accent-soft)]'
          }
          ${isDragging ? 'border-[var(--accent)] bg-[var(--accent-soft)] scale-[1.01]' : ''}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".jpg,.jpeg,.png,.dcm"
          onChange={handleFileInput}
          className="hidden"
        />

        {/* No file selected */}
        {!file && (
          <div className="flex flex-col items-center justify-center gap-2 py-10 px-6 text-center">
            <div className="w-12 h-12 rounded-full bg-white border border-[var(--border)] flex items-center justify-center mb-1">
              <Upload size={20} className="text-[var(--text-muted)]" />
            </div>
            <p className="text-sm font-medium text-[var(--text)]">
              Click to select file{' '}
              <span className="text-[var(--text-muted)] font-normal">or drag and drop</span>
            </p>
            <p className="text-xs text-[var(--text-muted)]">
              DICOM (.dcm), JPEG (.jpg, .jpeg), PNG (.png) · Max {MAX_SIZE_MB}MB
            </p>
          </div>
        )}

        {/* File selected — image preview */}
        {file && preview && (
          <div className="flex flex-col items-center gap-3 p-5">
            <img
              src={preview}
              alt="X-ray preview"
              className="max-h-48 rounded-xl object-contain border border-[var(--border)]"
            />
            <p className="text-xs text-[var(--text-muted)] font-medium">{file.name}</p>
          </div>
        )}

        {/* File selected — DCM (no preview) */}
        {file && !preview && (
          <div className="flex flex-col items-center gap-2 py-8 px-6">
            <div className="w-12 h-12 rounded-full bg-white border border-[var(--border)] flex items-center justify-center">
              <FileImage size={20} className="text-[var(--accent)]" />
            </div>
            <p className="text-sm font-medium text-[var(--text)]">{file.name}</p>
            <p className="text-xs text-[var(--text-muted)]">DICOM file — preview not available</p>
          </div>
        )}

        {/* Clear button */}
        {file && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); handleClear() }}
            className="absolute top-3 right-3 w-7 h-7 flex items-center justify-center rounded-lg bg-white border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--danger)] transition-colors cursor-pointer"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <p className="text-xs font-medium text-[var(--danger)] px-1">{error}</p>
      )}

      <Button type="submit" fullWidth disabled={isSubmitting || isProceedingLowQuality || !file || Boolean(qualityPrompt)}>
        <Upload size={15} />
        {isSubmitting ? 'Uploading...' : 'Upload X-ray'}
      </Button>

      <Modal
        isOpen={Boolean(qualityPrompt)}
        onClose={() => {}}
        hideClose
        size="lg"
      >
        <div className="flex flex-col gap-4">
          <h3 className="text-xl font-semibold text-[var(--deep-navy)]">Low-quality image detected</h3>
          <p className="text-sm text-[var(--text)] leading-relaxed">
            {qualityPrompt?.message ?? 'The uploaded image may be too low quality for reliable AI interpretation.'}
          </p>
          {typeof qualityPrompt?.qualityScore === 'number' && (
            <p className="text-sm text-[var(--text-muted)]">
              Quality score: <span className="font-semibold text-[var(--text)]">{qualityPrompt.qualityScore.toFixed(2)}</span>
            </p>
          )}
          <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {AI_DISCLAIMER_TEXT}
          </p>
          <p className="text-sm text-[var(--text-muted)]">
            Continuing may reduce AI reliability. Re-upload a clearer image when available.
          </p>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="secondary"
              onClick={handleReupload}
              disabled={isProceedingLowQuality}
            >
              Re-upload
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={handleProceedAnyway}
              disabled={isProceedingLowQuality}
            >
              {isProceedingLowQuality ? 'Continuing...' : 'Proceed Anyway'}
            </Button>
          </div>
        </div>
      </Modal>

    </form>
  )
}