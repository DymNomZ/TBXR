import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

const ROLE_DASHBOARD = {
  RADIOLOGIC_TECH: '/dashboard/technologist',
  RADIOLOGIST:     '/dashboard/radiologist',
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

  const logout = async () => {
    try {
      // Read CSRF token from cookie
      const csrfToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1]

      await fetch('/accounts/logout/', {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRFToken': csrfToken ?? '' },
      })
    } catch (e) {
      // proceed with local logout even if request fails
    }

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