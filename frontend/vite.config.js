import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiBaseUrl = env.VITE_API_BASE_URL || '/api'

  return {
    plugins: [vue()],
    server: {
      host: '0.0.0.0',
      port: 3598,
      proxy: {
        [apiBaseUrl]: {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path
        }
      }
    }
  }
})
