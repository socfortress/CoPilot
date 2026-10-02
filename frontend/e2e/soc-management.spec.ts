import { execFileSync } from "node:child_process"
import process from "node:process"
import { fileURLToPath, URL } from "node:url"
import { expect, test } from "@playwright/test"
import { apiAs, signIn, signOut } from "./fixtures/auth"

/**
 * SOC Management & SLA (#1187), end to end: real app, real backend, real MySQL.
 *
 * A month of SOC history is seeded by `backend/tests/e2e/soc_management_seed.py` (the
 * same script the backend's own e2e documents) because response and resolution times
 * cannot be produced in the past through the API. Everything else goes through the API
 * and the UI as a person would — which is what these specs are about:
 *
 * - an analyst assigned to one customer sees that customer's figures, and only their own
 *   analyst row — on screen and below it;
 * - SLA policies are an admin's to change, and a change persists;
 * - a human action through the incidents API stops an SLA clock, and the alert page
 *   shows it;
 * - a case's severity can be set from its page and re-targets its clock;
 * - a customer's business hours are an admin's to set, and persist;
 * - an alert waiting on the customer shows its clocks stopped, and the wait afterwards —
 *   set through the alert page's own status switch, as an analyst would;
 * - publishing the Customer Portal SLA page is a switch on the customer, and persists;
 * - the PDF report downloads.
 *
 * The seeded rows are left in place, like the rest of this suite's seed: the script is
 * idempotent, and `soc_management_seed.py cleanup` removes them by hand.
 *
 * The seed needs the backend's virtualenv (E2E_PYTHON to override) and the backend's
 * database env (MYSQL_URL & co. — the disposable 13306 instance by default).
 */

const backendDir = fileURLToPath(new URL("../../backend", import.meta.url))
const python = process.env.E2E_PYTHON || `${backendDir}/.venv/bin/python`

interface Seed {
	admin: string
	scoped_analyst: string
	analysts: string[]
	password: string
	customers: Record<string, string>
	scoped_customer: string
	override_customer: string
	ids: { unacked_open_alert: Record<string, number>; case: Record<string, number> }
}

function socSeed(command: "seed" | "cleanup"): Seed | null {
	const output = execFileSync(python, ["tests/e2e/soc_management_seed.py", command], {
		cwd: backendDir,
		env: { ...process.env, PYTHONPATH: backendDir },
		encoding: "utf8",
		stdio: ["ignore", "pipe", "ignore"],
		timeout: 120_000
	})
	return command === "seed" ? (JSON.parse(output.trim().split("\n").at(-1) ?? "{}") as Seed) : null
}

let seed: Seed
function CODES() {
	return Object.keys(seed.customers)
}

function scopedQuery() {
	return CODES()
		.map(code => `customer=${code}`)
		.join("&")
}

test.describe.configure({ mode: "serial" })

test.beforeAll(() => {
	seed = socSeed("seed") as Seed
})

