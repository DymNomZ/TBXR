import AppLayout from '../../components/layout/AppLayout'

export default function PatientDashboardPage() {
  return (
    <AppLayout>
      <section className="rounded-xl border border-[var(--border)] bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold text-[var(--deep-navy)]">Patient Validation Dashboard</h1>
        <p className="mt-3 text-sm text-[var(--muted)]">
          This read-only dashboard is being staged. Validation respondents will be able to view finalized
          reports and case details without edit permissions.
        </p>
      </section>
    </AppLayout>
  )
}
