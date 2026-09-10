import process from "node:process"
import { defineConfig, devices } from "@playwright/test"
import { BASE_URL, PORT } from "./e2e-mocked/config"

/**
 * Playwright setup for the *mocked* suite.
 *
 * Sibling of `playwright.config.ts`, and intentionally separate from it. That suite is
 * about what the server refuses to send, so it insists on a real backend and a real
 * MySQL and seeds them in `globalSetup`. These specs are about defects that live
 * entirely in the browser — a link built without a parameter, a form left unfilled —
 * where the backend is scenery. Stubbing it at the network layer is what makes the
 * scenario reproducible: the customer, the alert, the asset and the event sources are
 * fixed, so a failure means the app behaved differently, not that the data moved.
 *
 * Everything else is real: the real Vue app, in a real Chromium, with the real router,
 * the real stores and the real components.
 *
 *   pnpm test:e2e:mocked
 */
const USE_OWN_SERVER = !process.env.E2E_MOCK_BASE_URL && !process.env.E2E_NO_SERVER

const HEADED = process.argv.includes("--headed") || process.argv.includes("--debug")
const SLOW_MO = Number(process.env.E2E_SLOW_MO ?? (HEADED ? 350 : 0))

export default defineConfig({
	testDir: "./e2e-mocked",
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	timeout: 90_000,
	expect: { timeout: 15_000 },
	reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"], ["html", { open: "never" }]],
	use: {
		baseURL: BASE_URL,
		trace: "retain-on-failure",
		video: "retain-on-failure",
		screenshot: "only-on-failure",
		launchOptions: { slowMo: SLOW_MO },
		actionTimeout: 15_000
	},
	projects: [
		{
			name: "chromium",
			use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } }
		}
	],
	webServer: USE_OWN_SERVER
		? {
				command: `pnpm dev --port ${PORT} --strictPort`,
				url: BASE_URL,
				reuseExistingServer: true,
				timeout: 120_000,
				stdout: "ignore",
				stderr: "pipe"
			}
		: undefined
})
