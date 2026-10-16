import { execFileSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { test as base, expect, type Page } from '@playwright/test';

const root = fileURLToPath(new URL('../..', import.meta.url));
const origin = 'http://127.0.0.1:5173';
const test = base.extend<{ networkGuard: void }>({
  networkGuard: [async ({ context, page }, use) => {
    const unexpected: string[] = [];
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    await context.route('**/*', async route => {
      if (new URL(route.request().url()).origin !== origin) {
        unexpected.push(route.request().url());
        await route.abort();
      } else await route.continue();
    });
    await context.routeWebSocket('**/*', route => {
      if (new URL(route.url()).origin !== origin.replace('http:', 'ws:')) {
        unexpected.push(route.url());
        route.close();
      } else route.connectToServer(); // Vite's local development socket only.
    });
    await use();
    expect(unexpected, 'Browser attempted an external request').toEqual([]);
    expect(errors, 'Uncaught browser errors').toEqual([]);
  }, { auto: true }],
});

async function openViewer(page: Page) {
  await page.goto('/');
  await expect(page.getByText('No report has been requested for these controls.', { exact: false })).toBeVisible();
  await page.getByLabel('Before week', { exact: true }).fill('3');
}

async function build(page: Page) {
  const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/report');
  await page.getByRole('button', { name: 'Build report' }).click();
  return response;
}

test('real filtered API report, both roles, native JSON download and offline brief replay', async ({ page }, info) => {
  let requests = 0;
  page.on('request', request => { if (new URL(request.url()).pathname === '/api/v1/report') requests++; });
  await openViewer(page);
  expect(requests).toBe(0);
  await page.getByLabel('Maximum yards to goal', { exact: true }).fill('20');
  await page.getByLabel('Minimum score difference', { exact: true }).fill('-7');
  await page.getByLabel('Maximum score difference', { exact: true }).fill('0');
  await page.getByRole('combobox', { name: 'Period', exact: true }).selectOption('Q4');
  await page.getByLabel('Maximum seconds remaining', { exact: true }).fill('120');
  await page.getByLabel('Compare with other teams in the same role').check();
  await page.getByLabel('Bootstrap repetitions', { exact: true }).fill('200');

  for (const [team, side] of [['CAR', 'offense'], ['ATL', 'defense']]) {
    await page.getByLabel('Team code', { exact: true }).fill(team);
    await page.getByRole('combobox', { name: 'Role', exact: true }).selectOption(side);
    const response = await build(page);
    expect(response.status()).toBe(200);
    const bytes = await response.body();
    const report = JSON.parse(bytes.toString('utf8'));
    // Hand-checkable synthetic observations: 0.8, -0.4, missing, in one game.
    expect(report.overall).toMatchObject({ plays: 3, games: 1, dropbacks: 1, designed_runs: 2,
      epa_observations: 2, missing_epa: 1, epa_per_play: 0.2, success_rate: 0.5 });
    expect(report.league_comparison.overall).toMatchObject({ plays: 1, epa_per_play: 3 });
    await expect(page.getByRole('status')).toHaveText(`Report loaded: ${team}, ${side}, 3 eligible plays.`);
    await expect(page.getByText(/SYNTHETIC browser integration fixture/)).toBeVisible();
    const metrics = page.locator('.metric-grid');
    await expect(metrics).toContainText('0.200');
    await expect(metrics).toContainText('2 observed EPA · 1 missing');
    await expect(metrics).toContainText('50.0%');
    await expect(page.getByText('Withheld · fewer than 5 contributing games', { exact: true }).first()).toBeVisible();

    const link = page.getByRole('link', { name: 'Download report JSON' });
    await link.focus();
    await expect(link).toBeFocused();
    const downloading = page.waitForEvent('download');
    await link.press('Enter');
    const download = await downloading;
    expect(download.suggestedFilename()).toBe(`nfl-oi-${team}-2024-REG-${side}-before-week-3.report.json`);
    const saved = info.outputPath(`${side}.report.json`);
    await download.saveAs(saved);
    expect(await readFile(saved)).toEqual(bytes);
    const brief = execFileSync('python3', ['-m', 'opponent_intelligence.brief', '--report', saved],
      { cwd: root, env: { ...process.env, PYTHONPATH: 'src' }, encoding: 'utf8', timeout: 10_000 });
    expect(brief).toContain('SYNTHETIC browser integration fixture');
    expect(brief).toContain(team);
    expect(brief).toContain('0.200');
    expect(brief).toContain(report.source.sha256);
    expect(requests).toBe(side === 'offense' ? 1 : 2); // Download/replay never refetches.
    await page.getByLabel('Before week', { exact: true }).fill('2');
    await expect(link).toHaveCount(0);
    await expect(page.getByRole('article')).toHaveCount(0);
    await page.getByLabel('Before week', { exact: true }).fill('3');
  }
});

test('invalid controls make no request; real API error and empty cohort recover honestly', async ({ page }) => {
  let requests = 0;
  page.on('request', request => { if (new URL(request.url()).pathname === '/api/v1/report') requests++; });
  await openViewer(page);
  await page.getByLabel('Maximum seconds remaining', { exact: true }).fill('120');
  await page.getByRole('button', { name: 'Build report' }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  expect(requests).toBe(0); // Clock without a period is invalid, not an unrestricted query.
  await page.getByLabel('Maximum seconds remaining', { exact: true }).fill('');
  await page.getByLabel('Season', { exact: true }).fill('2023');
  expect((await build(page)).status()).toBe(422);
  await expect(page.getByRole('alert')).toContainText(/season/i);
  await expect(page.getByRole('link', { name: 'Download report JSON' })).toHaveCount(0);
  await page.getByLabel('Season', { exact: true }).fill('2024');
  await page.getByLabel('Before week', { exact: true }).fill('1');
  expect((await build(page)).status()).toBe(200);
  await expect(page.getByRole('heading', { name: 'No eligible plays match this query.' })).toBeVisible();
  await expect(page.locator('.metric-grid')).toContainText('Unavailable');
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect(requests).toBe(2);
});

test('editing during a delayed real response cannot publish a stale report or download', async ({ page }) => {
  let release!: () => void;
  let received!: () => void;
  const hold = new Promise<void>(resolve => { release = resolve; });
  const captured = new Promise<void>(resolve => { received = resolve; });
  await page.route('**/api/v1/report?*', async route => {
    const response = await route.fetch(); // Actual server response; only delivery is delayed.
    received();
    await hold;
    await route.fulfill({ response });
  });
  await openViewer(page);
  await page.getByRole('button', { name: 'Build report' }).click();
  try {
    await captured;
    await expect(page.getByRole('status')).toContainText('Building report');
    await expect(page.getByRole('button', { name: 'Building' })).toBeDisabled();
    await page.getByLabel('Team code', { exact: true }).fill('ATL');
  } finally { release(); }
  await page.unrouteAll({ behavior: 'wait' });
  await expect(page.getByRole('article')).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Download report JSON' })).toHaveCount(0);
  expect((await build(page)).status()).toBe(200);
  await expect(page.getByRole('status')).toHaveText('Report loaded: ATL, offense, 5 eligible plays.');
});

test('keyboard query, focusable table and viewport containment', async ({ page }, info) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to report query' })).toBeFocused();
  await page.keyboard.press('Enter');
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Team code', { exact: true })).toBeFocused();
  await page.keyboard.press('Tab'); // Season
  await page.keyboard.press('Tab'); // Cutoff
  const cutoff = page.getByLabel('Before week', { exact: true });
  await expect(cutoff).toBeFocused();
  await cutoff.fill('3');
  await page.keyboard.press('Enter'); // Native form submission from the focused input.
  await expect(page.getByRole('status')).toHaveText('Report loaded: CAR, offense, 15 eligible plays.');
  const table = page.getByRole('region', { name: 'Down and distance table, scroll horizontally on small screens' });
  await table.focus();
  await expect(table).toBeFocused();
  if (info.project.name === 'narrow') {
    await table.press('ArrowRight');
    await expect.poll(() => table.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
