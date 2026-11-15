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
  await expect(decision.getByRole('table', { name: 'Observed Run and Pass evidence for the selected offense' })).toBeVisible();
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
  await expect(decision.getByRole('table', { name: 'Observed Run and Pass evidence for the selected offense' }).getByRole('cell', { name: /^Unavailable/ })).toHaveCount(6);
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
  for (const name of ['team', 'season', 'before_week', 'season_type', 'down', 'distance_min', 'distance_max', 'yardline_min', 'yardline_max', 'score_min', 'score_max', 'period', 'clock_min', 'clock_max', 'compare_league', 'bootstrap_repetitions', 'bootstrap_seed']) {
    await page.keyboard.press('Tab');
    const input = decision.locator(`[name="${name}"]`);
    await expect(input).toBeFocused();
    if (name === 'before_week') { await page.keyboard.press('ControlOrMeta+A'); await page.keyboard.insertText('3'); }
  }
  await page.keyboard.press('Tab');
  await expect(decision.getByRole('radio', { name: 'Run', exact: true })).toBeFocused();
  await page.keyboard.press('Tab'); // No selection yet; Clear choice is disabled.
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

test('Decision field bounds retain exact cohorts, show ordered accounting and recover without fallback', async ({ page }, info) => {
  await openViewer(page);
  const decision = await openDecision(page);
  const upper = decision.getByLabel('Maximum yards to goal', { exact: true });
  await upper.fill('1e'); await upper.press('Enter');
  await expect(upper).toBeFocused();
  await expect(upper).toHaveValue('1e');
  await expect(upper).toHaveAccessibleDescription(/Field-position bounds must be decimals/);
  await scanAccessibility(page, info, 'decision-field-invalid');
  await upper.fill('20.5');
  const pending = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/decision');
  await upper.press('Enter');
  const response = await pending;
  expect(response.status()).toBe(200);
  expect(new URL(response.url()).searchParams.get('yardline_max')).toBe('20.5');
  const evidence = await response.json();
  // Independent invented browser rows: 15 CAR plays -> 2 missing positions + 1 at 80 + 12 retained.
  expect(evidence.population).toEqual({ plays: 12, games: 1 });
  expect(evidence.candidates[0]).toMatchObject({ plays: 3, frequency: .25, epa_observations: 2, missing_epa: 1, epa_per_play: -.5 });
  await expect(decision.getByRole('status')).toHaveText('Decision evidence loaded: CAR, 12 eligible plays. No preferred call.');
  const accounting = decision.getByRole('region', { name: 'Decision filter accounting, scroll horizontally on small screens' });
  expect(await accounting.getByRole('rowheader').allTextContents()).toEqual(['Field position', 'Down', 'Distance']);
  expect(await accounting.getByRole('row', { name: /^Field position/ }).getByRole('cell').allTextContents()).toEqual(['15', '2', '1', '12']);
  await expect(decision.getByText('0–20.5 yards to the offense’s opponent’s goal line')).toBeVisible();
  await scanAccessibility(page, info, 'decision-field-loaded');
  await page.setViewportSize({ width: 320, height: 900 });
  await accounting.focus(); await expect(accounting).toBeFocused();
  await accounting.press('ArrowRight');
  await expect.poll(() => accounting.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath('decision-field-accounting-320.png') });
  await scanAccessibility(page, info, 'decision-field-320');
  await page.getByRole('tab', { name: 'Scout' }).click();
  await expect(page.getByRole('textbox', { name: 'Maximum yards to goal' })).toHaveValue('');
  await page.getByRole('tab', { name: 'Decision Lab' }).click();
  await expect(upper).toHaveValue('20.5');
  await expect(decision.getByRole('status')).toContainText('12 eligible plays');
  await upper.fill('0');
  await expect(decision.getByRole('article')).toHaveCount(0);
  await upper.press('Enter');
  await expect(decision.getByRole('heading', { name: 'No eligible plays match this situation.' })).toBeVisible();
  await expect(decision.getByText('0–0 yards to the offense’s opponent’s goal line')).toBeVisible();
  await upper.fill('');
  const unrestricted = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/decision');
  await upper.press('Enter');
  expect(new URL((await unrestricted).url()).searchParams.has('yardline_max')).toBe(false);
  await expect(decision.getByRole('status')).toContainText('15 eligible plays');
  await expect(decision.getByRole('region', { name: 'Situation filters' })).toHaveCount(0);
  await expect(decision.getByText('Field position: unrestricted; missing positions are not excluded by field position.')).toBeVisible();
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

test('Decision score filters preserve pre-play signs and ordered missingness through the real API', async ({ page }, info) => {
  await openViewer(page);
  const decision = await openDecision(page);
  const lower = decision.getByLabel('Minimum score difference', { exact: true });
  const upper = decision.getByLabel('Maximum score difference', { exact: true });
  let requests = 0;
  page.on('request', request => { if (new URL(request.url()).pathname === '/api/v1/decision') requests++; });
  await lower.fill('-'); await lower.press('Enter');
  await expect(lower).toBeFocused(); await expect(lower).toHaveValue('-');
  await expect(lower).toHaveAccessibleDescription(/Pre-play score bounds must be signed whole points/);
  expect(requests).toBe(0);
  await scanAccessibility(page, info, 'decision-score-invalid');
  await decision.getByLabel('Maximum yards to goal', { exact: true }).fill('20.5');
  await lower.fill('-7'); await upper.fill('0');
  const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/decision');
  await upper.press('Enter');
  const response = await pending;
  expect(response.status()).toBe(200);
  const params = new URL(response.url()).searchParams;
  expect(params.get('score_min')).toBe('-7'); expect(params.get('score_max')).toBe('0');
  expect(params.get('yardline_max')).toBe('20.5');
  const evidence = await response.json();
  // Invented rows: field excludes two missing and one at 80; score then excludes one missing.
  expect(evidence.population).toEqual({ plays: 11, games: 1 });
  expect(evidence.candidates[0]).toMatchObject({ plays: 3, epa_observations: 2, missing_epa: 1, epa_per_play: -.5 });
  expect(evidence.candidates[0].frequency).toBeCloseTo(3 / 11);
  await expect(decision.getByRole('status')).toContainText('11 eligible plays');
  const accounting = decision.getByRole('region', { name: 'Decision filter accounting, scroll horizontally on small screens' });
  expect(await accounting.getByRole('rowheader').allTextContents()).toEqual(['Field position', 'Pre-play score', 'Down', 'Distance']);
  const rows = await accounting.getByRole('row').all();
  const expected = [['15', '2', '1', '12'], ['12', '1', '0', '11'], ['11', '0', '0', '11'], ['11', '0', '0', '11']];
  for (let i = 1; i < rows.length; i++) expect(await rows[i].getByRole('cell').allTextContents()).toEqual(expected[i - 1]);
  await expect(decision.getByText('-7 to 0 points', { exact: true })).toBeVisible();
  await expect(decision.getByText(/a play missing both fields is removed at the field stage/)).toBeVisible();
  await scanAccessibility(page, info, 'decision-score-loaded');
  await page.setViewportSize({ width: 320, height: 900 });
  await accounting.focus(); await accounting.press('ArrowRight');
  await expect.poll(() => accounting.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath('decision-score-accounting-320.png') });
  await scanAccessibility(page, info, 'decision-score-320');
  await page.getByRole('tab', { name: 'Scout' }).click();
  const scoutScore = page.getByRole('textbox', { name: 'Minimum score difference' });
  await expect(scoutScore).toHaveValue(''); await scoutScore.fill('-14');
  await page.getByRole('tab', { name: 'Decision Lab' }).click();
  await expect(lower).toHaveValue('-7'); await expect(decision.getByRole('status')).toContainText('11 eligible plays');
  await lower.fill('0'); await upper.press('Enter');
  await expect(decision.getByRole('status')).toContainText('2 eligible plays');
  await expect(decision.getByText('0 to 0 points', { exact: true })).toBeVisible();
  const candidates = decision.getByRole('region', { name: 'Run and Pass evidence, scroll horizontally on small screens' });
  await expect(candidates.getByRole('row', { name: /^Run/ })).toContainText('EPA missing for every observed play');
  await expect(candidates.getByRole('row', { name: /^Pass/ })).toContainText('0.000');
  await lower.fill('1'); await upper.fill('6'); await upper.press('Enter');
  await expect(decision.getByRole('heading', { name: 'No eligible plays match this situation.' })).toBeVisible();
  await expect(decision.getByText('+1 to +6 points', { exact: true })).toBeVisible();
  await scanAccessibility(page, info, 'decision-score-empty');
  await lower.fill(''); await upper.fill('');
  await expect(decision.getByRole('article')).toHaveCount(0);
  const cleared = page.waitForResponse(result => new URL(result.url()).pathname === '/api/v1/decision');
  await upper.press('Enter');
  const clearedParams = new URL((await cleared).url()).searchParams;
  expect(clearedParams.has('score_min')).toBe(false); expect(clearedParams.has('score_max')).toBe(false);
  expect(clearedParams.get('yardline_max')).toBe('20.5');
  await expect(decision.getByRole('status')).toContainText('12 eligible plays');
  expect(await accounting.getByRole('rowheader').allTextContents()).toEqual(['Field position', 'Down', 'Distance']);
  await expect(decision.getByText('Pre-play score: unrestricted; missing scores are not excluded by score.')).toBeVisible();
  await expect(decision.getByRole('heading', { name: 'No preferred call' })).toBeVisible();
});

