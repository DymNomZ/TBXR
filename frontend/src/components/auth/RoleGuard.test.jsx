import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from '../../context/AuthContext'
import RoleGuard from './RoleGuard'

function renderGuard({ role = null, path = '/radiologist-only' } = {}) {
  if (role) {
    localStorage.setItem('user', JSON.stringify({ role }))
  } else {
    localStorage.removeItem('user')
  }

  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route
            path="/radiologist-only"
            element={
              <RoleGuard allowedRoles={['RADIOLOGIST']}>
                <div>Radiologist View</div>
              </RoleGuard>
            }
          />
          <Route path="/dashboard/patient" element={<div>Patient Dashboard</div>} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('RoleGuard', () => {
  it('redirects unauthenticated users to login', () => {
    renderGuard({ role: null })
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })

  it('redirects patient users to their own dashboard when hitting a disallowed route', () => {
    renderGuard({ role: 'PATIENT' })
    expect(screen.getByText('Patient Dashboard')).toBeInTheDocument()
  })

  it('allows users with matching role', () => {
    renderGuard({ role: 'RADIOLOGIST' })
    expect(screen.getByText('Radiologist View')).toBeInTheDocument()
  })
})