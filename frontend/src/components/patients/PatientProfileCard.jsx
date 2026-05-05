import { User } from 'lucide-react';

const FIELD_ROW = ({ label, value }) => (
  <div className="flex items-center justify-between py-3 border-b border-[var(--border)] last:border-none">
    <span className="text-sm text-[var(--text-muted)]">{label}</span>
    <span className="text-sm font-medium text-[var(--text)]">{value ?? '—'}</span>
  </div>
);

export default function PatientProfileCard({ patient }) {
  if (!patient) return null;

  return (
    <div className="bg-white rounded-2xl border border-[var(--border)] shadow-sm p-6 flex flex-col gap-1">
      {/* Card header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-full bg-[var(--accent-soft)] flex items-center justify-center">
          <User size={16} className="text-[var(--accent)]" />
        </div>
        <h2 className="text-base font-bold text-[var(--deep-navy)]">Patient Profile</h2>
      </div>

      {/* Fields */}
      <FIELD_ROW label="Full Name"       value={`${patient.first_name} ${patient.last_name}`} />
      <FIELD_ROW label="Patient ID"      value={patient.patient_id} />
      <FIELD_ROW label="MRN"             value={patient.mrn} />
      <FIELD_ROW label="Date of Birth"   value={patient.date_of_birth} />
      <FIELD_ROW label="Sex"             value={patient.sex} />
      <FIELD_ROW label="Contact Number"  value={patient.contact_number} />
      <FIELD_ROW label="Total Records"   value={patient.total_records ?? 0} />
    </div>
  );
}