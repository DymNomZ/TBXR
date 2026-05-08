import { useState, useRef } from 'react'
import { Upload, FileImage, X } from 'lucide-react'
import Button from '../ui/Button'

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

export default function XrayUploadForm({ patientId, patientName, onSuccess }) {
  const [file, setFile]                 = useState(null)
  const [preview, setPreview]           = useState(null)
  const [isDragging, setIsDragging]     = useState(false)
  const [error, setError]               = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
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
        onSuccess?.(data)
        return
      }

      const data = await response.json().catch(() => null)
      const message = Array.isArray(data)
        ? data[0]
        : data?.error ?? data?.detail ?? `Upload failed (HTTP ${response.status}).`
      setError(message)
    } catch {
      setError('Unable to reach the server. Please try again.')
    }
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

      <Button type="submit" fullWidth disabled={isSubmitting || !file}>
        <Upload size={15} />
        {isSubmitting ? 'Uploading...' : 'Upload X-ray'}
      </Button>

    </form>
  )
}