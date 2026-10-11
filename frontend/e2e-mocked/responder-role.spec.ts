import type { BrowserContext, Page, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { installMockBackend, mintToken, signIn } from "./mock-backend"

/**
 * The responder role (#1219), against a fixed backend: a responder gets the response
 * pages and tabs an analyst does not (the server enforces it too — this pins what the
 * UI offers), and an admin making someone a responder picks their customers in the
 * same step. What is asserted is what each role is shown and what the browser sends.
 */

type Role = "admin" | "analyst" | "responder"

const SCOPES: Record<Role, string[]> = {
	admin: ["admin"],
	analyst: ["analyst"],
	responder: ["responder", "analyst"]
}

interface Writes {
	roles: unknown[]
}

async function installRoleMock(context: BrowserContext, role: Role): Promise<Writes> {
	const writes: Writes = { roles: [] }
	const json = (route: Route, body: unknown) =>
		route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })

	// Registered after the generic mock, so these run first; anything else falls back to it.
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const path = new URL(route.request().url()).pathname.replace(/^\/api/, "")
			const method = route.request().method()

			if (path === "/auth/token" || path === "/auth/refresh") {
				return json(route, { success: true, access_token: mintToken(role, SCOPES[role]), token_type: "bearer" })
			}
			if (path === "/auth/users") {
				return json(route, {
					success: true,
					message: "",
					users: [
						{ id: 1, username: "admin", email: "admin@x", role_id: 1, role_name: "admin", customer_codes: [] },
						{ id: 4, username: "bob", email: "bob@x", role_id: 4, role_name: "customer_user", customer_codes: [] },
						{ id: 7, username: "legacy", email: "legacy@x", role_id: 2, role_name: "analyst", customer_codes: [] }
					]
				})
			}
			if (path === "/auth/sso/allowed-emails" && method === "GET") {
				return json(route, { success: true, message: "", emails: [] })
			}
			if (path === "/auth/users/4/customers") {
				return json(route, { success: true, customer_codes: [] })
			}
			if (path === "/auth/users/4/role/by-name" && method === "PUT") {
				writes.roles.push(route.request().postDataJSON())
				return json(route, { success: true, message: "Role updated" })
			}
			return route.fallback()
		}
	)
	return writes
}

async function signInAs(context: BrowserContext, page: Page, role: Role) {
	await installMockBackend(context)
	const writes = await installRoleMock(context, role)
	await signIn(page)
	return writes
}

/** Naive's tabs carry no ARIA tab role: find them by their own class. */
function tab(page: Page, name: string) {
	return page.locator(".n-tabs-tab", { hasText: new RegExp(`^\\s*${name}\\s*$`) })
}

async function openRespondMenu(page: Page) {
	await page.goto("/overview")
	await page.getByText("Respond", { exact: true }).first().click()
}

test.describe("a responder", () => {
	test("is offered CoPilot Actions, and the command and quarantine tabs", async ({ context, page }) => {
		await signInAs(context, page, "responder")
		await openRespondMenu(page)
		await expect(page.getByRole("menuitem", { name: "CoPilot Actions" })).toBeVisible()

		await page.goto("/artifacts")
		await expect(tab(page, "Command")).toBeVisible({ timeout: 60_000 })
		await expect(tab(page, "Quarantine")).toBeVisible()
	})

	test("still has no administration", async ({ context, page }) => {
		await signInAs(context, page, "responder")
		await page.goto("/overview")
		await page.getByText("Platform", { exact: true }).first().click()
		await expect(page.getByRole("menuitem", { name: "Audit Log" })).toHaveCount(0)
		await expect(page.getByRole("menuitem", { name: "SSO" })).toHaveCount(0)
	})
})

test.describe("an analyst", () => {
	test("is offered neither", async ({ context, page }) => {
		await signInAs(context, page, "analyst")
		await openRespondMenu(page)
		await expect(page.getByRole("menuitem", { name: "Active Response" })).toBeVisible()
		await expect(page.getByRole("menuitem", { name: "CoPilot Actions" })).toHaveCount(0)

		await page.goto("/artifacts")
		await expect(tab(page, "Collect")).toBeVisible({ timeout: 60_000 })
		await expect(tab(page, "Command")).toHaveCount(0)
		await expect(tab(page, "Quarantine")).toHaveCount(0)
	})
})

test.describe("an admin", () => {
	test("makes a user a responder together with their customers", async ({ context, page }) => {
		const writes = await signInAs(context, page, "admin")
		await page.goto("/users")

		const row = page.locator("tr", { hasText: "bob" })
		await row.getByRole("button").last().click()
		await page.getByRole("button", { name: "Assign Role" }).click()

		await page.getByTestId("assign-role-select").click()
		await page.locator(".n-base-select-option", { hasText: "Responder" }).click()
		const submit = page.getByTestId("assign-role-submit")
		await expect(submit).toBeDisabled()

		await page.getByTestId("user-customers-select").click()
		await page.locator(".n-base-select-option", { hasText: "Acme Corp" }).click()
		await expect(submit).toBeEnabled()
		await submit.click()

		await expect.poll(() => writes.roles).toEqual([{ role_name: "responder", customer_codes: ["ACME"] }])
	})

	test("sees an analyst left without customers flagged, and offers no customers for an admin", async ({
		context,
		page
	}) => {
		await signInAs(context, page, "admin")
		await page.goto("/users")

		await expect(page.locator("tr", { hasText: "legacy" }).getByTestId("user-no-customers")).toBeVisible()
		await expect(page.locator("tr", { hasText: "bob" }).getByTestId("user-no-customers")).toHaveCount(0)

		await page.locator("tr", { hasText: "admin@x" }).getByRole("button").last().click()
		await expect(page.getByRole("button", { name: "Assign Role" })).toBeVisible()
		await expect(page.getByRole("button", { name: "Assign Customer" })).toHaveCount(0)
	})
})
