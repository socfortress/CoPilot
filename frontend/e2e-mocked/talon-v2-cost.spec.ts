import type { BrowserContext, Page, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { installMockBackend, mintToken, signIn } from "./mock-backend"

/**
 * Talon v2 cost and run views (talon-analyst M5-9; CoPilot M5-9b), behind the "Talon v2" setting:
 * an admin sees the AI Analyst page's Usage and Budgets tabs, the usage total exactly as the API's
 * string; an analyst sees Usage (with what a non-admin sees said) and, on a job's page, its cost and
 * run timeline, and no Budgets tab. The server enforces all of it too; this pins what the UI offers.
 */

type Role = "admin" | "analyst"

const JOB = "copilot-inv-840-1760601600000"

function figures(cost: string) {
	return {
		responses: 2,
		input_tokens: 1200,
		output_tokens: 300,
		cache_read_tokens: 0,
		cache_write_tokens: 0,
		cost_usd: cost,
		unpriced_responses: 0,
		cost_complete: true,
		failed_attempts: 0
	}
}

const USAGE = {
	from: "2026-09-17",
	to: "2026-10-16",
	group_by: "customer",
	customer_code: null,
	groups: [
		{ key: "ACME", ...figures("0.2") },
		{ key: null, ...figures("0.1") }
	],
	truncated: false,
	total: figures("0.3")
}

function entry(extra: Record<string, unknown> = {}) {
	return {
		window: "day",
		period: "2026-10-16",
		limit_usd: "25",
		source: "override",
		spent_usd: "20.5",
		remaining_usd: "4.5",
		warning: true,
		exhausted: false,
		...extra
	}
}

const BUDGETS = {
	warn_at: "0.8",
	customers: [{ customer_code: "ACME", daily: entry(), monthly: entry({ window: "month", period: "2026-10" }) }],
	user: { user_id: "1", daily: entry({ limit_usd: null, source: "unset", remaining_usd: null, warning: false }) },
	general: { daily: entry({ limit_usd: null, source: "unset", remaining_usd: null, warning: false }) }
}

const JOB_ROW = {
	id: JOB,
	alert_id: 840,
	customer_code: "ACME",
	status: "completed",
	alert_type: null,
	triggered_by: "auto",
	template_used: null,
	created_at: "2026-10-16T08:00:00",
	started_at: "2026-10-16T08:00:01",
	completed_at: "2026-10-16T08:02:00",
	error_message: null
}

const INVESTIGATION = {
	job_id: JOB,
	customer_code: "ACME",
	status: "completed",
	stage_durations_ms: { S5: 61000 },
	runs: [
		{
			run_id: "r-1",
			stage: "S5",
			provider: "anthropic",
			model: "claude-sonnet-5-5",
			first_at: "2026-10-16T08:00:03+00:00",
			last_at: "2026-10-16T08:01:03+00:00",
			...figures("0.100412")
		}
	],
	truncated: false,
	total: figures("0.100412")
}

const TIMELINE = {
	job_id: JOB,
	customer_code: "ACME",
	spans: [
		{
			span_id: "000000000000000a",
			trace_id: "00000000000000000000000000000001",
			parent_id: null,
			kind: "AGENT",
			name: "invoke_agent analyst-investigation",
			start_time: "2026-10-16T08:00:00.000000Z",
			end_time: "2026-10-16T08:00:10.000000Z",
			duration_ms: 10000,
			status_code: "OK",
			stage: "S5",
			role: "analyst",
			model: null,
			tool: null,
			prompt_tokens: null,
			completion_tokens: null,
			total_tokens: null,
			cache_read_tokens: null,
			cache_write_tokens: null
		},
		{
			span_id: "000000000000000b",
			trace_id: "00000000000000000000000000000001",
			parent_id: "000000000000000a",
			kind: "TOOL",
			name: "execute_tool siem_search",
			start_time: "2026-10-16T08:00:02.000000Z",
			end_time: "2026-10-16T08:00:04.000000Z",
			duration_ms: 2000,
			status_code: "ERROR",
			stage: "S5",
			role: "analyst",
			model: null,
			tool: "siem_search",
			prompt_tokens: null,
			completion_tokens: null,
			total_tokens: null,
			cache_read_tokens: null,
			cache_write_tokens: null
		}
	],
	truncated: false,
	dropped: 0,
	note: null
}

interface Seen {
	paths: string[]
}

async function installCostMock(context: BrowserContext, role: Role): Promise<Seen> {
	const seen: Seen = { paths: [] }
	const json = (route: Route, body: unknown, status = 200) =>
		route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })

	// Registered after the generic mock, so these run first; anything else falls back to it.
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const path = new URL(route.request().url()).pathname.replace(/^\/api/, "")
			if (path.startsWith("/talon/")) seen.paths.push(path)

			if (path === "/auth/token" || path === "/auth/refresh") {
				return json(route, { success: true, access_token: mintToken(role, [role]), token_type: "bearer" })
			}
			if (path === "/talon/v2/availability") {
				return json(route, { success: true, message: "on", enabled: true, run_view: true })
			}
			if (path === "/talon/actions") return json(route, { success: true, message: "", actions: [] })
			if (path === "/talon/v2/usage") return json(route, USAGE)
			if (path === "/talon/v2/budgets") {
				// The backend's rule (decision B), so a UI that offered the tab to an analyst would show the refusal.
				return role === "admin"
					? json(route, BUDGETS)
					: json(route, { detail: "Only an admin may read or set Talon budgets" }, 403)
			}
			if (path === `/ai_analyst/jobs/${JOB}`) return json(route, { success: true, message: "", job: JOB_ROW })
			if (path === `/talon/v2/usage/investigations/${JOB}`) return json(route, INVESTIGATION)
			if (path === `/talon/v2/runs/${JOB}/timeline`) return json(route, TIMELINE)
			return route.fallback()
		}
	)
	return seen
}

