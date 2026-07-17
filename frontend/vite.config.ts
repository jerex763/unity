import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'
import { defineConfig } from 'vitest/config'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
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
        '/api': {
          target: env.VITE_DEV_API_PROXY ?? 'http://127.0.0.1:8000',
          changeOrigin: false,
        },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      css: true,
    },
  }
})
