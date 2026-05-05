import { useNavigate } from 'react-router-dom';
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
    key: 'full_name',
    header: 'Full Name',
    render: (row) => (
      <span className="font-medium text-[var(--text)]">{row.full_name}</span>
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

// Placeholder until GET /patients/ is confirmed with backend
const MOCK_DATA = [
  { id: 1, patient_id: 'PT-0001', full_name: 'Andrea Hiyahiya', date_of_birth: '1999-03-12', sex: 'Female', contact_number: '(280) 548-0124' },
  { id: 2, patient_id: 'PT-0002', full_name: 'Bianca Lalema',   date_of_birth: '1982-07-04', sex: 'Female', contact_number: '(124) 864-1794' },
  { id: 3, patient_id: 'PT-0003', full_name: 'John Smith',      date_of_birth: '1997-11-23', sex: 'Male',   contact_number: '(789) 164-4876' },
];

export default function PatientTable({ search = '' }) {

  // 🔌 Replace this with your real fetch when backend is ready:
  //
  // const { data, isLoading } = useQuery({
  //   queryKey: ['patients', search],
  //   queryFn: () => fetch(`/api/patients/?search=${encodeURIComponent(search)}`).then(r => r.json()),
  // });

  // --- MOCK: filter locally until backend is wired ---
  const filtered = MOCK_DATA.filter((p) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      p.full_name.toLowerCase().includes(q) ||
      p.patient_id.toLowerCase().includes(q)
    );
  });

  const navigate = useNavigate();

  return (
    <div className="bg-white rounded-2xl border border-[var(--border)] overflow-hidden shadow-sm">
      <Table
        columns={COLUMNS}
        data={filtered}   // was MOCK_DATA, now filtered
        onRowClick={(row) => navigate(`/patients/${row.patient_id}`)}
      />
    </div>
  );
}