test('Decision period and clock filters preserve missingness and all ordered stages through the real API', async ({ page }, info) => {
  await openViewer(page);
  const decision = await openDecision(page);
  const period = decision.getByRole('combobox', { name: 'Period', exact: true });
  const lower = decision.getByLabel('Minimum seconds remaining', { exact: true });
  const upper = decision.getByLabel('Maximum seconds remaining', { exact: true });
  const compare = decision.getByRole('button', { name: 'Compare Run and Pass' });
  let requests = 0;
  page.on('request', request => { if (new URL(request.url()).pathname === '/api/v1/decision') requests++; });
  await upper.fill('0'); await upper.press('Enter');
  await expect(period).toBeFocused(); await expect(period).toHaveAccessibleDescription(/Choose an explicit period/);
  await expect(upper).toHaveValue('0'); expect(requests).toBe(0);
  await scanAccessibility(page, info, 'decision-time-invalid');
  await period.selectOption('Q4'); await upper.fill('2:00'); await upper.press('Enter');
  await expect(upper).toBeFocused(); await expect(upper).toHaveValue('2:00');
  await expect(upper).toHaveAccessibleDescription(/Clock bounds must be whole seconds/); expect(requests).toBe(0);
  await upper.fill(''); await compare.click();
  await expect(decision.getByRole('status')).toContainText('8 eligible plays'); // Q4 includes one missing clock.
  await expect(decision.getByText(/Clock unrestricted: period selection alone/)).toBeVisible();
  await lower.fill('0'); await upper.fill('900'); await compare.click();
  await expect(decision.getByRole('status')).toContainText('7 eligible plays'); // Same snapshot, explicit full range excludes it.
  await lower.fill(''); await upper.fill('120');
  await decision.getByLabel('Maximum yards to goal', { exact: true }).fill('20');
  await decision.getByLabel('Minimum score difference', { exact: true }).fill('-7');
  await decision.getByLabel('Maximum score difference', { exact: true }).fill('0');
  const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/decision');
  await upper.press('Enter'); const response = await pending;
  expect(response.status()).toBe(200);
  const params = new URL(response.url()).searchParams;
  expect(params.get('period')).toBe('Q4'); expect(params.get('clock_max')).toBe('120'); expect(params.has('clock_min')).toBe(false);
  const evidence = await response.json();
  expect(evidence.population).toEqual({ plays: 3, games: 1 });
  expect(evidence.candidates[0]).toMatchObject({ plays: 2, epa_observations: 1, missing_epa: 1, epa_per_play: -.4 });
  expect(evidence.candidates[0].frequency).toBeCloseTo(2 / 3);
  expect(evidence.candidates[1]).toMatchObject({ plays: 1, epa_observations: 1, epa_per_play: .8 });
  await expect(decision.getByRole('status')).toContainText('3 eligible plays');
  const accounting = decision.getByRole('region', { name: 'Decision filter accounting, scroll horizontally on small screens' });
  expect(await accounting.getByRole('rowheader').allTextContents()).toEqual(['Field position', 'Pre-play score', 'Period', 'Clock', 'Down', 'Distance']);
  const rows = await accounting.getByRole('row').all();
  const expected = [['15', '2', '1', '12'], ['12', '1', '0', '11'], ['11', '1', '5', '5'], ['5', '1', '1', '3'], ['3', '0', '0', '3'], ['3', '0', '0', '3']];
  for (let i = 1; i < rows.length; i++) expect(await rows[i].getByRole('cell').allTextContents()).toEqual(expected[i - 1]);
  await expect(decision.getByText('0–120 seconds remaining at play start', { exact: true })).toBeVisible();
  await expect(decision.getByText(/a play missing both period and clock is removed at period/)).toBeVisible();
  await scanAccessibility(page, info, 'decision-time-loaded');
  await page.setViewportSize({ width: 320, height: 900 });
  await accounting.focus(); await accounting.press('ArrowRight');
  await expect.poll(() => accounting.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await accounting.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath('decision-time-accounting-320.png') });
  await scanAccessibility(page, info, 'decision-time-320');
  await page.getByRole('tab', { name: 'Scout' }).click();
  await expect(page.getByRole('combobox', { name: 'Period', exact: true })).toHaveValue('');
  await page.getByRole('combobox', { name: 'Period', exact: true }).selectOption('Q2');
  await page.getByRole('tab', { name: 'Decision Lab' }).click();
  await expect(period).toHaveValue('Q4'); await expect(upper).toHaveValue('120');
  await expect(decision.getByRole('status')).toContainText('3 eligible plays');
  await period.selectOption('OT'); await compare.click();
  await expect(decision.getByRole('status')).toContainText('2 eligible plays'); // Both overtime periods 5 and 6.
  await expect(decision.getByText('OT — all periods numbered 5 or higher', { exact: true })).toBeVisible();
  await expect(decision.getByRole('row', { name: /^Run/ })).toContainText('-0.600');
  await expect(decision.getByRole('row', { name: /^Pass/ })).toContainText('0.400');
  await period.selectOption('Q4'); await lower.fill('0'); await upper.fill('0'); await compare.click();
  await expect(decision.getByRole('status')).toContainText('1 eligible plays');
  await expect(decision.getByText('0–0 seconds remaining at play start', { exact: true })).toBeVisible();
  await expect(decision.getByRole('row', { name: /^Run/ })).toContainText('-0.400');
  await lower.fill('1'); await upper.fill('59'); await compare.click();
  await expect(decision.getByRole('heading', { name: 'No eligible plays match this situation.' })).toBeVisible();
  await scanAccessibility(page, info, 'decision-time-empty');
  await period.selectOption('');
  await expect(lower).toHaveValue('1'); await expect(upper).toHaveValue('59');
  await expect(decision.getByRole('article')).toHaveCount(0);
  const beforeInvalid = requests;
  await compare.click(); await expect(period).toBeFocused(); expect(requests).toBe(beforeInvalid);
  await lower.fill(''); await upper.fill('');
  const cleared = page.waitForResponse(result => new URL(result.url()).pathname === '/api/v1/decision');
  await compare.click(); const clearedParams = new URL((await cleared).url()).searchParams;
  for (const key of ['period', 'clock_min', 'clock_max']) expect(clearedParams.has(key)).toBe(false);
  expect(clearedParams.get('yardline_max')).toBe('20'); expect(clearedParams.get('score_min')).toBe('-7');
  await expect(decision.getByRole('status')).toContainText('11 eligible plays');
  expect(await accounting.getByRole('rowheader').allTextContents()).toEqual(['Field position', 'Pre-play score', 'Down', 'Distance']);
  await expect(decision.getByRole('heading', { name: 'No preferred call' })).toBeVisible();
});

