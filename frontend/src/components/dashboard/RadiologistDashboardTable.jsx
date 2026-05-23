import { useNavigate } from 'react-router-dom'
import Table from '../ui/Table'
import StatusBadge from '../ui/StatusBadge'
import Button from '../ui/Button'
import AIRiskBadge from '../ui/AIRiskBadge'

// ✏️ Tag filterable: true to auto-add a filter dropdown for that column
export const QUEUE_COLUMNS = [
  {
    key: 'transaction_id',
    header: 'Transaction ID',
    filterable: false,
    width: '160px',
    render: (row) => (
      <span className="font-mono text-xs text-[var(--text-muted)]">
        {row.transaction_id}
      </span>
    ),
  },
  {
    key: 'patient_id',
    header: 'Patient ID',
    filterable: false,
    width: '160px',
    render: (row) => (
        <span className="text-xs text-[var(--text-muted)]">{row.patient.patient_id}</span>
    ),
  },
  {
    key: 'first_name',
    header: 'First Name',
    width: '160px',
    render: (row) => (
      <span className="font-medium text-[var(--text)]">{row.patient.first_name}</span>
    ),
  },
  {
    key: 'last_name',
    header: 'Last Name',
    width: '160px',
    render: (row) => (
      <span className="font-medium text-[var(--text)]">{row.patient.last_name}</span>
    ),
  },
  {
    key: 'upload_timestamp',
    header: 'Upload Date',
    filterable: false,
    width: '160px',
    render: (row) => (
      <span className="text-sm text-[var(--text-muted)]">
        {new Date(row.upload_timestamp).toLocaleString()}
      </span>
    ),
  },
  {
    key: 'uploader',
    header: 'Uploader',
    filterable: false,
    width: '140px',
    render: (row) => (
      <span className="text-sm text-[var(--text)]">
        {row.uploader?.username ?? '—'}
      </span>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    label: 'Statuses',
    filterable: true,
    filterOptions: ['PENDING', 'IN_REVIEW', 'AI_REVIEWED', 'COMPLETED'],
    width: '140px',
    render: (row) => <StatusBadge status={row.status} />,
  },
  {
    key: 'risk_score',
    header: 'AI Risk Score',
    label: 'Scores',
    filterable: true,
    filterOptions: ['LOW', 'HIGH'],
    width: '140px',
    render: (row) => row.ai_result
      ? <AIRiskBadge label={row.ai_result.risk_label} score={row.ai_result.risk_score} />
      : <span className="text-xs text-[var(--text-muted)]">—</span>,
  },
  {
    key: 'action',
    header: 'Action',
    filterable: false,
    width: '140px',
    render: (row) => <ReviewButton record={row} />,
  },
]

function ReviewButton({ record }) {
  const navigate = useNavigate()
  return (
    <Button
      size="sm"
      variant="primary"
      onClick={(e) => {
        e.stopPropagation()
        navigate(`/radiologist/review/${record.transaction_id}`)
      }}
    >
      Review →
    </Button>
  )
}

export default function RadiologistDashboardTable({ data = [] }) {
  const navigate = useNavigate()

  return (
    <div className="bg-white rounded-2xl border border-[var(--border)] shadow-sm overflow-hidden">
      <Table
        columns={QUEUE_COLUMNS}
        data={data}
        // onRowClick={(row) => navigate(`/radiologist/review/${row.transaction_id}`)}
      />
    </div>
  )
}