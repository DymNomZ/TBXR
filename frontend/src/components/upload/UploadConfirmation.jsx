import SuccessBanner from './SuccessBanner'
import DetailField from '../ui/DetailField'
import StatusBadge from '../ui/StatusBadge'
import Button from '../ui/Button'

function formatTimestamp(raw) {
  if (!raw) return '—'
  return new Date(raw).toLocaleString('en-PH', {
    year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

export default function UploadConfirmation({ data, patientName, onDashboard, onUploadAnother }) {
  const { transaction_id, status, upload_timestamp } = data

  return (
    <div className="overflow-hidden rounded-[28px]">

      {/* Full-bleed success banner — no outer padding so it extends edge to edge */}
      <SuccessBanner
        title="Upload Successful"
        subtitle="The X-ray has been received and is awaiting radiologist review."
      />

      {/* Detail fields */}
      <div className="px-6 pt-5 pb-2">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-[var(--text-muted)] mb-1">
          Upload Details
        </p>
        <DetailField label="Transaction ID"   value={transaction_id} mono />
        <DetailField label="Patient Name"     value={patientName} />
        <DetailField label="Upload Timestamp" value={formatTimestamp(upload_timestamp)} />
        <DetailField label="Status"           value={<StatusBadge status={status} />} last />
      </div>

      {/* Actions */}
      <div className="px-6 pb-6 pt-4 flex gap-3">
        <Button onClick={onDashboard} className="flex-1">
          Go to Dashboard
        </Button>
        <Button onClick={onUploadAnother} variant="secondary" className="flex-1">
          Upload Another
        </Button>
      </div>

    </div>
  )
}
