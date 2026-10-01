import type { BrowserContext, Page, Route } from "@playwright/test"
import type { PolicyUpdatePayload, SocDashboard } from "../src/types/soc-management"
import { expect, test } from "@playwright/test"
import { installMockBackend, mintToken, signIn } from "./mock-backend"
import { dashboard, POLICY } from "./soc-management-fixtures"

/**
 * SOC Management (#1187) — the page's own behaviour, against a fixed snapshot.
 *
 * What lives in the browser and nowhere else: which number lands in which tile, that
 * the filters and the tab are the URL, that a period preset turns into the request's
 * date range, that a failure reads as one, that an analyst gets the analyst page, and
 * the exact policy payload a save sends. Tenancy — what the server refuses to send —
 * is the real-backend suite's job (`e2e/soc-management.spec.ts`).
 */

interface Mock {
	dashboardRequests: URL[]
	policySaves: PolicyUpdatePayload[]
}

async function installSocMock(
	context: BrowserContext,
	options: { snapshot?: SocDashboard; dashboardStatus?: number; role?: "admin" | "analyst" } = {}
): Promise<Mock> {
	const mock: Mock = { dashboardRequests: [], policySaves: [] }
	const json = (route: Route, body: unknown, status = 200) =>
		route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })

	// Registered after the generic mock, so these run first; anything else falls back to it.
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const url = new URL(route.request().url())
			const path = url.pathname.replace(/^\/api/, "")
			const method = route.request().method()

			if (path === "/auth/token" && options.role === "analyst") {
				return json(route, { success: true, access_token: mintToken("ana", ["analyst"]), token_type: "bearer" })
			}
			if (path === "/soc_management/dashboard") {
				mock.dashboardRequests.push(url)
				if (options.dashboardStatus && options.dashboardStatus >= 400) {
					return json(route, { detail: "The SOC Management service is unavailable" }, options.dashboardStatus)
				}
				return json(route, { success: true, message: "", ...(options.snapshot ?? dashboard()) })
			}
			if (path === "/soc_management/attention") {
				const snapshot = options.snapshot ?? dashboard()
				return json(route, {
					success: true,
					message: "",
					items: snapshot.attention,
					total: snapshot.attention.length
				})
			}
			if (path === "/soc_management/policies/overrides") {
				return json(route, { success: true, message: "", overrides: [] })
			}
			if (path === "/soc_management/policies" && method === "GET") {
				return json(route, { success: true, message: "", policy: POLICY })
			}
			if (path === "/soc_management/policies" && method === "PUT") {
				mock.policySaves.push(route.request().postDataJSON() as PolicyUpdatePayload)
				return json(route, { success: true, message: "Saved the global policy", policy: POLICY, retargeted: 0 })
			}
			if (path === "/incidents/db_operations/configured/sources") {
				return json(route, { success: true, message: "", sources: ["wazuh", "office365"] })
			}
			return route.fallback()
		}
	)
	return mock
}

async function open(page: Page, query = "") {
	await page.goto(`/soc-management${query}`)
	await expect(page.getByTestId("soc-management")).toBeVisible({ timeout: 60_000 })
}

