import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  server: {
    host: '127.0.0.1', port: 5173, strictPort: true, cors: false,
    // Do not expose the surrounding repository or its raw snapshots as assets.
    fs: { strict: true, allow: [fileURLToPath(new URL('.', import.meta.url))] },
    proxy: {
      '^/api/v1/report(?:\\?|$)': {
        target: 'http://127.0.0.1:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: { environment: 'jsdom', setupFiles: ['./src/test-setup.ts'] },
});
