import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PatientForm from './PatientForm'

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

function fillValidForm() {
  fireEvent.change(document.getElementById('first_name'), { target: { value: 'Regression' } })
  fireEvent.change(document.getElementById('last_name'), { target: { value: 'Tester' } })
  fireEvent.change(document.getElementById('date_of_birth'), { target: { value: '1990-05-05' } })
  fireEvent.change(document.getElementById('sex'), { target: { value: 'M' } })
  fireEvent.change(document.getElementById('contact_number'), { target: { value: '09171234567' } })
}

describe('PatientForm validation feedback', () => {
  it('renders field errors nested under "errors" returned by the register endpoint', async () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({
      errors: { first_name: ['Ensure this field has no more than 100 characters.'] },
    }, 400)))

    const { container } = render(<PatientForm onSuccess={vi.fn()} />)
    fillValidForm()
    fireEvent.submit(container.querySelector('form'))

    expect(
      await screen.findByText('Ensure this field has no more than 100 characters.')
    ).toBeInTheDocument()
  })

  it('renders top-level field errors for backward compatibility', async () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({
      last_name: ['This field may not be blank.'],
    }, 400)))

    const { container } = render(<PatientForm onSuccess={vi.fn()} />)
    fillValidForm()
    fireEvent.submit(container.querySelector('form'))

    expect(await screen.findByText('This field may not be blank.')).toBeInTheDocument()
  })

  it('shows a detail message (e.g. 403) in the error banner', async () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({
      detail: 'You do not have permission to perform this action.',
    }, 403)))

    const { container } = render(<PatientForm onSuccess={vi.fn()} />)
    fillValidForm()
    fireEvent.submit(container.querySelector('form'))

    expect(
      await screen.findByText('You do not have permission to perform this action.')
    ).toBeInTheDocument()
  })
})
