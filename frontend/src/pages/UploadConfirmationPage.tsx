import { useLocation, useNavigate } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import SuccessBanner from '../components/upload/SuccessBanner'
import DetailField from '../components/ui/DetailField'
import StatusBadge from '../components/ui/StatusBadge'

function formatTimestamp(raw: string | number | Date) {
  if (!raw) return '—'
  return new Date(raw).toLocaleString('en-PH', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export default function UploadConfirmationPage() {
  const location = useLocation()
  const navigate = useNavigate()

  const {
    transactionId   = 'a3f7b2c1-4e8d-4f2a-b1c3-d5e6f7a8b9c0',
    patientName     = 'Juan dela Cruz',
    uploadTimestamp = new Date().toISOString(),
    status          = 'Pending Review',
  } = location.state ?? {}

  return (
    <AppLayout>
      <div className="flex items-center justify-center py-10">
        <div className="w-full max-w-lg bg-white rounded-2xl border border-[var(--border)] shadow-sm overflow-hidden">

          <SuccessBanner
            title="Upload Successful"
            subtitle="The X-ray has been received and is awaiting radiologist review."
          />

          <div className="px-6 pt-5 pb-2">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-[var(--text-muted)] mb-1">
              Upload Details
            </p>
            <DetailField label="Transaction ID"  value={transactionId} mono />
            <DetailField label="Patient Name"    value={patientName} />
            <DetailField label="Upload Timestamp" value={formatTimestamp(uploadTimestamp)} />
            <DetailField label="Status"          value={<StatusBadge status={status} />} last />
          </div>

          <div className="px-6 pb-6 flex gap-3 pt-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex-1 py-3 bg-[var(--deep-navy)] text-white text-sm font-semibold rounded-xl hover:opacity-90 transition-opacity cursor-pointer"
            >
              Go to Dashboard
            </button>
            <button
              onClick={() => navigate('/upload')}
              className="flex-1 py-3 bg-transparent text-[var(--text)] text-sm font-medium rounded-xl border border-[var(--border)] hover:bg-[var(--surface-soft)] transition-colors cursor-pointer"
            >
              Upload Another
            </button>
          </div>

        </div>
      </div>
    </AppLayout>
  )
}