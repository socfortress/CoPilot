import type { BrowserContext, Page, Route } from "@playwright/test"
import process from "node:process"
import { expect, test } from "@playwright/test"
import { installMockBackend, mintToken, signIn } from "./mock-backend"

/**
 * The AI Analyst page's Overview tab is the Talon health dashboard (`GET /api/talon/health`),
 * whatever the "Talon v2" setting says: the banner, CoPilot's own checks, the component grid with a
 * "How to fix", the uptime bars, the charts and the configuration; with Talon unreachable, CoPilot's
 * checks and the reason; with an older Talon, the upgrade notice. `E2E_SHOTS=<dir>` saves a
 * screenshot of each state, to look at the layout.
 */

const OLD_TALON = "This Talon version has no health endpoint; upgrade to talon-analyst 0.1.3 or later"
const IDS: [string, string, string][] = [
	["api", "API", "core"],
	["database", "Database", "core"],
	["queue", "Queue", "core"],
	["migrations", "Migrations", "core"],
	["mempalace", "MemPalace", "core"],
	["phoenix", "Phoenix", "core"],
	["sandbox", "Sandbox", "core"],
	["indexer_mcp", "Wazuh indexer MCP", "mcp"],
	["wazuh_mcp", "Wazuh manager MCP", "mcp"],
	["velociraptor_mcp", "Velociraptor MCP", "mcp"],
	["intel_mcp", "Threat intel MCP", "mcp"],
	["model_provider", "Model provider", "model"]
]

function hoursAgo(h: number, minutes = 60) {
	const now = Date.now()
	const start = Math.floor(now / (minutes * 60_000)) * minutes * 60_000
	return new Date(start - h * minutes * 60_000).toISOString().replace(".000Z", "Z")
}

function healthy() {
	const count = 288
	const components = IDS.map(([id, name, group]) => {
		const status = id === "wazuh_mcp" ? "warn" : id === "intel_mcp" ? "off" : "ok"
		return {
			id,
			name,
			group,
			status,
			latency_ms: status === "off" ? null : 4 + id.length,
			detail:
				status === "warn"
					? "The Wazuh API answered slowly (2.4 s)"
					: status === "off"
						? "Threat intel is not set up"
						: `${name} answered`,
			fix: status === "warn" ? "Check the Wazuh manager's load, and that the read-only API account is not locked." : null,
			checked_at: hoursAgo(0, 1)
		}
	})
	const history: Record<string, unknown[]> = {}
	for (const [id] of IDS) {
		history[id] = Array.from({ length: count }, (_, i) => {
			const t = hoursAgo(count - 1 - i, 5)
			if (id === "intel_mcp") return { t, ok: 0, warn: 0, fail: 0 }
			if (id === "wazuh_mcp" && i > 270) return { t, ok: 2, warn: 3, fail: 0 }
			if (id === "model_provider" && i >= 120 && i < 123) return { t, ok: 1, warn: 0, fail: 4 }
			return { t, ok: 5, warn: 0, fail: 0 }
		})
	}
	const series = Array.from({ length: 24 }, (_, i) => ({
		t: hoursAgo(23 - i),
		investigations_completed: [3, 5, 2, 0, 1, 4, 6, 8, 7, 9, 5, 4, 6, 3, 2, 5, 7, 6, 4, 3, 2, 4, 5, 3][i],
		investigations_failed: i === 10 || i === 11 ? 2 : 0,
		queue_depth_max: i < 3 ? null : [0, 1, 2, 4, 1, 0, 3, 2, 1, 0, 0, 1, 2, 1, 0, 0, 1, 2, 1, 0, 1][i - 3],
		duration_p50_s: 60 + (i % 5) * 7,
		duration_p95_s: 140 + (i % 4) * 22,
		tool_calls: 30 + (i % 6) * 6,
		tool_errors: null,
		model_errors: i === 10 ? 3 : 0,
		cost_usd: `${(0.4 + (i % 7) * 0.13).toFixed(4)}`
	}))
	return {
		success: true,
		message: "Talon health retrieved",
		hours: 24,
		checked_at: new Date(Date.now() - 9000).toISOString(),
		copilot: {
			connector: { exists: true, configured: true, verified: true, url: "http://talon-analyst-api:3100" },
			reachable: { ok: true, latency_ms: 6.2, status_code: 200, error: null },
			auth: { ok: true, latency_ms: null, status_code: 200, error: null },
			v2_enabled: true,
			last_sent: { customer_code: "ACME", status: "pipeline", at: hoursAgo(0, 1).replace("Z", "") },
			last_job: { customer_code: "ACME", status: "running", at: hoursAgo(0, 1).replace("Z", "") },
			last_report: { customer_code: "ACME", status: null, at: hoursAgo(1, 10).replace("Z", "") },
			jobs_failed_24h: 4,
			ai_trigger_customers: 3,
			scope: "deployment"
		},
		health: {
			data: {
				status: "degraded",
				version: "0.1.3",
				image_browser: false,
				uptime_seconds: 302_400,
				checked_at: hoursAgo(0, 1),
				components,
				config: {
					writeback_mode: "live",
					live_customers: ["ACME", "GLOBEX"],
					automation_max_level: 1,
					automation_policy_source: "copilot",
					v2_api: true,
					action_tools: true,
					endpoint_actions: true,
					intel: false,
					workspace_tools: false,
					chat_browser: false,
					models: { chat: "claude-sonnet-5-5", investigation: "claude-opus-5-5" },
					budgets: { daily_usd: "25.00", monthly_usd: "unlimited", spent_today_usd: "12.4402", spent_month_usd: "311.20" }
				}
			},
			error: null,
			status_code: 200,
			unsupported: false
		},
		history: { data: { bucket_minutes: 5, components: history }, error: null, status_code: 200, unsupported: false },
		metrics: { data: { bucket_minutes: 60, series }, error: null, status_code: 200, unsupported: false }
	}
}

