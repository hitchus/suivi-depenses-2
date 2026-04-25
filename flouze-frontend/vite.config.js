import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // WebSocket must be listed before the generic /api catch-all
      '/api/v1/ws': {
        target: 'ws://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
