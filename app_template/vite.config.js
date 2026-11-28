import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  base: '/app/',
  build: { outDir: 'dist' },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/promo': 'http://localhost:8000',
    },
  },
})
