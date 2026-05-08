import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Upload} from 'lucide-react';
import { useState, useEffect } from 'react';
import AppLayout from '../components/layout/AppLayout';
import PatientProfileCard from '../components/patients/PatientProfileCard';
import XrayRecordList from '../components/patients/XrayRecordList';
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import XrayUploadForm from '../components/upload/XrayUploadForm'
import UploadConfirmation from '../components/upload/UploadConfirmation'

export default function PatientDetailPage() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const [patient, setPatient] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isUploadOpen, setIsUploadOpen] = useState(false)
  const [isConfirmOpen, setIsConfirmOpen] = useState(false)
  const [uploadResult, setUploadResult]   = useState(null)
  const [xrayRefreshKey, setXrayRefreshKey] = useState(0)

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

  const handleUploadSuccess = (data) => {
    setUploadResult(data)           // set data first
    setXrayRefreshKey((k) => k + 1)
    setIsUploadOpen(false)          // close upload modal
    setTimeout(() => setIsConfirmOpen(true), 250)  // open confirm after animation
  }

  const handleDashboard = () => {
    setIsConfirmOpen(false)
    navigate('/dashboard')
  }
 
  const handleUploadAnother = () => {
    setIsConfirmOpen(false)
    // Wait for confirmation modal exit animation before reopening upload
    setTimeout(() => setIsUploadOpen(true), 250)
  }

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

  const patientName = `${patient.first_name} ${patient.last_name}`

   return (
    <AppLayout>
      <div className="flex flex-col gap-6">
 
        {/* Back nav + page title + Upload button */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/patients')}
              className="w-9 h-9 flex items-center justify-center rounded-xl border border-[var(--border)] hover:bg-[var(--surface-soft)] transition-colors"
            >
              <ArrowLeft size={16} className="text-[var(--text-muted)]" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-[var(--deep-navy)] tracking-tight">
                {patientName}
              </h1>
              <p className="text-sm text-[var(--text-muted)]">
                Patient ID: {patient.patient_id}
              </p>
            </div>
          </div>
 
          <Button onClick={() => setIsUploadOpen(true)}>
            <Upload size={15} />
            Upload X-ray
          </Button>
        </div>
 
        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <PatientProfileCard patient={patient} />
          <XrayRecordList patientId={patientId} refreshKey={xrayRefreshKey} />
        </div>
 
      </div>
 
      {/* Upload X-ray modal */}
      <Modal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        title="Upload X-ray"
      >
        <XrayUploadForm
          patientId={patientId}
          patientName={patientName}
          onSuccess={handleUploadSuccess}
        />
      </Modal>

      {/* Upload confirmation modal */}
      <Modal
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        noPadding
        hideClose
      >
        {uploadResult && (
          <UploadConfirmation
            data={uploadResult}
            patientName={patientName}
            onDashboard={handleDashboard}
            onUploadAnother={handleUploadAnother}
          />
        )}
      </Modal>
 
    </AppLayout>
  )
}