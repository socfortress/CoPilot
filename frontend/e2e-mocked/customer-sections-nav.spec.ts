import type { BrowserContext, Page, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { openCustomerSection } from "./customer-sections"
import { installMockBackend, signIn } from "./mock-backend"

/**
 * The customer page's grouped sections (#1325) in a browser: a group's menu previews what each
 * section holds, a section opens from it, the search or a pin, the URL keeps the section, the
 * lights follow a switch flipped in a section, and the page fits a phone.
 */

interface Stored {
	ioc: boolean
	statusReads: number
}

async function installSectionsMock(context: BrowserContext): Promise<Stored> {
	const stored: Stored = { ioc: false, statusReads: 0 }
	const json = (route: Route, body: unknown) =>
		route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })

	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const path = new URL(route.request().url()).pathname.replace(/^\/api/, "")
			const method = route.request().method()

			if (path === "/customers/ACME/full") {
				return json(route, {
					success: true,
					customer: { customer_code: "ACME", customer_name: "Acme Corp", contact_first_name: "A", contact_last_name: "B" }
				})
			}
			if (path === "/customers/ACME/sections/status") {
				stored.statusReads += 1
				return json(route, {
					success: true,
					message: "",
					customer_code: "ACME",
					sections: {
						integrations: { count: 2 },
						network_connectors: { count: 0 },
						event_sources: { count: 3 },
						waf: { count: 1 },
						knowledge: { count: 0 },
						ai_triggers: { on: true },
						notification_workflows: { count: 0 },
						notification_routes: { count: 2 },
						portal_branding: { on: false },
						portal_languages: { on: false, count: 1 },
						portal_sla: { on: true },
						portal_activity: { on: true },
						portal_exposure: { on: false },
						portal_audit: { on: false },
						portal_ai_report: { on: true },
						portal_talon_chat: { on: false },
						portal_ask_soc: { on: false },
						portal_ioc_enrichment: { on: stored.ioc },
						portal_notifications: { on: false }
					}
				})
			}
			if (path === "/customer_portal/ioc_enrichment/settings/ACME") {
				if (method === "PUT") stored.ioc = (route.request().postDataJSON() as { enabled: boolean }).enabled
				return json(route, {
					success: true,
					message: "",
					settings: { customer_code: "ACME", enabled: stored.ioc, daily_lookup_limit: null, updated_at: null, updated_by: null },
					connectors: { virustotal: true, opencti: false },
					cache_hours: 24
				})
			}
			return route.fallback()
		}
	)
	return stored
}

async function openCustomer(page: Page, query = "") {
	await page.goto(`/customers/ACME${query}`)
	await expect(page.getByTestId("customer-sections-bar")).toBeVisible({ timeout: 60_000 })
}

function railItem(page: Page, id: string) {
	return page.getByTestId(`rail-item-${id}`)
}