test.describe("an admin", () => {
	test.beforeEach(async ({ page }) => {
		await signOut(page)
		await signIn(page, seed.admin, seed.password)
	})

	test("sees a month of SOC history, every analyst, and every customer", async ({ page }) => {
		await page.goto(`/soc-management?${scopedQuery()}`)
		await expect(page.getByTestId("kpi-alerts-opened").getByTestId("kpi-value")).not.toHaveText("0", {
			timeout: 30_000
		})
		await expect(page.getByTestId("sla-gauge-value")).toHaveText(/\d+\.\d\s*%/)

		await page.getByTestId("soc-tab-analysts").click()
		const analysts = page.getByTestId("analysts-table")
		for (const name of [seed.scoped_analyst, ...seed.analysts]) {
			await expect(analysts).toContainText(name)
		}

		await page.getByTestId("soc-tab-customers").click()
		for (const name of Object.values(seed.customers)) {
			await expect(page.getByTestId("customers-table")).toContainText(name)
		}

		await page.getByTestId("soc-tab-rules").click()
		await expect(page.getByTestId("rules-table")).toContainText("Brute force SSH login")
		await expect(page.getByTestId("rules-table")).toContainText("noisy")
	})

	test("changes a customer's SLA override, and it persists", async ({ page }) => {
		const code = seed.override_customer
		await page.goto("/soc-management?tab=policies")
		await page.getByTestId(`policy-scope-${code}`).click()
		await expect(page.getByTestId("policy-own-alert-High")).toContainText("Override")

		await page.getByTestId("policy-own-alert-Medium").click()
		const respond = page.getByTestId("policy-ack-alert-Medium").locator("input").first()
		await respond.fill("45")
		await respond.blur()
		await page.getByTestId("policy-ack-alert-Medium").locator(".n-base-selection").click()
		await page.locator(".n-select-menu .n-base-select-option", { hasText: "min" }).click()
		await page.getByTestId("policy-save").click()
		await expect(page.getByText(`Saved customer ${code}`)).toBeVisible()

		const stored = await (await apiAs(seed.admin, `/soc_management/policies?customer_code=${code}`)).json()
		const medium = stored.policy.cells.find(
			(c: { entity: string; severity: string }) => c.entity === "alert" && c.severity === "Medium"
		)
		expect(medium).toMatchObject({ ack_minutes: 45, source: "customer" })

		// "Follow global" removes every override of the customer.
		await page.getByTestId("policy-remove-override").click()
		await page.getByRole("button", { name: "Confirm" }).click()
		await expect(page.getByTestId("policy-own-alert-High")).not.toHaveClass(/n-switch--active/)
		const after = await (await apiAs(seed.admin, `/soc_management/policies?customer_code=${code}`)).json()
		expect(after.policy.cells.filter((c: { source: string }) => c.source === "customer")).toEqual([])
	})

	test("sets a customer's business hours, which persist until it follows the global ones again", async ({
		page
	}) => {
		const code = seed.override_customer
		await page.goto("/soc-management?tab=policies")
		await page.getByTestId(`policy-scope-${code}`).click()
		const calendar = page.getByTestId("calendar-panel")
		await expect(calendar.getByTestId("calendar-source")).not.toHaveText("Customer calendar")

		await calendar.getByTestId("calendar-open-sat").click()
		await calendar.getByTestId("calendar-save").click()
		await expect(page.getByText(`Saved customer ${code}`)).toBeVisible()
		await expect(calendar.getByTestId("calendar-source")).toHaveText("Customer calendar")
		await expect(page.getByTestId(`policy-scope-calendar-${code}`)).toBeVisible()

		const stored = await (await apiAs(seed.admin, `/soc_management/calendars?customer_code=${code}`)).json()
		expect(stored.calendar).toMatchObject({ source: "customer" })
		expect(stored.calendar.week.sat).toEqual([["09:00", "17:00"]])

		await calendar.getByTestId("calendar-remove").click()
		await page.getByRole("button", { name: "Confirm" }).click()
		await expect(calendar.getByTestId("calendar-source")).not.toHaveText("Customer calendar")
		const after = await (await apiAs(seed.admin, `/soc_management/calendars?customer_code=${code}`)).json()
		expect(after.calendar.source).not.toBe("customer")
	})

	test("publishes the Customer Portal SLA page from the customer's SLA tab, and it persists", async ({ page }) => {
		const code = seed.scoped_customer
		const stored = async () =>
			(await (await apiAs(seed.admin, `/customer_portal/sla/settings/${code}`)).json()).settings.enabled as boolean
		await apiAs(seed.admin, `/customer_portal/sla/settings/${code}`, {
			method: "PUT",
			body: JSON.stringify({ enabled: false })
		})

		await page.goto(`/customers/${code}`)
		await page.locator(".n-tabs-tab", { hasText: /^\s*SLA\s*$/ }).click()
		const toggle = page.getByTestId("sla-settings-switch")
		await expect(toggle).toBeVisible({ timeout: 30_000 })
		await expect(page.getByTestId("sla-settings-state")).toContainText("stay internal")

		await toggle.click()
		await expect(page.getByTestId("sla-settings-state")).toContainText("can see their SLA targets")
		await expect.poll(stored).toBe(true)

		await page.reload()
		await page.locator(".n-tabs-tab", { hasText: /^\s*SLA\s*$/ }).click()
		await expect(page.getByTestId("sla-settings-switch")).toHaveClass(/n-switch--active/, { timeout: 30_000 })
		await page.getByTestId("sla-settings-switch").click()
		await expect.poll(stored).toBe(false)
	})

	test("sets a case's severity from its page, which re-targets its clock", async ({ page }) => {
		const caseId = seed.ids.case[seed.scoped_customer] ?? Object.values(seed.ids.case)[0]
		await page.goto(`/incident-management/cases/${caseId}`)
		await expect(page.getByTestId("item-sla-case")).toBeVisible({ timeout: 30_000 })

		await page.getByTestId("case-severity-value").click()
		await page.locator(".n-popselect-menu .n-base-select-option", { hasText: "Critical" }).click()
		await expect(page.getByTestId("case-severity-value")).toContainText("Critical")
		await expect(page.getByTestId("item-sla-case")).toContainText("Critical")

		const sla = await (await apiAs(seed.admin, `/soc_management/items/case/${caseId}/sla`)).json()
		expect(sla.severity).toBe("Critical")
	})

	test("downloads the SOC report as a PDF", async ({ page }) => {
		await page.goto(`/soc-management?${scopedQuery()}`)
		await expect(page.getByTestId("soc-export")).toBeEnabled({ timeout: 30_000 })
		const download = page.waitForEvent("download", { timeout: 90_000 })
		await page.getByTestId("soc-export").click()
		expect((await download).suggestedFilename()).toMatch(/^soc_report_\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}\.pdf$/)
	})
})

