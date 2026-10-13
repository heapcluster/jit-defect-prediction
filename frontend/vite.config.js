import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 后端地址走本地代理，不要硬编码进页面
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
