import { useAuth } from '../../context/AuthContext'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import InputField from '../ui/InputField'
import ErrorBanner from '../ui/ErrorBanner'
import Button from '../ui/Button'

const LOGIN_URL = '/accounts/login/'
const CSRF_URL = '/accounts/csrf-token/'

function getCsrfToken() {
  return document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith('csrftoken='))
    ?.split('=')[1]
}

function LoginForm() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    fetch(CSRF_URL, { credentials: 'include' }).catch(() => {})
  }, [])

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      const response = await fetch(LOGIN_URL, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(getCsrfToken() ? { 'X-CSRFToken': getCsrfToken() } : {}),
        },
        body: JSON.stringify({ username, password }),
      })

      if (response.ok) {
        const data = await response.json()
        login({ role: data.role })
        navigate(data.redirect ?? '/dashboard/')
        return
      }

      const contentType = response.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        const data = await response.json()
        setError(data.detail || data.error || data.errors || 'Login failed')
      } else {
        const text = (await response.text()).trim()
        setError(text || 'Login failed. Please try again.')
      }
    } catch (fetchError) {
      setError('Unable to reach the server. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <ErrorBanner message={error} />

      <InputField
        id="username"
        label="Username"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
        placeholder="Enter your username"
        autoComplete="username"
      />

      <InputField
        id="password"
        label="Password"
        type="password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        placeholder="Enter your password"
        autoComplete="current-password"
      />

      <Button type="submit" fullWidth disabled={isSubmitting}>
        {isSubmitting ? 'Signing in...' : 'Sign in'}
      </Button>
    </form>
  )
}

export default LoginForm