async function signInAs(context: BrowserContext, page: Page, role: Role) {
	await installMockBackend(context)
	const seen = await installCostMock(context, role)
	await signIn(page)
	return seen
}

/** Naive's tabs carry no ARIA tab role: find them by their own class. */
function tab(page: Page, name: string) {
	return page.locator(".n-tabs-tab", { hasText: new RegExp(`^\\s*${name}\\s*$`) })
}

test.describe("talon v2 cost and run views", () => {
	test("an admin sees Usage and Budgets", async ({ context, page }) => {
		await signInAs(context, page, "admin")
		await page.goto("/ai-analyst")

		await expect(tab(page, "Usage")).toBeVisible()
		await expect(tab(page, "Budgets")).toBeVisible()

		await tab(page, "Usage").click()
		await expect(page.getByTestId("talon-usage-total-cost")).toHaveText("0.3")
		await expect(page.getByTestId("talon-usage-cost")).toHaveText(["0.2", "0.1"])
		await expect(page.getByTestId("talon-usage-scope-note")).toHaveCount(0)

		await tab(page, "Budgets").click()
		const daily = page.locator('[data-testid="talon-budget-row"][data-customer="ACME"][data-window="daily"]')
		await expect(daily.getByTestId("talon-budget-spent")).toHaveText("20.5")
		await expect(daily.getByTestId("talon-budget-warning")).toBeVisible()
	})

	test("an analyst sees Usage and the run view, but not Budgets", async ({ context, page }) => {
		const seen = await signInAs(context, page, "analyst")
		await page.goto("/ai-analyst")

		await expect(tab(page, "Usage")).toBeVisible()
		await expect(tab(page, "Approvals")).toBeVisible() // the v2 tabs are there, so Budgets' absence means something
		await expect(tab(page, "Budgets")).toHaveCount(0)

		await tab(page, "Usage").click()
		await expect(page.getByTestId("talon-usage-total-cost")).toHaveText("0.3")
		await expect(page.getByTestId("talon-usage-scope-note")).toHaveText(
			"Investigations for your customers and your own chat."
		)

		await page.goto(`/ai-analyst/jobs/${JOB}`)
		const card = page.getByTestId("job-cost-and-run")
		await expect(card.getByTestId("talon-job-cost-total")).toHaveText("0.100412")
		await expect(card.getByTestId("talon-run-span")).toHaveCount(2)
		await expect(card.getByTestId("talon-run-span-name").first()).toHaveText("invoke_agent analyst-investigation")
		await expect(card.getByTestId("talon-run-span-error")).toHaveCount(1)

		expect(seen.paths).not.toContain("/talon/v2/budgets")
	})
})
