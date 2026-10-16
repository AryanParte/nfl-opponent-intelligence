import { fileURLToPath } from 'node:url';
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1, // The API deliberately allows only one active report builder.
  retries: 0,
  forbidOnly: !!process.env.CI,
  timeout: 30_000,
  reporter: 'list',
  use: {
    browserName: 'chromium',
    baseURL: 'http://127.0.0.1:5173',
    serviceWorkers: 'block',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 900 } } },
    { name: 'narrow', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  webServer: [
    {
      name: 'Synthetic API',
      command: 'python3 -m tests_api.browser_server',
      cwd: fileURLToPath(new URL('..', import.meta.url)),
      env: { PYTHONPATH: 'src' },
      url: 'http://127.0.0.1:8000/openapi.json',
      reuseExistingServer: false, // Never test a user's real snapshot by accident.
      gracefulShutdown: { signal: 'SIGTERM', timeout: 5_000 },
      timeout: 30_000,
    },
    {
      name: 'Viewer',
      command: 'npm run dev',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: false,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 5_000 },
      timeout: 30_000,
    },
  ],
});