test('Decision league comparison preserves evidence, matches baseline contexts and explains unavailable differences', async ({ page }, info) => {
  await openViewer(page);
  const decision = await openDecision(page);
  const toggle = decision.getByRole('checkbox', { name: 'Compare with other offenses' });
  const submit = decision.getByRole('button', { name: 'Compare Run and Pass' });
  const request = async () => {
    const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/decision');
    await submit.click(); const response = await pending; expect(response.status()).toBe(200); return response;
  };
  let requests = 0;
  page.on('request', req => { if (new URL(req.url()).pathname === '/api/v1/decision') requests++; });
  await expect(toggle).not.toBeChecked();
  await decision.getByLabel('Maximum yards to goal', { exact: true }).fill('20');
  await decision.getByLabel('Minimum score difference', { exact: true }).fill('-7');
  await decision.getByLabel('Maximum score difference', { exact: true }).fill('0');
  await decision.getByRole('combobox', { name: 'Period', exact: true }).selectOption('Q4');
  await decision.getByLabel('Maximum seconds remaining', { exact: true }).fill('120');
  const off = await (await request()).json(); expect(off).not.toHaveProperty('league_comparison');
  await expect(decision.getByRole('status')).toContainText('3 eligible plays');
  const selectedTable = decision.getByRole('region', { name: 'Run and Pass evidence, scroll horizontally on small screens' });
  const originalSelected = await selectedTable.innerText();
  await toggle.focus(); await toggle.press('Space');
  await expect(toggle).toBeChecked(); await expect(decision.getByRole('article')).toHaveCount(0); expect(requests).toBe(1);
  const response = await request(); expect(new URL(response.url()).searchParams.get('compare_league')).toBe('true');
  const on = await response.json(); expect(on.candidates).toEqual(off.candidates); expect(on.source).toEqual(off.source);
  const comparison = decision.getByRole('region', { name: 'Matched candidate league comparison', exact: true });
  await expect(comparison).toBeVisible(); expect(await selectedTable.innerText()).toBe(originalSelected);
  await expect(comparison).toContainText('1 baseline plays / 1 games');
  await expect(comparison).toContainText('1 observed baseline offenses: ATL');
  await expect(comparison).toContainText('not Pass minus Run');
  await expect(comparison).toContainText('not an average of team rates');
  const run = decision.getByRole('region', { name: 'Run league comparison, scroll horizontally on small screens' });
  const pass = decision.getByRole('region', { name: 'Pass league comparison, scroll horizontally on small screens' });
  await expect(run.getByRole('row', { name: /^Call frequency/ })).toContainText('+66.7 pp');
  await expect(run.getByRole('row', { name: /^EPA/ }).getByRole('cell').last()).toHaveText('Unavailable');
  await expect(pass.getByRole('row', { name: /^EPA/ }).getByRole('cell')).toHaveText(['0.800', '3.000', '-2.200 EPA/play']);
  const ledger = decision.getByRole('region', { name: 'Baseline filter accounting, scroll horizontally on small screens' });
  expect(await ledger.getByRole('rowheader').allTextContents()).toEqual(['Field position', 'Pre-play score', 'Period', 'Clock', 'Down', 'Distance']);
  const rows = await ledger.getByRole('row').all();
  const expected = [['5', '1', '0', '4'], ['4', '0', '0', '4'], ['4', '1', '1', '2'], ['2', '1', '0', '1'], ['1', '0', '0', '1'], ['1', '0', '0', '1']];
  for (let i = 1; i < rows.length; i++) expect(await rows[i].getByRole('cell').allTextContents()).toEqual(expected[i - 1]);
  await expect(comparison).toContainText('20 eligible plays in the same season/type before the cutoff → 15 selected-offense plays removed → 5 other-offense plays');
  await scanAccessibility(page, info, 'decision-comparison-loaded');
  await page.setViewportSize({ width: 320, height: 900 });
  await pass.focus(); await pass.press('ArrowRight');
  await expect.poll(() => pass.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  await pass.scrollIntoViewIfNeeded(); await page.screenshot({ path: info.outputPath('decision-comparison-320.png') });
  await ledger.focus(); await ledger.press('ArrowRight');
  await expect.poll(() => ledger.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await ledger.scrollIntoViewIfNeeded(); await page.screenshot({ path: info.outputPath('decision-baseline-accounting-320.png') });
  await scanAccessibility(page, info, 'decision-comparison-320');
  await page.getByRole('tab', { name: 'Scout' }).click();
  const scoutToggle = page.getByRole('checkbox', { name: 'Compare with other teams in the same role' });
  await expect(scoutToggle).not.toBeChecked(); await scoutToggle.check();
  await page.getByRole('tab', { name: 'Decision Lab' }).click();
  await expect(toggle).toBeChecked(); await expect(comparison).toBeVisible(); expect(requests).toBe(2);
  await decision.getByLabel('Maximum seconds remaining', { exact: true }).fill('0');
  const emptyBaseline = await (await request()).json(); expect(emptyBaseline.league_comparison.population.plays).toBe(0);
  await expect(comparison).toContainText('No matching baseline plays. No broader baseline');
  await expect(run.getByRole('row', { name: /^Call frequency/ }).getByRole('cell').last()).toHaveText('Unavailable');
  await expect(selectedTable.getByRole('row', { name: /^Run/ })).toContainText('-0.400');
  await scanAccessibility(page, info, 'decision-comparison-empty-baseline');
  await decision.getByLabel('Offense team code', { exact: true }).fill('ZZZ');
  await decision.getByLabel('Maximum seconds remaining', { exact: true }).fill('120');
  const emptySelected = await (await request()).json(); expect(emptySelected.population.plays).toBe(0);
  expect(emptySelected.league_comparison.population.plays).toBe(4);
  await expect(comparison).toContainText('The selected cohort is empty');
  await expect(comparison).toContainText('2 observed baseline offenses: ATL, CAR');
  await expect(pass.getByRole('row', { name: /^EPA/ }).getByRole('cell')).toHaveText(['Unavailable', '1.900', 'Unavailable']);
  await scanAccessibility(page, info, 'decision-comparison-empty-selected');
  await decision.getByLabel('Offense team code', { exact: true }).fill('CAR');
  await toggle.focus(); await toggle.press('Space'); await expect(toggle).not.toBeChecked();
  const restored = await (await request()).json(); expect(restored.candidates).toEqual(off.candidates);
  await expect(decision.getByRole('status')).toContainText('3 eligible plays'); await expect(comparison).toHaveCount(0);
  expect(await selectedTable.innerText()).toBe(originalSelected);
  await expect(decision.getByRole('heading', { name: 'No preferred call' })).toBeVisible(); expect(requests).toBe(5);
});

test('Decision uncertainty uses real API support, bounded inputs and explicit empty states without changing point evidence', async ({ page }, info) => {
  await openViewer(page); const decision = await openDecision(page);
  await decision.getByLabel('Maximum yards to goal', { exact: true }).fill('20');
  await decision.getByLabel('Minimum score difference', { exact: true }).fill('-7');
  await decision.getByLabel('Maximum score difference', { exact: true }).fill('0');
  await decision.getByRole('combobox', { name: 'Period', exact: true }).selectOption('Q4');
  await decision.getByLabel('Maximum seconds remaining', { exact: true }).fill('120');
  const compare = decision.getByRole('checkbox', { name: 'Compare with other offenses' }); await compare.check();
  const repetitions = decision.getByLabel('Bootstrap repetitions', { exact: true });
  const seed = decision.getByLabel('Bootstrap seed', { exact: true });
  const title = 'Candidate game support and exploratory uncertainty';
  let requests = 0;
  page.on('request', r => { if (new URL(r.url()).pathname === '/api/v1/decision') requests++; });
  const request = async () => {
    const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/decision');
    await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
    const result = await response; expect(result.status()).toBe(200); return result;
  };
  const off = await (await request()).json(); expect(off.population.plays).toBe(3);
  const selected = decision.getByRole('region', { name: 'Run and Pass evidence, scroll horizontally on small screens' });
  const original = await selected.innerText();
  await repetitions.fill('199'); await seed.fill('0');
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  await expect(repetitions).toBeFocused(); await expect(repetitions).toHaveAccessibleDescription(/200.*1000/);
  await expect(decision.getByRole('alert')).toBeVisible(); expect(requests).toBe(1);
  await scanAccessibility(page, info, 'decision-uncertainty-invalid');
  await repetitions.fill('200'); await expect(decision.getByRole('article')).toHaveCount(0); expect(requests).toBe(1);
  const response = await request();
  expect(new URL(response.url()).searchParams.get('bootstrap_seed')).toBe('0');
  const { uncertainty, ...points } = await response.json(); expect(points).toEqual(off);
  expect(uncertainty).toMatchObject({ resampling_games: 1, repetitions: 200, performed_repetitions: 200, seed: 0, shared_game_weights: true });
  await expect(selected).toHaveText(original, { useInnerText: true });
  const section = decision.getByRole('region', { name: title }); await expect(section).toBeVisible();
  const run = decision.getByRole('region', { name: 'Run uncertainty, scroll horizontally on small screens' });
  const pass = decision.getByRole('region', { name: 'Pass uncertainty, scroll horizontally on small screens' });
  const runEPA = run.getByRole('row', { name: /^Selected \/ EPA/ }).getByRole('cell');
  await expect(runEPA.nth(0)).toHaveText('-0.400 EPA/play'); await expect(runEPA.nth(1)).toHaveText('Withheld');
  await expect(runEPA.nth(2)).toContainText('Selected 1'); await expect(runEPA.nth(3)).toHaveText('200 / 0');
  await expect(runEPA.nth(4)).toContainText('fewer than 5 contributing games');
  await expect(run.getByRole('row', { name: /^Baseline \/ Call frequency/ }).getByRole('cell').nth(0)).toHaveText('0.0%');
  await expect(run.getByRole('row', { name: /^Selected − baseline \/ EPA/ }).getByRole('cell').nth(1)).toHaveText('Unavailable');
  await expect(pass.getByRole('row', { name: /^Selected − baseline \/ EPA/ }).getByRole('cell').nth(0)).toHaveText('-2.200 EPA/play');
  await expect(section).toContainText('No Pass-minus-Run contrast interval is implemented');
  await decision.getByText('Decision uncertainty method and replay metadata').click();
  await expect(section).toContainText('python_random.Random.randrange / linear_n_minus_1');
  await scanAccessibility(page, info, 'decision-uncertainty-loaded');
  await page.setViewportSize({ width: 320, height: 900 }); await run.focus(); await run.press('ArrowRight');
  await expect.poll(() => run.evaluate(e => e.scrollLeft)).toBeGreaterThan(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await run.scrollIntoViewIfNeeded(); await page.screenshot({ path: info.outputPath('decision-uncertainty-320.png') });
  await scanAccessibility(page, info, 'decision-uncertainty-320');
  await page.getByRole('tab', { name: 'Scout' }).click();
  const scoutRepetitions = page.getByRole('tabpanel', { name: 'Scout' }).getByLabel('Bootstrap repetitions', { exact: true }); await expect(scoutRepetitions).toHaveValue(''); await scoutRepetitions.fill('500');
  await page.getByRole('tab', { name: 'Decision Lab' }).click();
  await expect(repetitions).toHaveValue('200'); await expect(section).toBeVisible(); expect(requests).toBe(2);
  await compare.uncheck(); const selectedOnly = await (await request()).json(); expect(selectedOnly.candidates).toEqual(off.candidates);
  expect(selectedOnly.uncertainty.shared_game_weights).toBe(false); await expect(section).toContainText('selected-only resampling frame');
  await expect(run.getByRole('row')).toHaveCount(4); await expect(section).toContainText('shared weights still apply across Run and Pass');
  await decision.getByLabel('Offense team code', { exact: true }).fill('ZZZ');
  const empty = await (await request()).json(); expect(empty.uncertainty.performed_repetitions).toBe(0);
  await expect(section).toContainText('0 / 200 performed / requested draws');
  await expect(run.getByRole('row', { name: /^Selected \/ Call frequency/ }).getByRole('cell').nth(1)).toHaveText('Unavailable');
  await scanAccessibility(page, info, 'decision-uncertainty-empty');
  await compare.check(); const baselineOnly = await (await request()).json(); expect(baselineOnly.uncertainty.performed_repetitions).toBe(200);
  await expect(run.getByRole('row', { name: /^Baseline \/ Call frequency/ }).getByRole('cell').nth(0)).toHaveText('50.0%');
  await expect(run.getByRole('row', { name: /^Selected − baseline \/ Call frequency/ }).getByRole('cell').nth(0)).toHaveText('Unavailable');
  await decision.getByLabel('Offense team code', { exact: true }).fill('CAR');
  await repetitions.fill(''); await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  await expect(repetitions).toBeFocused(); expect(requests).toBe(5); // retained seed requires correction
  await seed.fill(''); const restored = await request(); expect(await restored.json()).toEqual(off);
  expect(new URL(restored.url()).searchParams.has('bootstrap_repetitions')).toBe(false);
  await expect(section).toHaveCount(0); await expect(selected).toHaveText(original, { useInnerText: true });
  await expect(decision.getByRole('heading', { name: 'No preferred call' })).toBeVisible(); expect(requests).toBe(6);
});

test('Run/Pass choice stays local, keyboard operable and fixed-direction alongside real evidence', async ({ page }, info) => {
  await openViewer(page);
  const decision = await openDecision(page);
  const calls: string[] = [];
  page.on('request', request => { if (new URL(request.url()).pathname === '/api/v1/decision') calls.push(request.url()); });
  await decision.getByLabel('Maximum yards to goal').fill('20');
  await decision.getByLabel('Minimum score difference').fill('-7');
  await decision.getByLabel('Maximum score difference').fill('0');
  await decision.getByRole('combobox', { name: 'Period', exact: true }).selectOption('Q4');
  await decision.getByLabel('Maximum seconds remaining').fill('120');
  const run = decision.getByRole('radio', { name: 'Run', exact: true });
  const pass = decision.getByRole('radio', { name: 'Pass', exact: true });
  const clear = decision.getByRole('button', { name: 'Clear choice' });
  await expect(run).not.toBeChecked(); await expect(pass).not.toBeChecked(); await expect(clear).toBeDisabled();
  await run.focus(); await page.keyboard.press('Space'); await expect(run).toBeChecked();
  await page.keyboard.press('ArrowRight'); await expect(pass).toBeFocused(); await expect(pass).toBeChecked();
  await page.keyboard.press('ArrowLeft'); await expect(run).toBeFocused(); await expect(run).toBeChecked();
  await page.keyboard.press('Tab'); await expect(clear).toBeFocused(); await page.keyboard.press('Space');
  await expect(run).not.toBeChecked(); await expect(pass).not.toBeChecked();
  expect(calls).toHaveLength(0);
  await pass.check();
  await decision.getByRole('group', { name: 'Your call (optional)' }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath('decision-choice-controls.png') });
  const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/decision');
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  const received = await response;
  expect(received.status()).toBe(200);
  const data = await received.json();
  expect(data.comparison.preferred_candidate).toBeNull();
  expect(data.comparison.descriptive_contrast.direction).toBe('pass_minus_run');
  expect(data.comparison.descriptive_contrast.metrics.epa_per_play.value).toBeCloseTo(1.2);
  const comparison = decision.getByRole('region', { name: 'Run vs Pass: descriptive contrast', exact: true });
  const table = comparison.getByRole('table');
  await expect(table.getByRole('row', { name: /^Call frequency/ })).toContainText('-33.3 pp');
  await expect(table.getByRole('row', { name: /^EPA/ })).toContainText('+1.200 EPA/play');
  await expect(table.getByRole('row', { name: /^Offensive success/ })).toContainText('+100.0 pp');
  const text = await table.innerText();
  await expect(comparison).toContainText('Your choice: Pass. Alternative: Run.');
  await run.check();
  await expect(comparison).toContainText('Your choice: Run. Alternative: Pass.');
  await expect(table).toHaveText(text, { useInnerText: true });
  const points = decision.getByRole('table', { name: 'Observed Run and Pass evidence for the selected offense' });
  await expect(points.getByRole('rowheader').nth(0)).toHaveText(/RunYour choice/);
  await expect(points.getByRole('rowheader').nth(1)).toHaveText(/PassAlternative/);
  await expect(decision.getByRole('heading', { name: 'No preferred call' })).toBeVisible();
  await expect(comparison).toContainText('Pass-minus-Run interval: not implemented.');
  await page.getByRole('tab', { name: 'Scout' }).click();
  await expect(page.getByText('No report has been requested for these controls.', { exact: false })).toBeVisible();
  await page.getByRole('tab', { name: 'Decision Lab' }).click();
  await expect(run).toBeChecked(); await expect(table).toHaveText(text, { useInnerText: true });
  await scanAccessibility(page, info, 'decision-choice');
  await comparison.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath('decision-choice-contrast.png') });
  await page.setViewportSize({ width: 320, height: 900 });
  const scroll = comparison.getByRole('region', { name: /Pass minus Run descriptive contrast/ });
  await scroll.focus(); await expect(scroll).toBeFocused();
  expect(await scroll.evaluate(element => element.scrollWidth > element.clientWidth)).toBe(true);
  await page.keyboard.press('ArrowRight');
  await expect.poll(() => scroll.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  await page.keyboard.press('Tab'); await expect(scroll).not.toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await scanAccessibility(page, info, 'decision-choice-320');
  await clear.click(); await expect(comparison).toContainText('No call selected');
  await expect(table).toHaveText(text, { useInnerText: true });
  expect(calls).toHaveLength(1);
  expect(new URL(calls[0]).searchParams.has('decision_choice')).toBe(false);
  await pass.check(); await decision.getByLabel('Before week', { exact: true }).fill('2');
  await expect(pass).not.toBeChecked(); await expect(decision.getByRole('article')).toHaveCount(0);
  expect(calls).toHaveLength(1);
});

test('a selected call never fills absent or empty contrast evidence from the real API', async ({ page }, info) => {
  await openViewer(page);
  const decision = await openDecision(page);
  await decision.getByRole('combobox', { name: 'Period', exact: true }).selectOption('Q4');
  await decision.getByLabel('Minimum seconds remaining').fill('0');
  await decision.getByLabel('Maximum seconds remaining').fill('0');
  const pass = decision.getByRole('radio', { name: 'Pass', exact: true });
  await pass.check(); await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  const contrast = decision.getByRole('region', { name: 'Run vs Pass: descriptive contrast', exact: true });
  await expect(contrast.getByRole('row', { name: /^Call frequency/ })).toContainText('-100.0 pp');
  const epa = contrast.getByRole('row', { name: /^EPA/ });
  await expect(epa.getByRole('cell').nth(0)).toHaveText('Unavailable');
  await expect(epa).toContainText('Pass: no observed plays of this call.');
  await expect(contrast).toContainText('Your choice: Pass. Alternative: Run.');
  await scanAccessibility(page, info, 'decision-choice-unobserved');
  await decision.getByLabel('Before week', { exact: true }).fill('1');
  await expect(pass).not.toBeChecked(); await expect(contrast).toHaveCount(0);
  await decision.getByRole('radio', { name: 'Run', exact: true }).check();
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  await expect(decision.getByRole('heading', { name: 'No eligible plays match this situation.' })).toBeVisible();
  await expect(contrast.getByRole('row')).toHaveCount(4);
  const cells = await contrast.getByRole('row').all();
  for (const row of cells.slice(1)) {
    await expect(row.getByRole('cell').nth(0)).toHaveText('Unavailable');
    await expect(row).toContainText('Run: selected cohort is empty.');
    await expect(row).toContainText('Pass: selected cohort is empty.');
  }
  await expect(contrast).toContainText('Your choice: Run. Alternative: Pass.');
  await expect(decision.getByRole('heading', { name: 'No preferred call' })).toBeVisible();
  await scanAccessibility(page, info, 'decision-choice-empty');
});


test('Decision JSON native download preserves exact evidence independently of call choice and Scout', async ({ page }, info) => {
  await openViewer(page); await build(page);
  const scoutLink = page.getByRole('link', { name: 'Download report JSON' });
  await expect(scoutLink).toBeVisible(); const scoutUrl = await scoutLink.getAttribute('href');
  const decision = await openDecision(page);
  let requests = 0;
  page.on('request', request => { if (new URL(request.url()).pathname === '/api/v1/decision') requests++; });
  await decision.getByLabel('Maximum yards to goal').fill('20');
  await decision.getByLabel('Minimum score difference').fill('-7');
  await decision.getByLabel('Maximum score difference').fill('0');
  await decision.getByRole('combobox', { name: 'Period', exact: true }).selectOption('Q4');
  await decision.getByLabel('Maximum seconds remaining').fill('120');
  await decision.getByLabel('Compare with other offenses').check();
  await decision.getByLabel('Bootstrap repetitions', { exact: true }).fill('200');
  await decision.getByLabel('Bootstrap seed', { exact: true }).fill('7');
  const pass = decision.getByRole('radio', { name: 'Pass', exact: true }); await pass.check();
  const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/decision');
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  const received = await response; expect(received.status()).toBe(200);
  const bytes = await received.body(), data = JSON.parse(bytes.toString('utf8'));
  const downloadLink = decision.getByRole('link', { name: 'Download decision JSON' });
  await expect(downloadLink).toBeVisible(); const decisionUrl = await downloadLink.getAttribute('href');
  await expect(downloadLink).toHaveAccessibleDescription(/Your local call choice is not included/);
  expect(decisionUrl).not.toBe(scoutUrl);
  expect(data.population).toEqual({ plays: 3, games: 1 });
  expect(data.candidates[0]).toMatchObject({ candidate: 'run', plays: 2, epa_observations: 1, missing_epa: 1, epa_per_play: -.4 });
  expect(data.candidates[1]).toMatchObject({ candidate: 'pass', plays: 1, epa_per_play: .8 });
  expect(data.league_comparison.candidates[1].epa_per_play).toBe(3);
  expect(data.comparison.preferred_candidate).toBeNull();
  expect(data.comparison.descriptive_contrast.uncertainty).toEqual({ status: 'not_implemented', interval: null });
  expect(data.uncertainty.candidates[0].selected.frequency.status).toBe('insufficient_games');
  expect(data.source.label).toContain('SYNTHETIC browser integration fixture');

  for (const choice of ['Pass', 'Run', 'clear']) {
    if (choice === 'clear') await decision.getByRole('button', { name: 'Clear choice' }).click();
    else await decision.getByRole('radio', { name: choice, exact: true }).check();
    await expect(downloadLink).toHaveAttribute('href', decisionUrl!);
    await downloadLink.focus(); await expect(downloadLink).toBeFocused();
    const downloading = page.waitForEvent('download'); await downloadLink.press('Enter'); const download = await downloading;
    expect(download.suggestedFilename()).toBe('nfl-di-CAR-2024-REG-before-week-3-down-1-distance-10-10.decision.json');
    const saved = info.outputPath(`choice-${choice}.decision.json`); await download.saveAs(saved);
    expect(await readFile(saved)).toEqual(bytes);
    // An offline consumer reads the complete API response, not rounded display cells or the local annotation.
    const fingerprint = execFileSync('python3', ['-c', 'import json,sys; d=json.load(open(sys.argv[1])); assert d["comparison"]["preferred_candidate"] is None; assert "decision_choice" not in d; print(d["source"]["sha256"])', saved],
      { cwd: root, encoding: 'utf8', timeout: 10_000 });
    expect(fingerprint.trim()).toBe(data.source.sha256);
    expect(requests).toBe(1);
  }
  await scanAccessibility(page, info, 'decision-download');
  await decision.getByRole('region', { name: 'Decision download', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath('decision-download.png') });
  await page.getByRole('tab', { name: 'Scout' }).click(); await expect(scoutLink).toHaveAttribute('href', scoutUrl!);
  await page.getByRole('tab', { name: 'Decision Lab' }).click(); await expect(downloadLink).toHaveAttribute('href', decisionUrl!);
  expect(await page.locator('[id]').evaluateAll(nodes => new Set(nodes.map(node => node.id)).size === nodes.length)).toBe(true);
  await decision.getByLabel('Before week', { exact: true }).fill('1'); await expect(downloadLink).toHaveCount(0);
  const emptyResponse = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/decision');
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  const emptyBytes = await (await emptyResponse).body(); await expect(downloadLink).toBeVisible();
  await expect(decision.getByRole('heading', { name: 'No eligible plays match this situation.' })).toBeVisible();
  const downloading = page.waitForEvent('download'); await downloadLink.click(); const emptyDownload = await downloading;
  expect(emptyDownload.suggestedFilename()).toBe('nfl-di-CAR-2024-REG-before-week-1-down-1-distance-10-10.decision.json');
  const emptySaved = info.outputPath('empty.decision.json'); await emptyDownload.saveAs(emptySaved);
  expect(await readFile(emptySaved)).toEqual(emptyBytes); expect(JSON.parse(emptyBytes.toString()).candidates[0].frequency).toBeNull();
  expect(requests).toBe(2); await scanAccessibility(page, info, 'decision-download-empty');
});

test('Decision download failures and stale responses leave no old link while keeping valid evidence readable', async ({ page }, info) => {
  await openViewer(page); const decision = await openDecision(page);
  const downloadLink = decision.getByRole('link', { name: 'Download decision JSON' });
  await page.evaluate(() => {
    const create = URL.createObjectURL;
    // Keep the failure active through StrictMode's development effect replay.
    URL.createObjectURL = () => { throw new Error('/private/secret'); };
    window.addEventListener('restore-json-download', () => { URL.createObjectURL = create; }, { once: true });
  });
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  await expect(decision.getByRole('heading', { name: 'CAR · Run vs Pass' })).toBeVisible();
  await expect(decision.getByRole('alert')).toContainText('decision evidence is still available to read');
  await expect(decision.getByRole('alert')).not.toContainText('/private/secret'); await expect(downloadLink).toHaveCount(0);
  await expect(decision.getByRole('heading', { name: 'No preferred call' })).toBeVisible();
  await scanAccessibility(page, info, 'decision-download-preparation-error');
  await page.evaluate(() => window.dispatchEvent(new Event('restore-json-download')));
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click(); await expect(downloadLink).toBeVisible();
  await expect(decision.getByRole('alert')).toHaveCount(0);

  let release!: () => void; const held = new Promise<void>(resolve => { release = resolve; });
  let arrived!: () => void; const started = new Promise<void>(resolve => { arrived = resolve; });
  let finished!: () => void; const settled = new Promise<void>(resolve => { finished = resolve; });
  await page.route('**/api/v1/decision?*', async route => {
    const upstream = await route.fetch(); arrived(); await held;
    try { await route.fulfill({ response: upstream }); } finally { finished(); }
  });
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click(); await started;
  await expect(downloadLink).toHaveCount(0); await expect(decision.getByRole('status')).toContainText('Loading');
  await decision.getByLabel('Minimum yards to go', { exact: true }).fill('9'); release(); await settled;
  await expect(downloadLink).toHaveCount(0); await expect(decision.getByRole('article')).toHaveCount(0);
  await page.unroute('**/api/v1/decision?*');
  await page.route('**/api/v1/decision?*', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{"error":{"code":"report_busy"}}' }));
  await decision.getByRole('button', { name: 'Compare Run and Pass' }).click();
  await expect(decision.getByRole('alert')).toContainText('Another report is being built');
  await expect(downloadLink).toHaveCount(0); await scanAccessibility(page, info, 'decision-download-request-error');
});