test.describe("the customer's sections", () => {
	test("a group's menu previews each section's state, and opens one into the URL", async ({ context, page }) => {
		await installMockBackend(context)
		await installSectionsMock(context)
		await signIn(page)
		await openCustomer(page)

		await page.getByTestId("section-group-portal").hover()
		const menu = page.getByTestId("section-menu-portal")
		await expect(menu).toBeVisible()
		await expect(menu).toContainText("3 of 11 on")
		await expect(menu.getByTestId("section-menu-item-Portal Languages")).toContainText("English only")
		await expect(menu.getByTestId("section-menu-item-AI Report")).toContainText("On")
		await expect(menu.getByTestId("section-menu-item-Talon Chat")).toContainText("Off")
		await expect(menu.getByTestId("section-menu-item-Exposure")).toContainText("Off")

		await menu.getByTestId("section-menu-item-Exposure").click()
		await expect(page).toHaveURL(/tab=Exposure/)
		await expect(page.locator('[data-section="Exposure"]')).toBeVisible()
		await expect(page.getByTestId("customer-sections-rail")).toHaveAttribute("aria-label", "Customer Portal sections")
		await expect(page.getByTestId("section-toolbar")).toContainText("Off")

		// The URL opens it again after a reload.
		await page.reload()
		await expect(page.locator('[data-section="Exposure"]')).toBeVisible({ timeout: 60_000 })
	})

	test("the keyboard opens a group's menu and moves through it", async ({ context, page }) => {
		await installMockBackend(context)
		await installSectionsMock(context)
		await signIn(page)
		await openCustomer(page)

		await page.getByTestId("section-group-data").focus()
		await page.keyboard.press("ArrowDown")
		await expect(page.getByTestId("section-menu-item-3rd Party Integrations")).toBeFocused()
		await page.keyboard.press("ArrowDown")
		await expect(page.getByTestId("section-menu-item-Network Connectors")).toBeFocused()
		await page.keyboard.press("Escape")
		await expect(page.getByTestId("section-group-data")).toBeFocused()
	})

	test("'/' finds a section by what it does, and a pin brings it back on every visit", async ({ context, page }) => {
		await installMockBackend(context)
		await installSectionsMock(context)
		await signIn(page)
		await openCustomer(page)

		await page.locator("body").click()
		await page.keyboard.press("/")
		await page.keyboard.type("virustotal")
		await page.getByTestId("sections-search-option-IOC Enrichment").click()
		await expect(page.locator('[data-section="IOC Enrichment"]')).toBeVisible()

		await page.getByTestId("section-pin").click()
		await expect(page.getByTestId("section-pin")).toHaveAttribute("aria-pressed", "true")

		await openCustomer(page)
		await page.getByTestId("sections-pinned").click()
		await page.getByTestId("sections-pinned-item-IOC Enrichment").click()
		await expect(page.locator('[data-section="IOC Enrichment"]')).toBeVisible()
	})

	test("a switch flipped in a section lights up once the viewer moves on", async ({ context, page }) => {
		await installMockBackend(context)
		const stored = await installSectionsMock(context)
		await signIn(page)
		await openCustomer(page, "?tab=IOC Enrichment")

		await expect(railItem(page, "IOC Enrichment").locator(".section-led")).not.toHaveClass(/is-on/)
		const reads = stored.statusReads
		await page.getByTestId("ioc-enrichment-settings-switch").click()
		await expect.poll(() => stored.ioc).toBe(true)

		await railItem(page, "SLA").click()
		await expect.poll(() => stored.statusReads).toBeGreaterThan(reads)
		await expect(railItem(page, "IOC Enrichment").locator(".section-led")).toHaveClass(/is-on/)
	})

	test("where the groups don't fit on one line they wrap, whole, and a search result's name is never cut", async ({
		context,
		page
	}) => {
		await page.setViewportSize({ width: 1000, height: 760 })
		await installMockBackend(context)
		await installSectionsMock(context)
		await signIn(page)
		await openCustomer(page)

		const bar = page.getByTestId("customer-sections-bar")
		const barBox = await bar.boundingBox()
		for (const group of ["overview", "agents", "data", "automation", "reports", "portal"]) {
			const box = await page.getByTestId(`section-group-${group}`).boundingBox()
			expect(box, group).not.toBeNull()
			expect(box && barBox && box.x >= barBox.x && box.x + box.width <= barBox.x + barBox.width, group).toBe(true)
		}

		await page.getByTestId("sections-search").locator("input").fill("notif")
		const option = page.getByTestId("sections-search-option-Notification Workflows")
		await expect(option).toBeVisible()
		const name = option.locator("span").first()
		const cut = await name.evaluate(el => el.scrollWidth > el.clientWidth)
		expect(cut).toBe(false)
		await expect(name).toHaveText("Notification Workflows")
	})

	test("on a 360 px phone the sections sit on top and nothing scrolls sideways", async ({ context, page }) => {
		await page.setViewportSize({ width: 360, height: 760 })
		await installMockBackend(context)
		await installSectionsMock(context)
		await signIn(page)
		await openCustomer(page)

		await openCustomerSection(page, "Event Sources")
		const rail = page.getByTestId("customer-sections-rail")
		await expect(rail).toBeVisible()
		await expect(railItem(page, "WAF")).toBeVisible()
		const railBox = await rail.boundingBox()
		const paneBox = await page.locator('[data-section="Event Sources"]').boundingBox()
		expect(railBox && paneBox && railBox.y < paneBox.y).toBe(true)
		const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
		expect(overflow).toBeLessThanOrEqual(0)
	})
})
