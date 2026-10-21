import type { BrowserContext, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { installMockBackend, mintToken, signIn } from "./mock-backend"

/**
 * The customer's Exposure tab (#1289): an admin shows or hides the portal's Exposure page
 * (vulnerabilities and compliance across the customer's agents). What is asserted is the
 * payload of each write and what the tab shows back; an analyst sees the setting and cannot
 * change it.
 */

async function installExposureMock(context: BrowserContext, role: "admin" | "analyst" = "admin") {
	const writes: unknown[] = []
	const stored = { enabled: false, updated_at: null as string | null }
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
			if (path === "/customer_portal/exposure/settings/ACME") {
				if (method === "PUT") {
					const body = route.request().postDataJSON() as { enabled: boolean }
					writes.push(body)
					stored.enabled = body.enabled
					stored.updated_at = "2026-10-21T08:00:00"
				}
				return json(route, {
					success: true,
					message: "",
					settings: { customer_code: "ACME", ...stored, updated_by: stored.updated_at ? 1 : null }
				})
			}
			return route.fallback()
		}
	)
	return writes
}

async function openExposureTab(page: import("@playwright/test").Page) {
	await page.goto("/customers/ACME")
	await page.locator(".n-tabs-tab", { hasText: /^\s*Exposure\s*$/ }).click()
	await expect(page.getByTestId("exposure-settings-switch")).toBeVisible({ timeout: 60_000 })
}

test.describe("as an admin", () => {
	test("turns the portal's Exposure page on and off for the customer", async ({ context, page }) => {
		await installMockBackend(context)
		const writes = await installExposureMock(context)
		await signIn(page)

		await openExposureTab(page)
		await expect(page.getByTestId("exposure-settings-state")).toContainText("one agent at a time")

		await page.getByTestId("exposure-settings-switch").click()
		await expect.poll(() => writes).toEqual([{ enabled: true }])
		await expect(page.getByTestId("exposure-settings-state")).toContainText("across their agents")
		await expect(page.getByTestId("exposure-settings-updated")).toContainText("Last changed")

		await page.getByTestId("exposure-settings-switch").click()
		await expect.poll(() => writes.at(-1)).toEqual({ enabled: false })
	})
})

test.describe("as an analyst", () => {
	test("sees the setting but cannot change it", async ({ context, page }) => {
		await installMockBackend(context)
		const writes = await installExposureMock(context, "analyst")
		await signIn(page)

		await openExposureTab(page)
		await expect(page.getByTestId("exposure-settings-readonly")).toBeVisible()
		await expect(page.getByTestId("exposure-settings-switch")).toHaveClass(/n-switch--disabled/)
		await page.getByTestId("exposure-settings-switch").click({ force: true })
		expect(writes).toEqual([])
	})
})
