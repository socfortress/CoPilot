import type { BrowserContext, Page, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { ALERT_ID, installMockBackend, mintToken, signIn } from "./mock-backend"

/**
 * "Ask the SOC" in CoPilot (#1305): the customer's switch and daily limit, and the Customer
 * questions page where the SOC finds what portal users asked. What is asserted is the payload
 * of each write, the query the page sends, and what it shows back.
 */

function json(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })
}

async function installSettingsMock(context: BrowserContext, role: "admin" | "analyst" = "admin") {
	const writes: unknown[] = []
	const stored = { enabled: false, daily_request_limit: null as number | null, updated_at: null as string | null }
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const path = new URL(route.request().url()).pathname.replace(/^\/api/, "")
			if (path === "/auth/token" && role === "analyst") {
				return json(route, { success: true, access_token: mintToken("ana", ["analyst"]), token_type: "bearer" })
			}
			if (path === "/customers/ACME/full") {
				return json(route, {
					success: true,
					customer: { customer_code: "ACME", customer_name: "Acme Corp", contact_first_name: "A", contact_last_name: "B" }
				})
			}
			if (path === "/customer_portal/soc_requests/settings/ACME") {
				if (route.request().method() === "PUT") {
					const body = route.request().postDataJSON() as typeof stored
					writes.push(body)
					Object.assign(stored, body, { updated_at: "2026-10-24T08:00:00" })
				}
				return json(route, { success: true, message: "", settings: { customer_code: "ACME", ...stored, updated_by: 1 } })
			}
			return route.fallback()
		}
	)
	return writes
}

async function openAskTab(page: Page) {
	await page.goto("/customers/ACME")
	await page.locator(".n-tabs-tab", { hasText: /^\s*Ask the SOC\s*$/ }).click()
	await expect(page.getByTestId("ask-soc-settings-switch")).toBeVisible({ timeout: 60_000 })
}

function request(id: number, extra: Record<string, unknown> = {}) {
	return {
		id,
		customer_code: "ACME",
		case_id: null,
		alert_id: null,
		origin_alert_id: null,
		title: null,
		question: "Is this sign-in our VPN?",
		urgency: "normal",
		status: "open",
		requested_by: "jane",
		requested_at: "2026-10-24T07:00:00",
		answered_at: null,
		answered_by: null,
		answered_via: null,
		...extra
	}
}

async function installQuestionsMock(context: BrowserContext) {
	const queries: Record<string, string | string[]>[] = []
	const answered: number[] = []
	const all = [
		request(1, { case_id: 7, title: "Suspicious sign-in", urgency: "high", question: "Was this one of ours?" }),
		request(2, { alert_id: ALERT_ID, title: "Odd process", question: "Should we isolate the host?" }),
		request(3, {
			case_id: 8,
			title: "Phishing",
			status: "answered",
			answered_at: "2026-10-24T07:30:00",
			answered_by: "soc.analyst",
			answered_via: "comment"
		})
	]
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const url = new URL(route.request().url())
			const path = url.pathname.replace(/^\/api/, "")
			if (path === "/customer_portal/soc_requests") {
				const status = url.searchParams.get("status")
				queries.push({ status: status ?? "", customer_codes: url.searchParams.getAll("customer_codes") })
				const rows = all.filter(r => !status || r.status === status)
				return json(route, {
					success: true,
					message: "",
					requests: rows,
					total: all.length,
					open: all.filter(r => r.status === "open").length
				})
			}
			const answer = path.match(/^\/customer_portal\/soc_requests\/(\d+)\/answered$/)
			if (answer && route.request().method() === "POST") {
				const id = Number(answer[1])
				answered.push(id)
				const row = all.find(r => r.id === id)
				if (!row) return route.fulfill({ status: 404 })
				Object.assign(row, { status: "answered", answered_at: "2026-10-24T08:00:00", answered_by: "admin", answered_via: "manual" })
				return json(route, { success: true, message: "", request: row })
			}
			return route.fallback()
		}
	)
	return { queries, answered }
}

