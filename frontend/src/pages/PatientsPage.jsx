import { useSearchParams } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import PatientTable from '../components/patients/PatientTable';
import PatientSearchBar from '../components/patients/PatientSearchBar';

export default function PatientsPage() {
  const [searchParams] = useSearchParams();
  const search = searchParams.get('search') ?? '';

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        {/* Page header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[var(--deep-navy)] tracking-tight">
              Patients List
            </h1>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              All registered patient records
            </p>
          </div>
          <PatientSearchBar />
        </div>

        {/* Active search indicator */}
        {search && (
          <p className="text-sm text-[var(--text-muted)]">
            Showing results for{' '}
            <span className="font-semibold text-[var(--text)]">"{search}"</span>
          </p>
        )}

        <PatientTable search={search} />
      </div>
    </AppLayout>
  );
}