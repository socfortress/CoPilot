import type { BrowserContext, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { installMockBackend, mintToken, signIn } from "./mock-backend"

/**
 * The customer's AI Report tab (#1215): an admin lets the customer's portal users request
 * AI analyses and sets their daily limit. What is asserted is the payload of each write —
 * only the settings that changed, the read switch sent as it stands — and what the panel
 * shows back.
 */

interface Settings {
	enabled: boolean
	allow_customer_requests: boolean
	daily_request_limit: number | null
}

async function installAiReportMock(context: BrowserContext, role: "admin" | "analyst" = "admin") {
	const writes: unknown[] = []
	const stored: Settings = { enabled: true, allow_customer_requests: false, daily_request_limit: null }
	const json = (route: Route, body: unknown) =>
		route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })

	// Registered after the generic mock, so these run first; anything else falls back to it.
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const path = new URL(route.request().url()).pathname.replace(/^\/api/, "")
			const method = route.request().method()

			if (path === "/auth/token" && role === "analyst") {
				return json(route, { success: true, access_token: mintToken("ana", ["analyst"]), token_type: "bearer" })
			}
			if (path === "/customers/ACME/full") {
				return json(route, {
					success: true,
					customer: { customer_code: "ACME", customer_name: "Acme Corp", contact_first_name: "A", contact_last_name: "B" }
				})
			}
			if (path === "/customer_portal/ai_reports/settings/ACME") {
				if (method === "PUT") {
					const body = route.request().postDataJSON() as Partial<Settings>
					writes.push(body)
					Object.assign(stored, body)
				}
				return json(route, {
					success: true,
					message: "",
					settings: { customer_code: "ACME", ...stored, requests_last_24h: 3, updated_at: null, updated_by: null }
				})
			}
			return route.fallback()
		}
	)
	return writes
}

async function openAiReportTab(page: import("@playwright/test").Page) {
	await page.goto("/customers/ACME")
	await page.locator(".n-tabs-tab", { hasText: /^\s*AI Report\s*$/ }).click()
	await expect(page.getByTestId("ai-requests-switch")).toBeVisible({ timeout: 60_000 })
}

test.describe("as an admin", () => {
	let writes: unknown[]

	test.beforeEach(async ({ context, page }) => {
		await installMockBackend(context)
		writes = await installAiReportMock(context)
		await signIn(page)
	})

	test("lets the customer's portal users request analyses, then limits them", async ({ page }) => {
		await openAiReportTab(page)
		await expect(page.getByTestId("ai-requests-state")).toContainText("Only the SOC and AI Triggers")
		await expect(page.getByTestId("ai-requests-limit")).toHaveCount(0)

		await page.getByTestId("ai-requests-switch").click()
		await expect.poll(() => writes).toEqual([{ enabled: true, allow_customer_requests: true }])
		await expect(page.getByTestId("ai-requests-state")).toContainText("can ask the AI Analyst")
		await expect(page.getByTestId("ai-requests-usage")).toHaveText("3 requests in the last 24 hours, no limit.")

		await page.getByTestId("ai-requests-limit-mode").getByText("Limited", { exact: true }).click()
		const value = page.getByTestId("ai-requests-limit-value").locator("input")
		await value.fill("5")
		await value.blur()
		await page.getByTestId("ai-requests-limit-save").click()
		await expect.poll(() => writes.at(-1)).toEqual({ enabled: true, daily_request_limit: 5 })
		await expect(page.getByTestId("ai-requests-usage")).toHaveText("3 of 5 requests used in the last 24 hours.")
		await expect(page.getByTestId("ai-requests-limit-save")).toHaveCount(0)

		await page.getByTestId("ai-requests-limit-mode").getByText("Unlimited", { exact: true }).click()
		await page.getByTestId("ai-requests-limit-save").click()
		await expect.poll(() => writes.at(-1)).toEqual({ enabled: true, daily_request_limit: null })
	})
})

test.describe("as an analyst", () => {
	test("sees the settings but cannot change them", async ({ context, page }) => {
		await installMockBackend(context)
		const writes = await installAiReportMock(context, "analyst")
		await signIn(page)

		await openAiReportTab(page)
		await expect(page.getByTestId("ai-requests-switch")).toHaveClass(/n-switch--disabled/)
		await page.getByTestId("ai-requests-switch").click({ force: true })
		expect(writes).toEqual([])
	})
})
