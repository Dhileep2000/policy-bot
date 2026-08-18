import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, './backend', '')
  const apiBaseUrl = env.VITE_API_BASE_URL || process.env.VITE_API_BASE_URL || '/api'

  return {
    envDir: './backend',
    plugins: [react(), tailwindcss()],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: env.VITE_BACKEND_URL || 'http://127.0.0.1:8000',
          changeOrigin: true,
          secure: false,
        }
      }
    },
    define: {
      __API_BASE_URL__: JSON.stringify(apiBaseUrl),
      __APP_TITLE__: JSON.stringify(env.VITE_APP_TITLE || process.env.VITE_APP_TITLE || 'Lexis AI Policy Intelligence'),
      __DEBUG_MODE__: env.VITE_DEBUG_MODE === 'true' || process.env.VITE_DEBUG_MODE === 'true',
    }
  }
})
