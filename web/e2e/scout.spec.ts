import { execFileSync } from 'node:child_process';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { test as base, expect, type Page, type TestInfo } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

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

async function scanAccessibility(page: Page, info: TestInfo, state: string) {
  const result = await new AxeBuilder({ page }).analyze();
  const path = info.outputPath(`axe-${state}.json`);
  await writeFile(path, JSON.stringify(result, null, 2));
  await info.attach(`axe-${state}`, { path, contentType: 'application/json' });
  expect(result.violations, `${state}: automatic checks are not a complete accessibility audit`).toEqual([]);
}

test('Decision client reaches the real local API through the bounded proxy without changing Scout', async ({ page }) => {
  await openViewer(page);
  const result = await page.evaluate(async () => {
    const modulePath = '/src/decision.ts';
    const { fetchDecisionDocument }: typeof import('../src/decision') = await import(/* @vite-ignore */ modulePath);
    return fetchDecisionDocument({ team: 'CAR', season: 2024, season_type: 'REG', before_week: 3,
      down: 1, distance_min: 10, distance_max: 10, yardline_max: 20, score_min: -7, score_max: 0,
      period: 'Q4', clock_max: 120, compare_league: true, bootstrap_repetitions: 200 }, new AbortController().signal);
  });
  expect(JSON.parse(result.json)).toEqual(result.decision);
  expect(result.decision.population).toEqual({ plays: 3, games: 1 });
  expect(result.decision.candidates[0]).toMatchObject({ candidate: 'run', plays: 2, frequency: 2 / 3,
    epa_observations: 1, missing_epa: 1, epa_per_play: -.4, success_rate: 0 });
  expect(result.decision.candidates[1]).toMatchObject({ candidate: 'pass', plays: 1, epa_per_play: .8, success_rate: 1 });
  expect(result.decision.league_comparison!.candidates[1].epa_per_play).toBe(3);
  expect(result.decision.comparison.preferred_candidate).toBeNull();
  expect(result.decision.uncertainty!.candidates[0].selected.frequency.status).toBe('insufficient_games');
  expect(result.decision.source.label).toContain('SYNTHETIC browser integration fixture');
  await expect(page.getByText('No report has been requested for these controls.', { exact: false })).toBeVisible();
});

async function openDecision(page: Page) {
  await page.getByRole('tab', { name: 'Decision Lab' }).click();
  const panel = page.getByRole('tabpanel', { name: 'Decision Lab' });
  await panel.getByLabel('Before week', { exact: true }).fill('3');
  return panel;
}

test('Decision Lab renders real API evidence and preserves both modes and the Scout download', async ({ page }, info) => {
  await openViewer(page);
  await build(page);
  const download = page.getByRole('link', { name: 'Download report JSON' });
  await expect(download).toBeVisible();
  const href = await download.getAttribute('href');
  const decision = await openDecision(page);
  const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/decision');
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  expect((await response).status()).toBe(200);
  await expect(decision.getByRole('status')).toHaveText('Decision evidence loaded: CAR, 15 eligible plays. No preferred call.');
  const [run, pass] = await decision.getByRole('row').all().then(rows => rows.slice(1));
  // Invented browser dataset: four runs (-.4, missing, missing, -.6), eleven passes (EPA sum 3.5).
  await expect(run).toContainText('4 / 15 plays');
  await expect(run).toContainText('26.7%');
  await expect(run).toContainText('-0.500');
  await expect(run).toContainText('2 / 2');
  await expect(pass).toContainText('11 / 15 plays');
  await expect(pass).toContainText('73.3%');
  await expect(pass).toContainText('0.318');
  await expect(pass).toContainText('81.8%');
  await expect(decision.getByRole('heading', { name: 'No preferred call' })).toBeVisible();
  await expect(decision.getByText(/SYNTHETIC browser integration fixture/)).toBeVisible();
  await decision.getByText('Inspect source fingerprints').click();
  await scanAccessibility(page, info, 'decision-loaded');
  await decision.getByRole('heading', { level: 1 }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath('decision-query.png') });
  await decision.getByRole('heading', { name: 'No preferred call' }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath('decision-evidence.png') });
  await page.getByRole('tab', { name: 'Scout' }).click();
  await expect(page.getByRole('link', { name: 'Download report JSON' })).toHaveAttribute('href', href!);
  await expect(page.getByRole('status')).toHaveText('Report loaded: CAR, offense, 15 eligible plays.');
  await page.getByRole('tab', { name: 'Decision Lab' }).click();
  await expect(decision.getByRole('table')).toBeVisible();
  await expect(decision.locator('details')).toHaveAttribute('open', '');
  expect(await page.locator('[id]').evaluateAll(nodes => new Set(nodes.map(node => node.id)).size === nodes.length)).toBe(true);
});

