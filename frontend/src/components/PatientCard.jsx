import PatientForm from './PatientForm'

function PatientCard() {
  return (
    <div className="min-h-screen bg-bright-snow flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-[28px] border border-slate-200 bg-white p-8 shadow-soft">
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">
            TB-XR
          </p>
          <h1 className="mt-4 text-4xl font-semibold text-slate-950">New Patient</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Register a new patient for pulmonary TB screening.
          </p>
        </div>

        <PatientForm />
      </div>
    </div>
  )
}

export default PatientCard