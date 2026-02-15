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

	await page.getByPlaceholder(/username/i).or(page.getByRole('textbox', {name: /username/i})).first().fill(USERNAME);
	await page.getByPlaceholder(/password/i).or(page.locator('input[type="password"]')).first().fill(PASSWORD);
	await page.getByRole('button', {name: /sign in/i}).first().click();
	await page.waitForTimeout(2000);
	if (page.url().includes('/login')) {
		throw new Error('Login failed (still on /login)');
	}

	// Go to Customers
	await page.goto(`${BASE_URL}/customers`, {waitUntil: 'domcontentloaded'});
	await page.waitForTimeout(2000);

	// Screenshot the customers list (baseline)
	await page.screenshot({path: path.join(OUT_DIR, 'customers-list.png'), fullPage: true});

	// Open a customer details modal/panel.
	// Prefer a "Details" button if present; otherwise click the first visible row card.
	const detailsBtn = page.getByRole('button', {name: /^Details$/i}).first();
	if (await detailsBtn.count().then((c) => c > 0)) {
		await detailsBtn.click();
	} else {
		// fallback: click the first customer card area
		await page.locator('text=/Total:/').locator('..').click({timeout: 2000}).catch(() => undefined);
	}
	await page.waitForTimeout(1500);

	// Helper to click tabs by name
	async function clickTab(name) {
		await page.getByRole('tab', {name}).click({timeout: 5000});
		await page.waitForTimeout(1200);
	}

	// Provision tab
	await clickTab(/Provision/i);
	await page.screenshot({path: path.join(OUT_DIR, 'customer-tab-provision.png'), fullPage: true});

	// 3rd Party Integrations tab
	await clickTab(/3rd Party Integrations/i);
	await page.screenshot({path: path.join(OUT_DIR, 'customer-tab-3rd-party-integrations.png'), fullPage: true});

	// Network Connectors tab
	await clickTab(/Network Connectors/i);
	await page.screenshot({path: path.join(OUT_DIR, 'customer-tab-network-connectors.png'), fullPage: true});

	await browser.close();
	console.log('Done: wrote customer tab screenshots to', OUT_DIR);
}

main().catch((e) => {
	console.error(e?.stack || String(e));
	process.exit(1);
});
