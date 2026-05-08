import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import PatientProfileCard from '../components/patients/PatientProfileCard';
import XrayRecordList from '../components/patients/XrayRecordList';

// 🔌 Replace with real fetch once backend confirms shape:
// GET /patients/:patientId  →  { patient, xray_records }
const MOCK_PATIENT = {
  patient_id:     'PT-0001',
  mrn:            'MRN-12345',
  first_name:     'Andrea',
  last_name:      'Hiyahiya',
  date_of_birth:  '1999-03-12',
  sex:            'Female',
  contact_number: '(280) 548-0124',
  total_records:  3,
};

const MOCK_RECORDS = [
  {
    transaction_id:    'TXN-38291827',
    date:              '2025-11-15 09:45:22',
    view_type:         'X-Ray Chest PA',
    status:            'Reviewed - Normal',
    reviewing_doctor:  'Dr. Smith',
  },
  {
    transaction_id:    'TXN-29384756',
    date:              '2025-08-03 11:20:18',
    view_type:         'X-Ray Chest PA',
    status:            'Reviewed - Abnormal',
    reviewing_doctor:  'Dr. Johnson',
  },
  {
    transaction_id:    'TXN-19283746',
    date:              '2025-03-22 15:35:41',
    view_type:         'X-Ray Chest Lateral',
    status:            'Reviewed - Normal',
    reviewing_doctor:  'Dr. Smith',
  },
];

export default function PatientDetailPage() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const [patient, setPatient] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const xrayRecords = MOCK_RECORDS; // replace later with real data from API

  useEffect(() => {
    fetch(`/api/patients/${patientId}/`, {
      credentials: 'include',
    })
      .then((res) => {
        if (res.status === 404) throw new Error('Patient not found.')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        setPatient(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [patientId])

  if (loading) return (
    <AppLayout>
      <div className="flex items-center justify-center py-24 text-sm text-[var(--text-muted)]">
        Loading patient...
      </div>
    </AppLayout>
  )

  if (error) return (
    <AppLayout>
      <div className="flex items-center justify-center py-24 text-sm text-[var(--danger)]">
        {error}
      </div>
    </AppLayout>
  )

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">

        {/* Back nav + page title */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/patients')}
            className="w-9 h-9 flex items-center justify-center rounded-xl border border-[var(--border)] hover:bg-[var(--surface-soft)] transition-colors"
          >
            <ArrowLeft size={16} className="text-[var(--text-muted)]" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-[var(--deep-navy)] tracking-tight">
              {patient.first_name} {patient.last_name}
            </h1>
            <p className="text-sm text-[var(--text-muted)]">
              Patient ID: {patient.patient_id}
            </p>
          </div>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <PatientProfileCard patient={patient} />
          <XrayRecordList records={xrayRecords} />
        </div>

      </div>
    </AppLayout>
  );
}