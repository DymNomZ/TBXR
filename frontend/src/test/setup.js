import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// vitest runs with `globals: false`, so RTL's auto-cleanup (which relies on a
// global afterEach) never fires. Reset everything manually between tests.
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.useRealTimers()
  localStorage.clear()

  // Clear cookies set during tests (e.g., csrftoken) to avoid cross-test leakage.
  document.cookie.split(';').forEach((cookie) => {
    const eqPos = cookie.indexOf('=')
    const name = (eqPos > -1 ? cookie.slice(0, eqPos) : cookie).trim()
    if (name) {
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`
    }
  })
})