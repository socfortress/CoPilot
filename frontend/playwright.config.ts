import process from "node:process"
import { defineConfig, devices } from "@playwright/test"
import { BASE_URL, PORT } from "./e2e/config"
import "./e2e/load-env"

/**
 * Playwright setup for the analyst frontend.
 *
 * These are *real* end-to-end tests: a real browser drives the real Vue app, which
 * talks to a real CoPilot backend and a real MySQL. Nothing is stubbed — an API mock
 * would happily "prove" a tenancy fix that does not exist, since the whole point of
 * the fix is what the server refuses to send.
 *
 * What you need running before `pnpm test:e2e`:
 *   1. MySQL              — `docker compose up -d copilot-mysql`
 *   2. the backend        — `cd backend && uvicorn copilot:app --port 5000`
 *   3. nothing else       — Vite is started by this config (see `webServer`)
 *
 * Point it somewhere else with E2E_BASE_URL, and give it an admin account to seed
 * with via E2E_ADMIN_USER / E2E_ADMIN_PASSWORD (defaults match a fresh install).
 */

const USE_OWN_SERVER = !process.env.E2E_BASE_URL && !process.env.E2E_NO_SERVER

// `--headed` is how you watch it work, and at full speed a Vue app is a blur. Slow the
// browser down only when someone is actually looking at it.
const HEADED = process.argv.includes("--headed") || process.argv.includes("--debug")
const SLOW_MO = Number(process.env.E2E_SLOW_MO ?? (HEADED ? 350 : 0))

export default defineConfig({
	testDir: "./e2e",
	globalSetup: "./e2e/global-setup.ts",
	// Tenancy tests share seeded customers and users; running them in parallel against
	// one backend makes failures depend on ordering rather than on the code.
	workers: 1,
	fullyParallel: false,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	timeout: 60_000,
	expect: { timeout: 15_000 },
	reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"], ["html", { open: "never" }]],
	use: {
		baseURL: BASE_URL,
		// A failed run should be watchable after the fact, not just readable.
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
