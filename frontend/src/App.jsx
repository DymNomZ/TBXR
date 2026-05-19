import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import PatientsPage from './pages/PatientsPage'
import PatientCard from './components/patients/PatientCard'
import PatientDetailPage from './pages/PatientDetailPage';
import TechnologistDashboardPage from './pages/dashboard/TechnologistDashboardPage'
import RadiologistDashboardPage from './pages/dashboard/RadiologistDashboardPage'
import AnnotationReviewPage from './pages/AnnotationReviewPage'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Auth */}
          <Route path="/login" element={<LoginPage />} />

          {/* Dashboard */}
          <Route path="/dashboard/technologist" element={<TechnologistDashboardPage />} />
          <Route path="/dashboard/radiologist" element={<RadiologistDashboardPage />} />

          {/* Annotation review */}
          <Route path="/radiologist/review/:transactionId" element={<AnnotationReviewPage />} />

          {/* Patients */}
          <Route path="/patients" element={<PatientsPage />} />
          <Route path="/patients/:patientId" element={<PatientDetailPage />} />

          {/* Default redirect */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
