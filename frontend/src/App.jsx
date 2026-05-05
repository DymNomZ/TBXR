import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import PatientsPage from './pages/PatientsPage'
import PatientCard from './components/patients/PatientCard'
import PatientDetailPage from './pages/PatientDetailPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Auth */}
        <Route path="/login" element={<LoginPage />} />

        {/* Default redirect */}
        <Route path="*" element={<Navigate to="/login" replace />} />

        {/* Patients */}
        <Route path="/patients" element={<PatientsPage />} />
        <Route path="/patients/register" element={<PatientCard />} />
        <Route path="/patients/:patientId" element={<PatientDetailPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
