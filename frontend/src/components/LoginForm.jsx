import { useState } from 'react'
import InputField from './InputField'
import ErrorBanner from './ErrorBanner'

const LOGIN_URL = '/accounts/login/'

function getCsrfToken() {
  return document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith('csrftoken='))
    ?.split('=')[1]
}

function LoginForm() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

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

      if (response.redirected) {
        window.location.href = response.url
        return
      }

      if (response.ok) {
        const location = response.headers.get('Location')
        if (location) {
          window.location.href = location
          return
        }
        window.location.reload()
        return
      }

      const data = await response.json()
      setError(data.detail || data.error || data.errors || 'Login failed')
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

      <button
        className="flex w-full items-center justify-center rounded-3xl bg-slate-indigo px-4 py-3 text-sm font-semibold text-white opacity-50 transition duration-200 hover:bg-slate-indigo hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-80"
        type="submit"
        disabled={isSubmitting}
      >
        {isSubmitting ? 'Signing in...' : 'Sign in'}
      </button>
    </form>
  )
}

export default LoginForm
