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
})