function unreachable() {
	const error = "Talon could not be reached (ConnectError)"
	const base = healthy()
	const none = { data: null, error, status_code: null, unsupported: false }
	return {
		...base,
		copilot: {
			...base.copilot,
			reachable: { ok: false, latency_ms: null, status_code: null, error },
			auth: { ok: null, latency_ms: null, status_code: null, error }
		},
		health: none,
		history: none,
		metrics: none
	}
}

function oldTalon() {
	const old = { data: null, error: OLD_TALON, status_code: 404, unsupported: true }
	return { ...healthy(), health: old, history: old, metrics: old }
}

async function installHealthMock(context: BrowserContext, body: () => unknown) {
	const seen: string[] = []
	const json = (route: Route, payload: unknown, status = 200) =>
		route.fulfill({ status, contentType: "application/json", body: JSON.stringify(payload) })
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const url = new URL(route.request().url())
			const path = url.pathname.replace(/^\/api/, "")
			if (path === "/auth/token" || path === "/auth/refresh") {
				return json(route, { success: true, access_token: mintToken("admin", ["admin"]), token_type: "bearer" })
			}
			if (path === "/talon/health") {
				seen.push(url.search)
				return json(route, body())
			}
			if (path === "/talon/v2/availability") {
				return json(route, { success: true, message: "on", enabled: true, run_view: false })
			}
			if (path === "/talon/actions") return json(route, { success: true, message: "", actions: [] })
			if (path === "/talon/v2/usage") {
				return json(route, {
					from: "2026-09-23",
					to: "2026-10-22",
					group_by: "customer",
					customer_code: null,
					groups: [],
					truncated: false,
					total: {
						responses: 0,
						input_tokens: 0,
						output_tokens: 0,
						cache_read_tokens: 0,
						cache_write_tokens: 0,
						cost_usd: "0",
						unpriced_responses: 0,
						cost_complete: true,
						failed_attempts: 0
					}
				})
			}
			return route.fallback()
		}
	)
	return seen
}

async function open(context: BrowserContext, page: Page, body: () => unknown) {
	await installMockBackend(context)
	const seen = await installHealthMock(context, body)
	await signIn(page)
	await page.goto("/ai-analyst")
	await expect(page.getByTestId("talon-health-banner")).toBeVisible()
	return seen
}

async function shot(page: Page, name: string) {
	const dir = process.env.E2E_SHOTS
	if (!dir) return
	// The app scrolls inside its own layout, so a full-page shot is the viewport: make it tall.
	const size = page.viewportSize()
	await page.setViewportSize({ width: 1440, height: 3600 })
	await page.waitForTimeout(500)
	await page.screenshot({ path: `${dir}/${name}.png` })
	if (size) await page.setViewportSize(size)
}

test.describe("talon health dashboard", () => {
	test("a degraded Talon: every section, a fix, the 7 d window and the Usage link", async ({ context, page }) => {
		const seen = await open(context, page, healthy)
		await expect(page.getByTestId("talon-health-banner-title")).toHaveText("Degraded")
		await expect(page.getByTestId("talon-health-version")).toContainText("0.1.3")
		await expect(page.getByTestId("talon-check-reachable")).toContainText("Yes, 6 ms")
		await expect(page.getByTestId("talon-health-component")).toHaveCount(12)
		await expect(page.getByTestId("talon-uptime-row")).toHaveCount(12)
		await expect(page.locator('[data-testid="talon-uptime-row"][data-component="model_provider"] [data-testid="talon-uptime-summary"]')).toHaveText(
			"1 failing of 96"
		)
		await expect(page.getByTestId("talon-health-chart-tools")).toContainText("Tool errors: no data")
		await expect(page.getByTestId("talon-config-budget-daily")).toContainText("$25.00")
		await shot(page, "health-degraded")

		const wazuh = page.locator('[data-testid="talon-health-component"][data-component="wazuh_mcp"]')
		await wazuh.getByText("How to fix").click()
		await expect(wazuh.getByTestId("talon-health-fix")).toBeVisible()

		await page.getByTestId("talon-health-window-168").click()
		await expect.poll(() => seen.at(-1)).toBe("?hours=168")

		await page.getByTestId("talon-health-usage-link").click()
		await expect(page.getByTestId("talon-usage")).toBeVisible()
	})

	test("Talon unreachable: CoPilot's checks and the reason", async ({ context, page }) => {
		await open(context, page, unreachable)
		await expect(page.getByTestId("talon-health-banner-title")).toHaveText("Down")
		await expect(page.getByTestId("talon-check-reachable-detail")).toHaveText("Talon could not be reached (ConnectError)")
		await expect(page.getByTestId("talon-health-unavailable")).toHaveCount(4)
		await shot(page, "health-unreachable")
	})

	test("an older Talon: the upgrade notice", async ({ context, page }) => {
		await open(context, page, oldTalon)
		await expect(page.getByTestId("talon-health-old")).toContainText(OLD_TALON)
		await expect(page.getByTestId("talon-check-auth")).toContainText("Accepted")
		await shot(page, "health-old-talon")
	})
})
