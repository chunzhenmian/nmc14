import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发代理：/api 请求转发到 Flask 后端
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true
      }
    }
  }
})
