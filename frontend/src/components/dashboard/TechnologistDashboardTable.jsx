import { useNavigate } from 'react-router-dom'
import Table from '../ui/Table'
import StatusBadge from '../ui/StatusBadge'
import Button from '../ui/Button'

// ✏️ Tag a column as filterable to automatically add it to the filter bar
// filterable: true  →  FilterBar generates a dropdown for this column
// filterOptions     →  the options in that dropdown
export const DASHBOARD_COLUMNS = [
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
    key: 'status',
    header: 'Status',
    label: 'Statuses',
    filterable: true,
    // ✏️ Keep in sync with backend statuses
    filterOptions: ['PENDING', 'IN_REVIEW', 'COMPLETED'],
    width: '140px',
    render: (row) => <StatusBadge status={row.status} />,
  },
  {
    key: 'action',
    header: 'Action',
    filterable: false,
    width: '130px',
    render: (row) => <DashboardActionButton record={row} />,
  },
]

// ✏️ Update action map if new statuses are added
const ACTION_MAP = {
  'PENDING': 'primary',
  'IN_REVIEW': 'accent',
  'COMPLETED': 'secondary',
}

function DashboardActionButton({ record }) {
  const navigate = useNavigate()
  const action = { label: 'View →', variant: ACTION_MAP[record.status] ?? 'primary' }

  return (
    <Button
      size="sm"
      variant={action.variant}
      onClick={(e) => {
        e.stopPropagation() // prevent row click double-fire
        navigate(`/transactions/${record.transaction_id}`) // <--- Link to actual transaction detail view
      }}
    >
      {action.label}
    </Button>
  )
}

export default function TechnologistDashboardTable({ data = [] }) {
  const navigate = useNavigate()

  return (
    <div className="bg-white rounded-2xl border border-[var(--border)] shadow-sm overflow-hidden">
      <Table
        columns={DASHBOARD_COLUMNS}
        data={data}
        onRowClick={(row) => navigate(`/transactions/${row.transaction_id}`)}
      />
    </div>
  )
}