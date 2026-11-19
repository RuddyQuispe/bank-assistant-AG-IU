import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Tests de vitest con DOM simulado (las tools del agente tocan document)
  test: { environment: 'jsdom' },
})
