import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Table from '../ui/Table';
import StatusBadge from '../ui/StatusBadge';

// ✏️ This is your only edit point for the table structure.
// Each column needs:
//   key     — unique identifier
//   header  — column heading text
//   render  — function(row) → string | JSX
//   width   — (optional) CSS width hint
const COLUMNS = [
  {
    key: 'patient_id',
    header: 'Patient ID',
    width: '120px',
    render: (row) => (
      <span className="font-mono text-[var(--text-muted)]">{row.patient_id}</span>
    ),
  },
  {
    key: 'first_name',
    header: 'First Name',
    render: (row) => (
      <span className="font-medium text-[var(--text)]">{row.first_name}</span>
    ),
  },
  {
    key: 'last_name',
    header: 'Last Name',
    render: (row) => (
      <span className="font-medium text-[var(--text)]">{row.last_name}</span>
    ),
  },
  {
    key: 'date_of_birth',
    header: 'Date of Birth',
    render: (row) => row.date_of_birth,
  },
  {
    key: 'sex',
    header: 'Sex',
    width: '100px',
    render: (row) => row.sex,
  },
  {
    key: 'contact_number',
    header: 'Contact Number',
    render: (row) => row.contact_number,
  },
  // Example of a future status column — uncomment when needed:
  // {
  //   key: 'triage',
  //   header: 'Triage',
  //   render: (row) => <StatusBadge status={row.triage} />,
  // },
];

export default function PatientTable({ search = '' }) {
  const navigate = useNavigate()
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)

    const url = search.trim()
      ? `/api/patients/search/?name=${encodeURIComponent(search.trim())}`
      : '/api/patients/'

    fetch(url, {
      credentials: 'include',         // sends session cookie
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        setPatients(data)
        setLoading(false)
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        setError(err.message)
        setLoading(false)
      })

    return () => controller.abort()
  }, [search])

  if (loading) return (
    <div className="bg-white rounded-2xl border border-[var(--border)] p-12 text-center text-sm text-[var(--text-muted)]">
      Loading patients...
    </div>
  )

  if (error) return (
    <div className="bg-white rounded-2xl border border-[var(--border)] p-12 text-center text-sm text-[var(--danger)]">
      Failed to load patients: {error}
    </div>
  )

  return (
    <div className="bg-white rounded-2xl border border-[var(--border)] overflow-hidden shadow-sm">
      <Table
        columns={COLUMNS}
        data={patients}
        onRowClick={(row) => navigate(`/patients/${row.patient_id}`)}
      />
    </div>
  )
}