test.describe("an analyst assigned to one customer", () => {
	test.beforeEach(async ({ page }) => {
		await signOut(page)
		await signIn(page, seed.scoped_analyst, seed.password)
	})

	test("sees only that customer's figures and only their own analyst row", async ({ page }) => {
		await page.goto("/soc-management?tab=analysts")
		await expect(page.getByTestId("analysts-own-only")).toBeVisible({ timeout: 30_000 })
		await expect(page.getByTestId("analysts-table").locator("tbody tr")).toHaveCount(1)
		await expect(page.getByTestId("analysts-table")).toContainText(seed.scoped_analyst)

		await page.getByTestId("soc-tab-customers").click()
		const customers = page.getByTestId("customers-table")
		await expect(customers).toContainText(seed.scoped_customer)
		for (const code of CODES().filter(c => c !== seed.scoped_customer)) {
			await expect(customers).not.toContainText(code)
		}
	})

	test("is refused the other customers below the UI too", async ({ page }) => {
		await page.goto("/soc-management")
		const other = CODES().find(c => c !== seed.scoped_customer) as string
		const now = new Date()
		const period = `date_from=${new Date(now.getTime() - 30 * 86_400_000).toISOString()}&date_to=${now.toISOString()}`

		const asked = await (
			await apiAs(seed.scoped_analyst, `/soc_management/dashboard?${period}&customer_codes=${other}`)
		).json()
		expect(asked.customer_codes).toEqual([])
		expect(asked.headline.alerts.opened).toBe(0)

		const foreignAlert = seed.ids.unacked_open_alert[other]
		expect((await apiAs(seed.scoped_analyst, `/soc_management/items/alert/${foreignAlert}/sla`)).status).toBe(404)

		const save = await apiAs(seed.scoped_analyst, "/soc_management/policies", {
			method: "PUT",
			body: JSON.stringify({ customer_code: null, cells: [] })
		})
		expect(save.status).toBe(403)
	})

	test("stops an alert's response clock by acting on it", async ({ page }) => {
		const alertId = seed.ids.unacked_open_alert[seed.scoped_customer]
		await page.goto(`/incident-management/alerts/${alertId}`)
		const ack = page.getByTestId("item-sla-ack")
		await expect(ack).toBeVisible({ timeout: 30_000 })
		await expect(ack).not.toContainText(seed.scoped_analyst)

		const response = await apiAs(seed.scoped_analyst, "/incidents/db_operations/alert/status", {
			method: "PUT",
			body: JSON.stringify({ alert_id: alertId, status: "IN_PROGRESS" })
		})
		expect(response.ok).toBe(true)

		await page.reload()
		await expect(page.getByTestId("item-sla-ack")).toContainText(seed.scoped_analyst, { timeout: 30_000 })
		const sla = await (await apiAs(seed.scoped_analyst, `/soc_management/items/alert/${alertId}/sla`)).json()
		expect(sla.ack).toMatchObject({ by: seed.scoped_analyst, action: "status_changed" })
	})

	test("puts an alert on hold for the customer: its clocks stop, and the wait is shown after", async ({ page }) => {
		const alertId = seed.ids.unacked_open_alert[seed.scoped_customer]
		const setStatus = (status: string) =>
			apiAs(seed.scoped_analyst, "/incidents/db_operations/alert/status", {
				method: "PUT",
				body: JSON.stringify({ alert_id: alertId, status })
			})

		expect((await setStatus("PENDING_CUSTOMER")).ok).toBe(true)
		await page.goto(`/incident-management/alerts/${alertId}`)
		await expect(page.getByTestId("item-sla-paused")).toBeVisible({ timeout: 30_000 })
		await expect(page.getByTestId("item-sla-resolve")).toContainText("Waiting on customer")
		const paused = await (await apiAs(seed.scoped_analyst, `/soc_management/items/alert/${alertId}/sla`)).json()
		expect(paused.resolve.state).toBe("paused")

		await page.waitForTimeout(1_100) // a whole second of waiting, so the wait is visible
		expect((await setStatus("IN_PROGRESS")).ok).toBe(true)
		await page.reload()
		await expect(page.getByTestId("item-sla-paused")).toHaveCount(0, { timeout: 30_000 })
		await expect(page.getByTestId("item-sla-waited")).toBeVisible()
	})

	test("puts an alert on hold through its own status switch, and the SLA panel follows", async ({ page }) => {
		const alertId = seed.ids.unacked_open_alert[seed.scoped_customer]
		await apiAs(seed.scoped_analyst, "/incidents/db_operations/alert/status", {
			method: "PUT",
			body: JSON.stringify({ alert_id: alertId, status: "IN_PROGRESS" })
		})
		await page.goto(`/incident-management/alerts/${alertId}`)
		await expect(page.getByTestId("item-sla-alert")).toBeVisible({ timeout: 30_000 })
		await expect(page.getByTestId("item-sla-paused")).toHaveCount(0)

		await page.getByTestId("alert-status-trigger").click()
		await page.locator(".n-base-select-option", { hasText: "Waiting on customer" }).first().click()
		await expect(page.getByTestId("alert-status-trigger")).toContainText("Waiting on customer")

		const stored = await (await apiAs(seed.scoped_analyst, `/incidents/db_operations/alert/${alertId}`)).json()
		expect(stored.alerts[0].status).toBe("PENDING_CUSTOMER")
		await page.reload()
		await expect(page.getByTestId("item-sla-paused")).toBeVisible({ timeout: 30_000 })

		// Leave the seeded alert as the other specs expect it.
		await apiAs(seed.scoped_analyst, "/incidents/db_operations/alert/status", {
			method: "PUT",
			body: JSON.stringify({ alert_id: alertId, status: "IN_PROGRESS" })
		})
	})
})