test.describe("the customer's Ask the SOC tab", () => {
	test("an admin turns it on and sets a daily limit", async ({ context, page }) => {
		await installMockBackend(context)
		const writes = await installSettingsMock(context)
		await signIn(page)
		await openAskTab(page)
		await expect(page.getByTestId("ask-soc-settings-state")).toContainText("cannot ask the SOC")
		await expect(page.getByTestId("ask-soc-settings-limit")).toHaveCount(0)

		await page.getByTestId("ask-soc-settings-switch").click()
		await expect.poll(() => writes).toEqual([{ enabled: true, daily_request_limit: null }])
		await expect(page.getByTestId("ask-soc-settings-state")).toContainText("can ask the SOC")

		await page.getByTestId("ask-soc-settings-limit-mode").getByText("Limited", { exact: true }).click()
		const value = page.getByTestId("ask-soc-settings-limit-value").locator("input")
		await value.fill("25")
		await value.blur()
		await page.getByTestId("ask-soc-settings-limit-save").click()
		await expect.poll(() => writes.at(-1)).toEqual({ enabled: true, daily_request_limit: 25 })
		await expect(page.getByTestId("ask-soc-settings-limit-save")).toHaveCount(0)
		await expect(page.getByTestId("ask-soc-settings-updated")).toContainText("Last changed")
	})

	test("an analyst sees it but cannot change it", async ({ context, page }) => {
		await installMockBackend(context)
		const writes = await installSettingsMock(context, "analyst")
		await signIn(page)
		await openAskTab(page)
		await expect(page.getByTestId("ask-soc-settings-readonly")).toBeVisible()
		await expect(page.getByTestId("ask-soc-settings-switch")).toHaveClass(/n-switch--disabled/)
		await page.getByTestId("ask-soc-settings-switch").click({ force: true })
		expect(writes).toEqual([])
	})
})

test.describe("Incidents → Customer questions", () => {
	test("lists the open questions, marks one answered and keeps the status in the URL", async ({ context, page }) => {
		await installMockBackend(context)
		const { queries, answered } = await installQuestionsMock(context)
		await signIn(page)

		await page.goto("/incident-management/customer-questions")
		const rows = page.getByTestId("customer-question-row")
		await expect(rows).toHaveCount(2, { timeout: 60_000 })
		await expect(rows.first()).toContainText("Was this one of ours?")
		await expect(rows.first()).toContainText("High")
		await expect(page.getByTestId("customer-questions-status")).toContainText("Open (2)")
		expect(queries.at(-1)).toEqual({ status: "open", customer_codes: [] })

		await rows.first().getByTestId("customer-question-mark").click()
		await expect.poll(() => answered).toEqual([1])
		await expect(rows).toHaveCount(1)
		await expect(page.getByTestId("customer-questions-status")).toContainText("Open (1)")

		await page.getByTestId("customer-questions-status").getByText("Answered").click()
		await expect(page).toHaveURL(/status=answered/)
		await expect(rows).toHaveCount(2)
		await expect(page.getByTestId("customer-question-done").first()).toContainText("admin")
		expect(queries.at(-1)).toEqual({ status: "answered", customer_codes: [] })

		await page.reload()
		await expect(rows).toHaveCount(2, { timeout: 60_000 })
		await page.getByTestId("customer-questions-status").getByText(/^Open/).click()
		await expect(page).not.toHaveURL(/status=/)
	})

	test("opens the alert in a modal whose header leads to its page", async ({ context, page }) => {
		await installMockBackend(context)
		await installQuestionsMock(context)
		await signIn(page)

		await page.goto("/incident-management/customer-questions")
		const target = page.getByTestId("customer-question-target").filter({ hasText: "Odd process" })
		await target.click({ timeout: 60_000 })
		const link = page.locator(".n-modal").getByTestId("modal-page-button")
		await expect(link).toHaveAttribute("href", new RegExp(`/incident-management/alerts/${ALERT_ID}$`))
		await link.click()
		await expect(page).toHaveURL(new RegExp(`/incident-management/alerts/${ALERT_ID}$`))
		await expect(page.locator(".n-modal")).toHaveCount(0)
	})
})
