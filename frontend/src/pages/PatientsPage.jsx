import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import AppLayout from '../components/layout/AppLayout'
import PatientTable from '../components/patients/PatientTable'
import PatientSearchBar from '../components/patients/PatientSearchBar'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import PatientCard from '../components/patients/PatientCard'

export default function PatientsPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const search = searchParams.get('search') ?? ''
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  // Only technologists intake patients; other clinical roles may view the list.
  const canRegisterPatients = user?.role === 'RADIOLOGIC_TECH'

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

          {/* Search + New Patient — grouped on the right */}
          <div className="flex items-center gap-3">
            {canRegisterPatients && (
              <Button onClick={() => setIsModalOpen(true)}>
                <Plus size={16} />
                New Patient
              </Button>
            )}
            <PatientSearchBar />
          </div>
        </div>

        {/* Active search indicator */}
        {search && (
          <p className="text-sm text-[var(--text-muted)]">
            Showing results for{' '}
            <span className="font-semibold text-[var(--text)]">"{search}"</span>
          </p>
        )}

        <PatientTable search={search} refreshKey={refreshKey} />
      </div>

      {/* New Patient modal (technologists only) */}
      {canRegisterPatients && (
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
        >
          <PatientCard onSuccess={() => {
            setIsModalOpen(false)
            setRefreshKey((k) => k + 1)
          }} />
        </Modal>
      )}
    </AppLayout>
  )
}