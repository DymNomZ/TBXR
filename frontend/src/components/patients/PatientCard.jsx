import PatientForm from './PatientForm'
 
export default function PatientCard({ onSuccess }) {
  return (
    <div>
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">
          TB-XR
        </p>
        <h2 className="mt-3 text-2xl font-semibold text-[var(--deep-navy)]">
          New Patient
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
          Register a new patient for pulmonary TB screening.
        </p>
      </div>
 
      <PatientForm onSuccess={onSuccess} />
    </div>
  )
}