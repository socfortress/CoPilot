import process from "node:process"
import { expect, test } from "@playwright/test"
import { apiAs, signIn, signOut } from "./fixtures/auth"
import { tenants } from "./seed"

/**
 * Tenancy work fails in two directions. The specs beside this one check that a scoped
 * analyst is kept out; this one checks nobody locked the admin out of the tenants they
 * administer, which is the failure mode a "just deny everything" fix produces.
 */

const ADMIN_USER = process.env.E2E_ADMIN_USER ?? "admin"
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "admin"

const [TENANT_A, TENANT_B] = tenants()

test.describe("an admin", () => {
	test.beforeEach(async ({ page }) => {
		await signOut(page)
		await signIn(page, ADMIN_USER, ADMIN_PASSWORD)
	})

	test("sees every customer", async ({ page }) => {
		await page.goto("/customers")

		await expect(page.locator(`#customer-${TENANT_A.code}`)).toBeVisible()
		await expect(page.locator(`#customer-${TENANT_B.code}`)).toBeVisible()
	})

	test("reaches every tenant through the API", async () => {
		for (const tenant of [TENANT_A, TENANT_B]) {
			const res = await apiAs(ADMIN_USER, `/customers/${tenant.code}`)
			expect(res.status, `admin reading ${tenant.code}`).toBe(200)
		}
	})

	test("gets no unassigned-scope warning, because deployment-wide is their normal state", async ({ page }) => {
		await page.goto("/customers")
		await expect(page.locator('[data-testid="customers-list"]')).toBeVisible()

		await expect(page.locator('[data-testid="global-filter-unassigned-warning"]')).toHaveCount(0)
	})
})