test('Decision Lab invalid, unavailable and empty states remain accessible without stale measurements', async ({ page }, info) => {
  await openViewer(page);
  const decision = await openDecision(page);
  await scanAccessibility(page, info, 'decision-idle');
  const lower = decision.getByLabel('Minimum yards to go', { exact: true });
  await lower.fill('11');
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  await expect(lower).toBeFocused();
  await expect(lower).toHaveAccessibleDescription(/Minimum distance must not exceed maximum distance/);
  await scanAccessibility(page, info, 'decision-invalid');
  await lower.fill('10');
  await page.route('**/api/v1/decision?*', route => route.fulfill({ status: 503, contentType: 'application/json',
    body: JSON.stringify({ error: { code: 'report_busy', message: 'PRIVATE /snapshot/path' } }) }));
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  await expect(decision.getByRole('alert')).toContainText('Another report is being built');
  await expect(decision).not.toContainText('PRIVATE');
  await expect(decision.getByRole('table')).toHaveCount(0);
  await scanAccessibility(page, info, 'decision-error');
  await page.unroute('**/api/v1/decision?*');
  await decision.getByLabel('Before week', { exact: true }).fill('1');
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  await expect(decision.getByRole('heading', { name: 'No eligible plays match this situation.' })).toBeVisible();
  await expect(decision.getByRole('cell', { name: /^Unavailable/ })).toHaveCount(6);
  await expect(decision.getByRole('alert')).toHaveCount(0);
  await scanAccessibility(page, info, 'decision-empty');
});

