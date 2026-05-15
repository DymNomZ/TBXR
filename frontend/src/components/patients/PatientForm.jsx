import { useState } from 'react'
import InputField from '../ui/InputField'
import SelectField from '../ui/SelectField'
import ErrorBanner from '../ui/ErrorBanner'
import Button from '../ui/Button'

const CREATE_URL = '/api/patients/register/'

const SEX_OPTIONS = [
  { value: 'M', label: 'Male' },
  { value: 'F', label: 'Female' },
  { value: 'O', label: 'Other' },
]

function getCsrfToken() {
  return document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith('csrftoken='))
    ?.split('=')[1]
}

function PatientForm({ onSuccess }) {
  const [fields, setFields] = useState({
    first_name: '',
    last_name: '',
    date_of_birth: '',
    sex: '',
    contact_number: '',
  })
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleChange = (field) => (event) => {
    setFields((prev) => ({ ...prev, [field]: event.target.value }))
    setFieldErrors((prev) => ({ ...prev, [field]: '' }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setFieldErrors({})
    setIsSubmitting(true)

    try {
      const response = await fetch(CREATE_URL, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(getCsrfToken() ? { 'X-CSRFToken': getCsrfToken() } : {}),
        },
        body: JSON.stringify(fields),
      })

      if (response.ok) {
        onSuccess?.()
        return
      }

      const data = await response.json()

      // assumes Django returns { "first_name": ["This field is required."], ... }. 
      // It grabs the first message per field.
      if (data && typeof data === 'object' && !data.detail && !data.error) {
        const normalized = {}
        for (const [key, val] of Object.entries(data)) {
          normalized[key] = Array.isArray(val) ? val[0] : val
        }
        setFieldErrors(normalized)
      } else {
        setError(data.detail || data.error || 'Failed to create patient.')
      }
    } catch {
      setError('Unable to reach the server. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <ErrorBanner message={error} />

      <div className="grid grid-cols-2 gap-4">
        <InputField
          id="first_name"
          label="First Name"
          value={fields.first_name}
          onChange={handleChange('first_name')}
          placeholder="Juan"
          autoComplete="given-name"
          error={fieldErrors.first_name}
        />
        <InputField
          id="last_name"
          label="Last Name"
          value={fields.last_name}
          onChange={handleChange('last_name')}
          placeholder="Dela Cruz"
          autoComplete="family-name"
          error={fieldErrors.last_name}
        />
      </div>

      <InputField
        id="date_of_birth"
        label="Date of Birth"
        type="date"
        value={fields.date_of_birth}
        onChange={handleChange('date_of_birth')}
        autoComplete="bday"
        error={fieldErrors.date_of_birth}
      />

      <SelectField
        id="sex"
        label="Sex"
        value={fields.sex}
        onChange={handleChange('sex')}
        options={SEX_OPTIONS}
        error={fieldErrors.sex}
      />

      <InputField
        id="contact_number"
        label="Contact Number"
        type="tel"
        value={fields.contact_number}
        onChange={handleChange('contact_number')}
        placeholder="+63 912 345 6789"
        autoComplete="tel"
        error={fieldErrors.contact_number}
      />

      <Button type="submit" fullWidth disabled={isSubmitting}>
        {isSubmitting ? 'Saving...' : 'Create Patient'}
      </Button>
    </form>
  )
}

export default PatientForm