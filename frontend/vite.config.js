import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: false,
    setupFiles: './src/test/setup.js',
    include: ['src/**/*.test.{js,jsx}'],
  },
  server: {
    proxy: {
      '/accounts': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
    },
  },
})
