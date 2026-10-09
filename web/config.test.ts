// @vitest-environment node
import { expect, it } from 'vitest';
import config from './vite.config';

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
