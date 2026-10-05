import type { BrowserContext, Page, Route } from "@playwright/test"
import type { ItemSla } from "../src/types/soc-management"
import { expect, test } from "@playwright/test"
import { ALERT_ID, installMockBackend, mintToken, signIn } from "./mock-backend"

/**
 * The SLA surfaces outside the SOC Management page (#1187), against a fixed backend:
 * putting an alert on hold for the customer, the customer's portal SLA switch, and an
 * internal notification route on an SLA trigger. What is asserted is what the browser
 * sends — the payload of each write — and what it shows back.
 */

interface Writes {
	alertStatus: unknown[]
	slaSwitch: unknown[]
	routes: unknown[]
}

function itemSla(paused: boolean): ItemSla {
	return {
		entity: "alert",
		id: ALERT_ID,
		severity: "High",
		opened_at: "2026-09-08T10:00:00",
		tracked: true,
		ack: { due_at: "2026-09-08T11:00:00", achieved_at: "2026-09-08T10:05:00", state: "met", by: "admin", action: "status_changed", target_minutes: 60 },
		resolve: { due_at: "2026-09-08T18:00:00", achieved_at: null, state: paused ? "paused" : "on_track", by: null, action: null, target_minutes: 480 },
		first_assigned_at: null,
		reopen_count: 0,
		business_hours: false,
		calendar_timezone: null,
		paused_at: paused ? "2026-09-08T10:05:00" : null,
		paused_seconds: 0,
		generated_at: "2026-09-08T10:30:00"
	}
}

async function installSlaMock(context: BrowserContext, role: "admin" | "analyst" = "admin"): Promise<Writes> {
	const writes: Writes = { alertStatus: [], slaSwitch: [], routes: [] }
	let paused = false
	let slaEnabled = false
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
			if (path === "/incidents/db_operations/alert/status" && method === "PUT") {
				const body = route.request().postDataJSON() as { status: string }
				writes.alertStatus.push(body)
				paused = body.status === "PENDING_CUSTOMER"
				return json(route, { success: true, message: "Alert status updated successfully", alert: {} })
			}
			if (path === `/soc_management/items/alert/${ALERT_ID}/sla`) {
				return json(route, { success: true, message: "", ...itemSla(paused) })
			}
			if (path === "/customers/ACME/full") {
				return json(route, {
					success: true,
					customer: { customer_code: "ACME", customer_name: "Acme Corp", contact_first_name: "A", contact_last_name: "B" }
				})
			}
			if (path === "/customer_portal/sla/settings/ACME") {
				if (method === "PUT") {
					const body = route.request().postDataJSON() as { enabled: boolean }
					writes.slaSwitch.push(body)
					slaEnabled = body.enabled
				}
				return json(route, {
					success: true,
					message: "",
					settings: { customer_code: "ACME", enabled: slaEnabled, updated_at: null, updated_by: null }
				})
			}
			if (path === "/notification_channels") {
				return json(route, {
					success: true,
					channels: [
						{
							key: "resend",
							display_name: "Email (Resend)",
							supports_recipient_modes: ["static", "assignee"],
							supports_internal_scope: true,
							config_schema: {}
						}
					]
				})
			}
			if (path === "/notifications/templates") {
				return json(route, { success: true, message: "", templates: [] })
			}
			if (path === "/internal_notification_routes" && method === "POST") {
				writes.routes.push(route.request().postDataJSON())
				return json(route, { success: true, message: "Internal route created", route: { id: 1 } })
			}
			if (path === "/internal_notification_routes") {
				return json(route, { success: true, message: "", routes: [] })
			}
			return route.fallback()
		}
	)
	return writes
}

async function pick(page: Page, option: string) {
	await page.locator(".n-base-select-option", { hasText: option }).first().click()
}

test.describe("as an admin", () => {
	let writes: Writes

	test.beforeEach(async ({ context, page }) => {
		await installMockBackend(context)
		writes = await installSlaMock(context)
		await signIn(page)
	})

	test("puts an alert on hold for the customer, and its SLA panel says the clocks stopped", async ({ page }) => {
		await page.goto(`/incident-management/alerts/${ALERT_ID}`)
		await expect(page.getByTestId("item-sla-alert")).toBeVisible({ timeout: 60_000 })
		await expect(page.getByTestId("item-sla-paused")).toHaveCount(0)

		await page.getByTestId("alert-status-trigger").click()
		await expect(page.getByTestId("pending-customer-help")).toBeVisible()
		await pick(page, "Waiting on customer")

		await expect.poll(() => writes.alertStatus).toEqual([{ alert_id: ALERT_ID, status: "PENDING_CUSTOMER" }])
		await expect(page.getByTestId("alert-status-trigger")).toContainText("Waiting on customer")
		await expect(page.getByTestId("item-sla-paused")).toBeVisible()
		await expect(page.getByTestId("item-sla-resolve")).toContainText("stopped")
	})

	test("publishes the SLA page to a customer from the customer's SLA tab", async ({ page }) => {
		await page.goto("/customers/ACME")
		await page.locator(".n-tabs-tab", { hasText: /^\s*SLA\s*$/ }).click()
		const toggle = page.getByTestId("sla-settings-switch")
		await expect(toggle).toBeVisible({ timeout: 60_000 })
		await expect(page.getByTestId("sla-settings-state")).toContainText("SLA figures stay internal")

		await toggle.click()
		await expect.poll(() => writes.slaSwitch).toEqual([{ enabled: true }])
		await expect(page.getByTestId("sla-settings-state")).toContainText("can see their SLA targets")
	})

	test("creates an internal route that emails the assignee when an SLA is breached", async ({ page }) => {
		await page.goto("/internal-notifications/new")
		const form = page.locator(".n-form")
		await expect(form).toBeVisible({ timeout: 60_000 })
		await form.locator(".n-form-item", { hasText: "Name" }).locator("input").first().fill("SLA breaches to the assignee")

		await form.locator(".n-form-item", { hasText: "Trigger" }).locator(".n-base-selection").first().click()
		await pick(page, "An alert or case SLA is breached")
		await form.locator(".n-form-item", { hasText: "Minimum severity" }).locator(".n-base-selection").first().click()
		await pick(page, "Informational")
		await form.locator(".n-form-item", { hasText: "Deliver to" }).locator(".n-base-selection").first().click()
		await pick(page, "Whoever it's assigned to")

		await page.getByRole("button", { name: "Create route" }).click()
		await expect.poll(() => writes.routes.length).toBe(1)
		expect(writes.routes[0]).toMatchObject({
			name: "SLA breaches to the assignee",
			trigger: "sla_breached",
			scope: "internal",
			channel: "resend",
			recipient_mode: "assignee",
			min_severity: "Informational"
		})
	})
})

test.describe("as an analyst", () => {
	test("sees a customer's SLA switch but cannot flip it", async ({ context, page }) => {
		await installMockBackend(context)
		const writes = await installSlaMock(context, "analyst")
		await signIn(page)
		await page.goto("/customers/ACME")
		await page.locator(".n-tabs-tab", { hasText: /^\s*SLA\s*$/ }).click()
		await expect(page.getByTestId("sla-settings-readonly")).toBeVisible({ timeout: 60_000 })
		await expect(page.getByTestId("sla-settings-switch")).toHaveClass(/n-switch--disabled/)
		await page.getByTestId("sla-settings-switch").click({ force: true })
		expect(writes.slaSwitch).toEqual([])
	})
})
