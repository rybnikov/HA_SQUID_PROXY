import { fileURLToPath } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
    'process.env': '{}'
  },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    outDir: 'dist/panel',
    emptyOutDir: false,
    target: 'es2022',
    lib: {
      entry: fileURLToPath(new URL('./src/ha-panel.tsx', import.meta.url)),
      formats: ['es'],
      fileName: () => 'squid-proxy-panel.js'
    }
  }
});
