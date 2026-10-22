import type { BrowserContext, Page, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { installMockBackend, signIn } from "./mock-backend"

/**
 * The customer's Security tab (#1296): a SOC admin makes a portal user a customer admin (who then
 * manages the customer's portal users from the portal), and disables and enables an account.
 * What is asserted is each request sent, only once confirmed, and the list read back after it.
 */

interface SecurityUser {
	id: number
	username: string
	email: string
	role_name: string
	last_login_at: null
	totp_enabled: boolean
	must_change_password: boolean
	is_customer_admin: boolean
	disabled_at: string | null
}

function portalUser(id: number, username: string): SecurityUser {
	return {
		id,
		username,
		email: `${username}@acme.example`,
		role_name: "customer_user",
		last_login_at: null,
		totp_enabled: false,
		must_change_password: false,
		is_customer_admin: false,
		disabled_at: null
	}
}

async function installSecurityMock(context: BrowserContext) {
	const writes: string[] = []
	const users = [portalUser(1, "jane"), { ...portalUser(2, "ana"), role_name: "analyst" }]
	const json = (route: Route, body: unknown) =>
		route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })

	// Registered after the generic mock, so these run first; anything else falls back to it.
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const path = new URL(route.request().url()).pathname.replace(/^\/api/, "")
			const method = route.request().method()

			if (path === "/customers/ACME/full") {
				return json(route, {
					success: true,
					customer: {
						customer_code: "ACME",
						customer_name: "Acme Corp",
						contact_first_name: "A",
						contact_last_name: "B"
					}
				})
			}
			if (path === "/auth/security/customers/ACME/users") {
				return json(route, { success: true, message: "", users })
			}
			if (path === "/auth/security/smtp-status") {
				return json(route, { success: true, message: "", configured: true })
			}
			const appoint = path.match(/^\/auth\/security\/customers\/ACME\/users\/(\d+)\/customer-admin$/)
			if (appoint && method === "PUT") {
				const body = route.request().postDataJSON() as { is_customer_admin: boolean }
				writes.push(`admin ${appoint[1]} ${body.is_customer_admin}`)
				const target = users.find(u => u.id === Number(appoint[1]))
				if (target) target.is_customer_admin = body.is_customer_admin
				return json(route, { success: true, message: "Updated" })
			}
			const toggle = path.match(/^\/auth\/security\/users\/(\d+)\/(disable|enable)$/)
			if (toggle && method === "POST") {
				writes.push(`${toggle[2]} ${toggle[1]}`)
				const target = users.find(u => u.id === Number(toggle[1]))
				if (target) target.disabled_at = toggle[2] === "disable" ? "2026-10-22T09:00:00" : null
				return json(route, { success: true, message: "Updated" })
			}
			return route.fallback()
		}
	)
	return writes
}

/** Pick an action from the Actions menu of the account's row. */
async function act(page: Page, username: string, action: string | RegExp) {
	await page.locator(`[data-testid=security-row][data-user="${username}"]`).getByTestId("security-actions").click()
	await page.locator(".n-dropdown-option", { hasText: action }).click()
}

test.describe("customer admins and disabled accounts", () => {
	let writes: string[]

	test.beforeEach(async ({ context, page }) => {
		await installMockBackend(context)
		writes = await installSecurityMock(context)
		await signIn(page)
		await page.goto("/customers/ACME")
		await page.locator(".n-tabs-tab", { hasText: /^\s*Security\s*$/ }).click()
		await expect(page.getByTestId("security-actions").first()).toBeVisible({ timeout: 60_000 })
	})

	test("an admin appoints a customer admin once confirmed, and sees it", async ({ page }) => {
		// Only the portal user's menu has the account actions: a SOC user is never one.
		const portalUser = (await page.getByTestId("security-row").first().getAttribute("data-user")) ?? ""
		await act(page, portalUser, "Make customer admin")
		expect(writes).toEqual([])
		await page.locator(".n-dialog").getByRole("button", { name: "Make customer admin" }).click()
		await expect.poll(() => writes).toEqual(["admin 1 true"])
		await expect(page.getByTestId("security-customer-admin")).toHaveText("Customer admin")
		await page.locator(`[data-testid=security-row][data-user="${portalUser}"]`).getByTestId("security-actions").click()
		await expect(page.locator(".n-dropdown-option", { hasText: "Remove customer admin" })).toBeVisible()
	})

	test("an admin disables an account once confirmed, and enables it again", async ({ page }) => {
		const portalUser = (await page.getByTestId("security-row").first().getAttribute("data-user")) ?? ""
		await act(page, portalUser, "Disable account")
		await page.locator(".n-dialog").getByRole("button", { name: "Cancel" }).click()
		expect(writes).toEqual([])

		await act(page, portalUser, "Disable account")
		await page.locator(".n-dialog").getByRole("button", { name: "Disable" }).click()
		await expect.poll(() => writes).toEqual(["disable 1"])
		await expect(page.getByTestId("security-disabled")).toHaveText("Disabled")

		await act(page, portalUser, "Enable account")
		await expect.poll(() => writes).toEqual(["disable 1", "enable 1"])
		await expect(page.getByTestId("security-disabled")).toHaveCount(0)
	})
})
