import AppLayout from '../components/layout/AppLayout';
import PatientTable from '../components/patients/PatientTable';

export default function PatientsPage() {
  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        {/* Page header */}
        <div>
          <h1 className="text-2xl font-bold text-[var(--deep-navy)] tracking-tight">
            Patients List
          </h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            All registered patient records
          </p>
        </div>

        {/* Table */}
        <PatientTable />
      </div>
    </AppLayout>
  );
}