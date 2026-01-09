import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@ui-kit': fileURLToPath(new URL('../../packages/ui-kit/src', import.meta.url)),
      // reserved: '@schemas' later when we split schemas into packages/schemas
    },
  },
  server: {
    fs: {
      allow: [
        fileURLToPath(new URL('.', import.meta.url)),
        fileURLToPath(new URL('../../packages', import.meta.url)),
      ],
    },
  },
})
