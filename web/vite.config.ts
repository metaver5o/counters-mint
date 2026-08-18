import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  optimizeDeps: {
    include: ['@sats-connect/core'],
  },
  build: {
    outDir: '../counters_proto/server/static',
    emptyOutDir: false,
  },
})
