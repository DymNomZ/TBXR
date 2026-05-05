import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import PatientCard from './components/PatientCard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Auth */}
        <Route path="/login" element={<LoginPage />} />

        {/* Default redirect */}
        <Route path="*" element={<Navigate to="/login" replace />} />

        <Route path="/register" element={<PatientCard />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
