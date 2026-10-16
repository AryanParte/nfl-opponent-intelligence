// @vitest-environment node
import { expect, it } from 'vitest';
import config from './vite.config';
import browserConfig from './playwright.config';

it('restricts the development proxy to the report route and files to web/', () => {
  const server = config.server!;
  expect(server.host).toBe('127.0.0.1');
  expect(server.cors).toBe(false);
  expect(server.strictPort).toBe(true);
  const [rule] = Object.keys(server.proxy!);
  expect(new RegExp(rule).test('/api/v1/report?team=CAR')).toBe(true);
  for (const path of ['/api/refresh', '/api/v1/report/../../fetch', '/api/v1/report.csv']) {
    expect(new RegExp(rule).test(path)).toBe(false);
  }
  expect(server.fs?.allow).toHaveLength(1);
  expect(server.fs?.allow?.[0]).toMatch(/\/web\/$/);
});

it('keeps browser integration isolated, bounded and separate from unit tests', () => {
  expect(config.test?.exclude).toContain('e2e/**');
  expect(browserConfig.workers).toBe(1);
  expect(browserConfig.retries).toBe(0);
  expect(browserConfig.timeout).toBe(30_000);
  expect(browserConfig.use?.serviceWorkers).toBe('block');
  expect(browserConfig.projects?.map(project => project.name)).toEqual(['desktop', 'narrow']);
  const servers = browserConfig.webServer;
  expect(Array.isArray(servers)).toBe(true);
  if (!Array.isArray(servers)) throw new Error('Expected isolated API and viewer servers');
  expect(servers.map(server => server.url)).toEqual([
    'http://127.0.0.1:8000/openapi.json', 'http://127.0.0.1:5173',
  ]);
  for (const server of servers) {
    expect(server.reuseExistingServer).toBe(false);
    expect(server.gracefulShutdown).toEqual({ signal: 'SIGTERM', timeout: 5_000 });
  }
  expect(servers[0].command).toBe('python3 -m tests_api.browser_server');
});
