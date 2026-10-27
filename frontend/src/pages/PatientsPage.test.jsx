import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import PatientsPage from './PatientsPage'

function renderForRole(role) {
  localStorage.setItem('user', JSON.stringify({ role }))
  return render(
    <MemoryRouter>
      <AuthProvider>
        <PatientsPage />
      </AuthProvider>
    </MemoryRouter>
  )
}

describe('PatientsPage registration access', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    })))
  })

  it('shows the New Patient action for technologists', () => {
    renderForRole('RADIOLOGIC_TECH')
    expect(screen.getByRole('button', { name: /New Patient/i })).toBeInTheDocument()
  })

  it('hides the New Patient action for radiologists while keeping the list', () => {
    renderForRole('RADIOLOGIST')
    expect(screen.queryByRole('button', { name: /New Patient/i })).not.toBeInTheDocument()
    expect(screen.getByText('Patients List')).toBeInTheDocument()
  })

  it('hides the New Patient action for physicians while keeping the list', () => {
    renderForRole('PHYSICIAN')
    expect(screen.queryByRole('button', { name: /New Patient/i })).not.toBeInTheDocument()
    expect(screen.getByText('Patients List')).toBeInTheDocument()
  })

  it('hides the New Patient action for patients while keeping the list', () => {
    renderForRole('PATIENT')
    expect(screen.queryByRole('button', { name: /New Patient/i })).not.toBeInTheDocument()
    expect(screen.getByText('Patients List')).toBeInTheDocument()
  })
})
