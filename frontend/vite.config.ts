import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendTarget = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/auth': {
        target: backendTarget,
        changeOrigin: true,
        secure: false
      },
      '/cases': {
        target: backendTarget,
        changeOrigin: true,
        secure: false
      },
      '/trace': {
        target: backendTarget,
        changeOrigin: true,
        secure: false
      },
      '/reports': {
        target: backendTarget,
        changeOrigin: true,
        secure: false
      },
      '/health': {
        target: backendTarget,
        changeOrigin: true,
        secure: false
      }
    }
  }
})
