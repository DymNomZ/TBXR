import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

const ROLE_DASHBOARD = {
  RADIOLOGIC_TECH: '/dashboard/technologist',
  RADIOLOGIST:     '/dashboard/radiologist',
  PHYSICIAN:       '/dashboard/physician',
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    // Persist across page refreshes
    const stored = localStorage.getItem('user')
    return stored ? JSON.parse(stored) : null
  })

  const login = (userData) => {
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, ROLE_DASHBOARD }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}