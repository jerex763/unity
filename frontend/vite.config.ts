import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['unity-icon.svg'],
      manifest: {
        name: 'Unity Church Community',
        short_name: 'Unity',
        description: 'Church membership and discipleship management',
        theme_color: '#2f6b4f',
        background_color: '#fbf8f1',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: '/unity-icon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any maskable',
          },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})
