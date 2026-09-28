import { execFileSync } from "node:child_process"
import process from "node:process"
import { fileURLToPath, URL } from "node:url"
import { defineConfig } from "cypress"

/**
 * Browser end-to-end tests for the Customer Portal (#1181). They drive the real portal
 * against a real backend and the disposable e2e MySQL: see cypress/README.md, or just
 * run `pnpm test:e2e`, which starts both servers for you.
 */

const backendDir = fileURLToPath(new URL("../backend", import.meta.url))
const python = process.env.E2E_PYTHON || `${backendDir}/.venv/bin/python`

/** Runs the backend seed shared with tests/e2e/customer_portal_overview_e2e.py. */
function portalSeed(command: "seed" | "cleanup") {
	const output = execFileSync(python, ["tests/e2e/portal_overview_seed.py", command], {
		cwd: backendDir,
		env: { ...process.env, PYTHONPATH: backendDir },
		encoding: "utf8",
		stdio: ["ignore", "pipe", "ignore"]
	})
	return command === "seed" ? JSON.parse(output.trim().split("\n").at(-1) ?? "{}") : null
}

export default defineConfig({
	e2e: {
		baseUrl: process.env.CYPRESS_BASE_URL || "http://localhost:3101",
		specPattern: "cypress/e2e/**/*.cy.ts",
		supportFile: "cypress/support/e2e.ts",
		video: false,
		defaultCommandTimeout: 15000,
		setupNodeEvents(on) {
			on("task", {
				"portal:seed": () => portalSeed("seed"),
				"portal:cleanup": () => portalSeed("cleanup")
			})
		}
	}
})
