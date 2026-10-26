import type { BrowserContext, Page, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { installMockBackend, mintToken, signIn } from "./mock-backend"

/**
 * The customer's Portal Languages tab (#1310): an admin picks the languages the customer's portal
 * users may choose from; English is always on. What is asserted is the payload of each write and what
 * the tab shows back; an analyst sees the setting and cannot change it.
 */

const SUPPORTED = ["en", "it", "de", "fr", "es", "nl", "cs"]

async function installLanguagesMock(context: BrowserContext, role: "admin" | "analyst" = "admin") {
	const writes: unknown[] = []
	const stored = { languages: ["en"], updated_at: null as string | null }
	const json = (route: Route, body: unknown, status = 200) =>
		route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })

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
			if (path === "/customer_portal/languages/settings/ACME") {
				if (method === "PUT") {
					const body = route.request().postDataJSON() as { languages: string[] }
					writes.push(body)
					// The backend refuses a set without English (422), like the real route.
					if (!body.languages.includes("en")) return json(route, { detail: "English is always enabled" }, 422)
					stored.languages = SUPPORTED.filter(code => body.languages.includes(code))
					stored.updated_at = "2026-10-26T08:00:00"
				}
				return json(route, {
					success: true,
					message: "",
					supported: SUPPORTED,
					settings: { customer_code: "ACME", ...stored, updated_by: stored.updated_at ? 1 : null }
				})
			}
			return route.fallback()
		}
	)
	return writes
}

async function openLanguagesTab(page: Page) {
	await page.goto("/customers/ACME")
	await page.locator(".n-tabs-tab", { hasText: /^\s*Portal Languages\s*$/ }).click()
	await expect(page.getByTestId("language-settings-list")).toBeVisible({ timeout: 60_000 })
}

function checkbox(page: Page, code: string) {
	return page.getByTestId(`language-settings-${code}`).locator(".n-checkbox")
}

test.describe("as an admin", () => {
	test("enables Italian for the customer, English staying on", async ({ context, page }) => {
		await installMockBackend(context)
		const writes = await installLanguagesMock(context)
		await signIn(page)

		await openLanguagesTab(page)
		await expect(checkbox(page, "en")).toHaveClass(/n-checkbox--checked/)
		await expect(checkbox(page, "en")).toHaveClass(/n-checkbox--disabled/)
		await expect(page.getByTestId("language-settings-save")).toBeDisabled()

		await checkbox(page, "it").click()
		await expect(page.getByTestId("language-settings-unsaved")).toBeVisible()
		await page.getByTestId("language-settings-save").click()

		await expect.poll(() => writes).toEqual([{ languages: ["en", "it"] }])
		await expect(page.getByTestId("language-settings-unsaved")).toBeHidden()
		await expect(page.getByTestId("language-settings-updated")).toContainText("Last changed")

		// Read back after a reload: the stored set, not the page's memory.
		await page.reload()
		await openLanguagesTab(page)
		await expect(checkbox(page, "it")).toHaveClass(/n-checkbox--checked/)
		await expect(checkbox(page, "de")).not.toHaveClass(/n-checkbox--checked/)

		await checkbox(page, "it").click()
		await page.getByTestId("language-settings-save").click()
		await expect.poll(() => writes.at(-1)).toEqual({ languages: ["en"] })
	})
})

test.describe("as an analyst", () => {
	test("sees the setting but cannot change it", async ({ context, page }) => {
		await installMockBackend(context)
		const writes = await installLanguagesMock(context, "analyst")
		await signIn(page)

		await openLanguagesTab(page)
		await expect(page.getByTestId("language-settings-readonly")).toBeVisible()
		await expect(page.getByTestId("language-settings-save")).toHaveCount(0)
		await expect(checkbox(page, "fr")).toHaveClass(/n-checkbox--disabled/)
		await checkbox(page, "fr").click({ force: true })
		expect(writes).toEqual([])
	})
})
