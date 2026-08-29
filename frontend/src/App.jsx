import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import PatientsPage from './pages/PatientsPage'
import PatientDetailPage from './pages/PatientDetailPage';
import TechnologistDashboardPage from './pages/dashboard/TechnologistDashboardPage'
import RadiologistDashboardPage from './pages/dashboard/RadiologistDashboardPage'
import AnnotationReviewPage from './pages/AnnotationReviewPage'
import ReportWritePage from './pages/ReportWritePage'
import RoleGuard from './components/auth/RoleGuard'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Auth */}
          <Route path="/login" element={<LoginPage />} />

          {/* Dashboard */}
          <Route
            path="/dashboard/technologist"
            element={
              <RoleGuard allowedRoles={['RADIOLOGIC_TECH']}>
                <TechnologistDashboardPage />
              </RoleGuard>
            }
          />
          <Route
            path="/dashboard/radiologist"
            element={
              <RoleGuard allowedRoles={['RADIOLOGIST']}>
                <RadiologistDashboardPage />
              </RoleGuard>
            }
          />

          {/* Annotation review */}
          <Route
            path="/radiologist/review/:transactionId"
            element={
              <RoleGuard allowedRoles={['RADIOLOGIST']}>
                <AnnotationReviewPage />
              </RoleGuard>
            }
          />
          <Route
            path="/radiologist/report/:transactionId"
            element={
              <RoleGuard allowedRoles={['RADIOLOGIST']}>
                <ReportWritePage />
              </RoleGuard>
            }
          />

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
