import fs from 'node:fs/promises';
import path from 'node:path';
import {chromium} from 'playwright';

const BASE_URL = process.env.COPILOT_BASE_URL || 'https://copilot-lab.socfortressmdr.us';
const USERNAME = process.env.COPILOT_USERNAME;
const PASSWORD = process.env.COPILOT_PASSWORD;

if (!USERNAME || !PASSWORD) {
  console.error('Missing COPILOT_USERNAME or COPILOT_PASSWORD in environment.');
  process.exit(1);
}

const OUT_DIR = path.resolve(process.cwd(), '..', '..', 'docs', 'assets', 'ui');

const routes = [
  {key: 'overview', path: '/overview'},
  {key: 'incident-sources', path: '/incident-management/sources'},
  {key: 'incident-alerts', path: '/incident-management/alerts'},
  {key: 'incident-cases', path: '/incident-management/cases'},
  {key: 'alerts-siem', path: '/alerts/siem'},
  {key: 'alerts-mitre', path: '/alerts/mitre'},
  {key: 'alerts-atomic-red-team', path: '/alerts/atomic-red-team'},
  {key: 'artifacts', path: '/artifacts'},
  {key: 'customers', path: '/customers'},
  {key: 'agents', path: '/agents'},
  {key: 'agents-groups', path: '/agents/groups'},
  {key: 'agents-sysmon-config', path: '/agents/sysmon-config'},
  {key: 'agents-detection-rules', path: '/agents/detection-rules'},
  {key: 'agents-copilot-actions', path: '/agents/copilot-actions'},
  {key: 'agents-vulnerability-overview', path: '/agents/vulnerability-overview'},
  {key: 'agents-sca-overview', path: '/agents/sca-overview'},
  {key: 'patch-tuesday', path: '/patch-tuesday'},
  {key: 'report-general', path: '/report-creation/general'},
  {key: 'report-vulnerability', path: '/report-creation/vulnerability-reports'},
  {key: 'report-sca', path: '/report-creation/sca-reports'},
  {key: 'healthcheck', path: '/healthcheck'},
  {key: 'indices-management', path: '/indices/management'},
  {key: 'indices-snapshots', path: '/indices/snapshots'},
  {key: 'graylog-management', path: '/graylog/management'},
  {key: 'graylog-metrics', path: '/graylog/metrics'},
  {key: 'graylog-pipelines', path: '/graylog/pipelines'},
  {key: 'connectors', path: '/connectors'},
  {key: 'external-third-party-integrations', path: '/external-services/third-party-integrations'},
  {key: 'external-network-connectors', path: '/external-services/network-connectors'},
  {key: 'external-singul-app-auth', path: '/external-services/singul-app-auth'},
  {key: 'scheduler', path: '/scheduler'},
  {key: 'customer-portal', path: '/customer-portal'}
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function ensureDir(p) {
  await fs.mkdir(p, {recursive: true});
}

async function main() {
  await ensureDir(OUT_DIR);

  const browser = await chromium.launch({headless: true});
  const context = await browser.newContext({
    viewport: {width: 1440, height: 900},
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  // Login
  await page.goto(`${BASE_URL}/login`, {waitUntil: 'domcontentloaded'});
  await page.waitForTimeout(500);

  // Try a few common selectors for the login form
  const userInput = page.getByRole('textbox', {name: /username/i}).first()
    .or(page.getByPlaceholder(/username/i).first())
    .or(page.locator('input[type="text"], input[type="email"]').first());

  const passInput = page.getByRole('textbox', {name: /password/i}).first()
    .or(page.getByPlaceholder(/password/i).first())
    .or(page.locator('input[type="password"]').first());

  await userInput.fill(USERNAME);
  await passInput.fill(PASSWORD);

  const signIn = page.getByRole('button', {name: /sign in/i}).first()
    .or(page.locator('button[type="submit"]').first());

  await Promise.all([
    page.waitForLoadState('networkidle').catch(() => undefined),
    signIn.click()
  ]);

  // Give SPA time to hydrate
  await sleep(1500);

  // If still on /login, fail early
  if (page.url().includes('/login')) {
    const shot = path.join(OUT_DIR, '_login-failed.png');
    await page.screenshot({path: shot, fullPage: true});
    throw new Error(`Login appears to have failed; screenshot saved to ${shot}`);
  }

  // Screenshot sweep
  for (const r of routes) {
    const url = `${BASE_URL}${r.path}`;
    console.log(`SHOT ${r.key} -> ${url}`);
    await page.goto(url, {waitUntil: 'domcontentloaded'});
    await page.waitForTimeout(1200);

    // Attempt to close any toast/overlay by pressing Escape (best-effort)
    await page.keyboard.press('Escape').catch(() => undefined);

    const outPath = path.join(OUT_DIR, `${r.key}.png`);
    await page.screenshot({path: outPath, fullPage: true});
  }

  await browser.close();
  console.log(`Done. Wrote ${routes.length} screenshots to ${OUT_DIR}`);
}

main().catch((err) => {
  console.error(err?.stack || String(err));
  process.exit(1);
});
