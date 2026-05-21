import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 开发期 Vite 走 5173；/api 反向代理到 FastAPI 8000，避免跨域
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
