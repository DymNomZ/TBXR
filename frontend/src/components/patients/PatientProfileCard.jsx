import { User } from 'lucide-react';
import DetailField from '../ui/DetailField'

export default function PatientProfileCard({ patient }) {
  if (!patient) return null;

  const sexMap = {
    M: 'Male',
    F: 'Female',
    O: 'Other',
  };

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
      <DetailField label="Full Name"       value={`${patient.first_name} ${patient.last_name}`} />
      <DetailField label="Patient ID"      value={patient.patient_id} />
      <DetailField label="MRN"             value={patient.mrn} />
      <DetailField label="Date of Birth"   value={patient.date_of_birth} />
      <DetailField label="Sex"             value={sexMap[patient.sex] || 'Unknown'} />
      <DetailField label="Contact Number"  value={patient.contact_number} />
      <DetailField label="Total Records"   value={patient.total_records ?? 0} last />
    </div>
  );
}