import type { BrowserContext, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { installMockBackend, mintToken, signIn } from "./mock-backend"

/**
 * The customer's IOC Enrichment tab (#1318): an admin lets the customer's portal users check
 * their alerts' IOCs against Threat Intel, with an optional daily limit. What is asserted is the
 * payload of each write and what the tab shows back (the connectors' state included); an analyst
 * sees the setting and cannot change it.
 */

async function installIocEnrichmentMock(
	context: BrowserContext,
	{ role = "admin", opencti = false }: { role?: "admin" | "analyst"; opencti?: boolean } = {}
) {
	const writes: unknown[] = []
	const stored = { enabled: false, daily_lookup_limit: null as number | null, updated_at: null as string | null }
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
			if (path === "/customer_portal/ioc_enrichment/settings/ACME") {
				if (method === "PUT") {
					const body = route.request().postDataJSON() as { enabled: boolean; daily_lookup_limit: number | null }
					writes.push(body)
					Object.assign(stored, body, { updated_at: "2026-10-28T08:00:00" })
				}
				return json(route, {
					success: true,
					message: "",
					settings: { customer_code: "ACME", ...stored, updated_by: stored.updated_at ? 1 : null },
					connectors: { virustotal: true, opencti },
					cache_hours: 24
				})
			}
			return route.fallback()
		}
	)
	return writes
}

async function openTab(page: import("@playwright/test").Page) {
	await page.goto("/customers/ACME")
	await page.locator(".n-tabs-tab", { hasText: /^\s*IOC Enrichment\s*$/ }).click()
	await expect(page.getByTestId("ioc-enrichment-settings-switch")).toBeVisible({ timeout: 60_000 })
}

test.describe("as an admin", () => {
	test("turns IOC checks on, sets a daily limit and turns them off", async ({ context, page }) => {
		await installMockBackend(context)
		const writes = await installIocEnrichmentMock(context)
		await signIn(page)

		await openTab(page)
		await expect(page.getByTestId("ioc-enrichment-settings-state")).toContainText("cannot check IOCs")
		await expect(page.getByTestId("ioc-enrichment-settings-source-virustotal")).toContainText("connector verified")
		await expect(page.getByTestId("ioc-enrichment-settings-source-opencti")).toContainText("not verified")

		await page.getByTestId("ioc-enrichment-settings-switch").click()
		await expect.poll(() => writes).toEqual([{ enabled: true, daily_lookup_limit: null }])
		await expect(page.getByTestId("ioc-enrichment-settings-state")).toContainText("can check the IOCs")
		await expect(page.getByTestId("ioc-enrichment-settings-updated")).toContainText("Last changed")

		await page.getByTestId("ioc-enrichment-settings-limit-mode").getByText("Limited", { exact: true }).click()
		const limit = page.getByTestId("ioc-enrichment-settings-limit-value").locator("input")
		await limit.fill("250")
		await limit.blur()
		await page.getByTestId("ioc-enrichment-settings-limit-save").click()
		await expect.poll(() => writes.at(-1)).toEqual({ enabled: true, daily_lookup_limit: 250 })
		await expect(page.getByTestId("ioc-enrichment-settings-limit-save")).toBeHidden()

		await page.getByTestId("ioc-enrichment-settings-switch").click()
		await expect.poll(() => writes.at(-1)).toEqual({ enabled: false, daily_lookup_limit: 250 })
		await expect(page.getByTestId("ioc-enrichment-settings-limit")).toBeHidden()
	})
})

test.describe("as an analyst", () => {
	test("sees the setting but cannot change it", async ({ context, page }) => {
		await installMockBackend(context)
		const writes = await installIocEnrichmentMock(context, { role: "analyst", opencti: true })
		await signIn(page)

		await openTab(page)
		await expect(page.getByTestId("ioc-enrichment-settings-readonly")).toBeVisible()
		await expect(page.getByTestId("ioc-enrichment-settings-switch")).toHaveClass(/n-switch--disabled/)
		await page.getByTestId("ioc-enrichment-settings-switch").click({ force: true })
		expect(writes).toEqual([])
	})
})