test.describe("as an admin", () => {
	let mock: Mock

	test.beforeEach(async ({ context, page }) => {
		await installMockBackend(context)
		mock = await installSocMock(context)
		await signIn(page)
	})

	test("the overview shows the snapshot: hero rate, tiles with deltas, what needs attention", async ({ page }) => {
		await open(page)

		await expect(page.getByTestId("sla-gauge-value")).toHaveText(/96\.4\s*%/)
		const alertsOpened = page.getByTestId("kpi-alerts-opened")
		await expect(alertsOpened.getByTestId("kpi-value")).toHaveText("1,284")
		await expect(alertsOpened.getByTestId("delta-chip")).toContainText("+10%")
		await expect(page.getByTestId("kpi-tta").getByTestId("kpi-value")).toHaveText("12m")
		await expect(page.getByTestId("kpi-breached").getByTestId("kpi-value")).toHaveText("2")
		await expect(page.getByTestId("kpi-fp-rate").getByTestId("kpi-value")).toHaveText("31.5%")

		const attention = page.getByTestId("attention-list").first()
		await expect(attention).toContainText("Ransomware note dropped")
		await expect(attention).toContainText("Response breached")
		await expect(attention).toContainText("1h 45m late")
		await expect(page.getByTestId("attention-link-alert-4711")).toHaveAttribute(
			"href",
			"/incident-management/alerts/4711"
		)
		await expect(page.getByTestId("attention-link-case-12")).toHaveAttribute(
			"href",
			"/incident-management/cases/12"
		)
	})

	test("a period preset becomes the request's date range and the URL's", async ({ page }) => {
		await open(page)
		const before = mock.dashboardRequests.length
		await page.getByTestId("period-7d").click()

		await expect(page).toHaveURL(/period=7d/)
		await expect.poll(() => mock.dashboardRequests.length).toBeGreaterThan(before)
		const last = mock.dashboardRequests.at(-1) as URL
		const span =
			Date.parse(last.searchParams.get("date_to") as string) -
			Date.parse(last.searchParams.get("date_from") as string)
		expect(span).toBe(7 * 24 * 3600 * 1000)
	})

	test("the tab lives in the URL, and the rules tab filters its noisy rules", async ({ page }) => {
		await open(page)
		await page.getByTestId("soc-tab-rules").click()
		await expect(page).toHaveURL(/tab=rules/)

		const table = page.getByTestId("rules-table")
		await expect(table.locator("tbody tr")).toHaveCount(2)
		await expect(table).toContainText("noisy")
		await page.getByTestId("rules-only-noisy").click()
		await expect(table.locator("tbody tr")).toHaveCount(1)
		await expect(table).toContainText("Brute force SSH login")

		// A reload lands on the same tab.
		await page.reload()
		await expect(page.getByTestId("rules-table")).toBeVisible()
	})

	test("a severity filter is sent to the server and kept in the URL", async ({ page }) => {
		await open(page)
		await page.getByTestId("filter-severities").locator(".n-base-selection").click()
		await page.locator(".n-select-menu .n-base-select-option", { hasText: "Critical" }).click()
		await expect(page).toHaveURL(/severity=Critical/)
		await expect
			.poll(() => mock.dashboardRequests.at(-1)?.searchParams.getAll("severities[]"))
			.toEqual(["Critical"])
	})

	test("saving the policy sends the whole matrix, with the edited cell stored", async ({ page }) => {
		await open(page, "?tab=policies")
		await page.getByTestId("policy-own-alert-Critical").click()
		const respond = page.getByTestId("policy-ack-alert-Critical").locator("input").first()
		await respond.fill("10")
		await respond.blur()
		await page.getByTestId("policy-apply-open").click()
		await page.getByTestId("policy-save").click()

		await expect.poll(() => mock.policySaves.length).toBe(1)
		const payload = mock.policySaves[0]
		expect(payload.customer_code).toBeNull()
		expect(payload.apply_to_open).toBe(true)
		expect(payload.cells).toHaveLength(10)
		expect(payload.cells.find(c => c.entity === "alert" && c.severity === "Critical")).toEqual({
			entity: "alert",
			severity: "Critical",
			inherit: false,
			ack_minutes: 10,
			resolve_minutes: 240
		})
		// A cell the global policy already stores stays stored; the rest inherit the defaults.
		expect(payload.cells.find(c => c.entity === "alert" && c.severity === "High")?.inherit).toBe(false)
		expect(payload.cells.filter(c => c.inherit)).toHaveLength(8)
	})
})

test.describe("when things go wrong, or the viewer is an analyst", () => {
	test("a failed load says so instead of showing an empty dashboard", async ({ context, page }) => {
		await installMockBackend(context)
		await installSocMock(context, { dashboardStatus: 500 })
		await signIn(page)
		await open(page)
		await expect(page.getByTestId("soc-error")).toContainText("The SOC Management service is unavailable")
	})

	test("an analyst sees their own row, and the policy read-only", async ({ context, page }) => {
		await installMockBackend(context)
		const own = dashboard().analysts.filter(row => row.username === "ana")
		await installSocMock(context, {
			role: "analyst",
			snapshot: dashboard({
				viewer: { username: "ana", is_admin: false, sees_all_analysts: false },
				analysts: own
			})
		})
		await signIn(page)

		await open(page, "?tab=analysts")
		await expect(page.getByTestId("analysts-own-only")).toBeVisible()
		await expect(page.getByTestId("analysts-table").locator("tbody tr")).toHaveCount(1)

		await page.getByTestId("soc-tab-policies").click()
		await expect(page.getByTestId("policy-readonly")).toBeVisible()
		await expect(page.getByTestId("policy-save")).toHaveCount(0)
	})
})
