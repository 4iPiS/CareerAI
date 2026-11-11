import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/static-react/',
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:7777',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/app-v2-[hash].js',
        chunkFileNames: 'assets/chunk-v2-[hash].js',
        assetFileNames: 'assets/assets-v2-[hash][extname]',
      },
    },
  },
})
