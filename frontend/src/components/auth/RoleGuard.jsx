import { Navigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const ROLE_DASHBOARD = {
  RADIOLOGIC_TECH: '/dashboard/technologist',
  RADIOLOGIST:     '/dashboard/radiologist',
}

export default function RoleGuard({ allowedRoles, children }) {
  const { user } = useAuth()

  // Not logged in at all
  if (!user) return <Navigate to="/login" replace />

  // Logged in but wrong role
  if (!allowedRoles.includes(user.role)) {
    const fallback = ROLE_DASHBOARD[user.role] ?? '/dashboard'
    return <Navigate to={fallback} replace />
  }

  return children
}