test('Decision keyboard navigation, cancelled mode switches and contained table reflow at 320 pixels', async ({ page }, info) => {
  await page.goto('/');
  const scout = page.getByRole('tab', { name: 'Scout' }), tab = page.getByRole('tab', { name: 'Decision Lab' });
  await page.keyboard.press('Tab'); // Skip link.
  await page.keyboard.press('Tab'); await expect(scout).toBeFocused();
  await page.keyboard.press('ArrowRight'); await expect(tab).toBeFocused();
  await expect(scout).toHaveAttribute('aria-selected', 'true');
  await page.keyboard.press('Enter');
  const decision = page.getByRole('tabpanel', { name: 'Decision Lab' });
  await page.keyboard.press('Tab'); await expect(decision).toBeFocused();
  for (const name of ['team', 'season', 'before_week', 'season_type', 'down', 'distance_min', 'distance_max']) {
    await page.keyboard.press('Tab');
    const input = decision.locator(`[name="${name}"]`);
    await expect(input).toBeFocused();
    if (name === 'before_week') { await page.keyboard.press('ControlOrMeta+A'); await page.keyboard.insertText('3'); }
  }
  await page.keyboard.press('Tab');
  await expect(decision.getByRole('button', { name: 'Compare Run and Pass' })).toBeFocused();
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let arrived!: () => void;
  const started = new Promise<void>(resolve => { arrived = resolve; });
  await page.route('**/api/v1/decision?*', async route => { arrived(); await held; await route.continue(); });
  await page.keyboard.press('Enter'); await started;
  await expect(decision.getByRole('status')).toContainText('Loading decision evidence');
  await scout.click(); release();
  await tab.click();
  await expect(decision.getByRole('status')).toBeEmpty();
  await expect(decision.getByRole('table')).toHaveCount(0);
  await page.unroute('**/api/v1/decision?*');
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  await expect(decision.getByRole('heading', { name: 'Observed call evidence' })).toBeVisible();
  await page.setViewportSize({ width: 320, height: 900 });
  const region = decision.getByRole('region', { name: /Run and Pass evidence/ });
  await region.focus();
  await expect(region).toBeFocused();
  expect(await region.evaluate(element => element.scrollWidth > element.clientWidth)).toBe(true);
  await page.keyboard.press('ArrowRight');
  await expect.poll(() => region.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  await page.keyboard.press('Tab'); await expect(region).not.toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await scanAccessibility(page, info, 'decision-320');
  await region.focus(); await page.screenshot({ path: info.outputPath('decision-table-320.png') });
});

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

test('editing during a delayed real response cannot publish a stale report or download', async ({ page }, info) => {
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
    await scanAccessibility(page, info, 'loading');
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

test('accessibility scans cover idle, invalid, API error, empty and expanded evidence states', async ({ page }, info) => {
  test.setTimeout(60_000);
  await openViewer(page);
  await scanAccessibility(page, info, 'idle');
  await page.getByLabel('Maximum seconds remaining', { exact: true }).fill('120');
  await page.getByRole('button', { name: 'Build report' }).click();
  await expect(page.getByRole('alert')).toContainText('Choose an explicit period');
  await scanAccessibility(page, info, 'invalid');
  await page.getByLabel('Maximum seconds remaining', { exact: true }).fill('');
  await page.getByLabel('Season', { exact: true }).fill('2023');
  expect((await build(page)).status()).toBe(422);
  await expect(page.getByRole('alert')).toBeVisible();
  await scanAccessibility(page, info, 'api-error');
  await page.getByLabel('Season', { exact: true }).fill('2024');
  await page.getByLabel('Before week', { exact: true }).fill('1');
  await build(page);
  await expect(page.getByRole('heading', { name: 'No eligible plays match this query.' })).toBeVisible();
  await scanAccessibility(page, info, 'empty');
  await page.getByLabel('Before week', { exact: true }).fill('3');
  await page.getByLabel('Maximum yards to goal', { exact: true }).fill('20');
  await page.getByLabel('Minimum score difference', { exact: true }).fill('-7');
  await page.getByLabel('Maximum score difference', { exact: true }).fill('0');
  await page.getByRole('combobox', { name: 'Period', exact: true }).selectOption('Q4');
  await page.getByLabel('Maximum seconds remaining', { exact: true }).fill('120');
  await page.getByLabel('Compare with other teams in the same role').check();
  await page.getByLabel('Bootstrap repetitions', { exact: true }).fill('200');
  await build(page);
  await expect(page.getByRole('status')).toContainText('3 eligible plays');
  for (const summary of await page.locator('article summary').all()) {
    await summary.focus();
    await summary.press('Enter');
    await expect(summary.locator('..')).toHaveAttribute('open', '');
  }
  await scanAccessibility(page, info, 'expanded-evidence');
});

test('invalid submission focuses its field, describes the error and permits keyboard correction', async ({ page }) => {
  await openViewer(page);
  const clock = page.getByLabel('Maximum seconds remaining', { exact: true });
  const period = page.getByRole('combobox', { name: 'Period', exact: true });
  await clock.fill('120');
  await clock.press('Enter');
  await expect(period).toBeFocused();
  await expect(period).toHaveAttribute('aria-invalid', 'true');
  await expect(period).toHaveAccessibleDescription(/Choose an explicit period/);
  await expect(clock).not.toHaveAttribute('aria-invalid', 'true'); // The seconds themselves are valid.
  await page.keyboard.press('q'); // Native select type-ahead, then commit with Tab.
  await page.keyboard.press('Tab');
  await expect(period).not.toHaveAttribute('aria-invalid', 'true');
  await expect(page.getByRole('alert')).toHaveCount(0);
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status')).toContainText('Report loaded:');
});

test('full keyboard order, expanded tables and 320 CSS-pixel reflow', async ({ page }, info) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to report query' })).toBeFocused();
  await page.keyboard.press('Enter');
  for (const name of ['team', 'season', 'before_week', 'side', 'season_type', 'yardline_min', 'yardline_max',
    'score_min', 'score_max', 'period', 'clock_min', 'clock_max', 'compare_league', 'bootstrap_repetitions', 'bootstrap_seed']) {
    await page.keyboard.press('Tab');
    await expect(page.locator(`[name="${name}"]`)).toBeFocused();
    if (name === 'before_week') {
      await page.keyboard.press('ControlOrMeta+A');
      await page.keyboard.insertText('3');
    }
    if (name === 'compare_league') await page.keyboard.press('Space');
    if (name === 'bootstrap_repetitions') await page.keyboard.insertText('200');
  }
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Build report' })).toBeFocused();
  // Browser-computed styling: axe does not check component-border contrast.
  const colors = await page.getByLabel('Team code', { exact: true }).evaluate(element => {
    const style = getComputedStyle(element);
    return [style.borderTopColor, style.backgroundColor];
  });
  function luminance(color: string) {
    const rgb = color.match(/\d+/g)!.map(value => Number(value) / 255)
      .map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722;
  }
  const [border, background] = colors.map(luminance);
  expect((Math.max(border, background) + 0.05) / (Math.min(border, background) + 0.05)).toBeGreaterThanOrEqual(3);
  await page.keyboard.press('Enter');
  await expect(page.getByRole('status')).toHaveText('Report loaded: CAR, offense, 15 eligible plays.');
  await page.setViewportSize({ width: 320, height: 900 });
  for (const summary of await page.locator('article summary').all()) {
    await summary.focus();
    await summary.press('Enter');
    await expect(summary.locator('..')).toHaveAttribute('open', '');
  }
  const tables = page.locator('article .table-scroll');
  expect(await tables.count()).toBeGreaterThan(3); // Splits, comparisons and uncertainty.
  for (const region of await tables.all()) {
    await expect(region).toHaveAccessibleName(/.+/);
    const table = region.getByRole('table');
    await expect(table).toHaveAccessibleName(/.+/);
    expect(await table.getByRole('columnheader').count()).toBeGreaterThan(0);
    expect(await table.getByRole('rowheader').count()).toBeGreaterThan(0);
    await region.focus();
    await expect(region).toBeFocused();
    const focus = await region.evaluate(element => {
      const style = getComputedStyle(element);
      return { width: style.outlineWidth, style: style.outlineStyle, offset: style.outlineOffset };
    });
    expect(focus).toEqual({ width: '3px', style: 'solid', offset: '4px' });
    if (await region.evaluate(element => element.scrollWidth > element.clientWidth)) {
      await region.press('ArrowRight');
      await expect.poll(() => region.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
    }
    await page.keyboard.press('Tab');
    await expect(region).not.toBeFocused(); // No keyboard trap.
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await scanAccessibility(page, info, 'expanded-320');
  // Inspect focused controls and tables visually; these are not screen-reader tests.
  await page.getByLabel('Team code', { exact: true }).focus();
  await page.screenshot({ path: info.outputPath('query-320.png') });
  await tables.first().focus();
  await page.screenshot({ path: info.outputPath('table-320.png') });
});
