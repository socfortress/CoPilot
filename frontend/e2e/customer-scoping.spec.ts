import { expect, test } from "@playwright/test"
import { apiAs, signIn, signOut } from "./fixtures/auth"
import { SCOPED_ANALYST, tenants } from "./seed"

/**
 * The bug from #1050, as the reporter saw it: "logged in as analyst with one customer
 * assigned, and I'm still able to see other customer information", with a screenshot
 * of the Customers page listing every tenant.
 *
 * This is that screenshot, taken by a browser. Run it with `pnpm test:e2e:headed` to
 * watch the analyst sign in and find exactly one customer where there are two.
 */

const [TENANT_A, TENANT_B] = tenants()

test.describe("an analyst assigned to one customer", () => {
	test.beforeEach(async ({ page }) => {
		await signOut(page)
		await signIn(page, SCOPED_ANALYST)
	})

	test("sees only the assigned customer on the Customers page", async ({ page }) => {
		await page.goto("/customers")

		// CustomerItem renders `id="customer-<code>"`, so absence here is absence on screen.
		await expect(page.locator(`#customer-${TENANT_A.code}`)).toBeVisible()
		await expect(page.locator(`#customer-${TENANT_B.code}`)).toHaveCount(0)
		await expect(page.getByText(TENANT_B.name)).toHaveCount(0)

		// Naming the other tenant only catches a leak of *that* tenant. The reporter's
		// screenshot was a count — "Total: 3" where one was expected — so assert the
		// count too: it holds however many customers the deployment happens to have.
		await expect(page.locator('[data-testid="customers-total"]')).toHaveText("1")
	})

	test("is offered only the assigned customer in the global filter", async ({ page }) => {
		await page.goto("/customers")

		// The sidebar filter is fed by the same GET /customers, so a leak there would put
		// other tenants one click away even with the list itself scoped.
		await page.locator('[data-testid="global-customer-filter"]').click()

		const dropdown = page.locator(".n-select-menu")
		await expect(dropdown).toBeVisible()
		await expect(dropdown.getByText(TENANT_A.code, { exact: false })).toBeVisible()
		await expect(dropdown.getByText(TENANT_B.code, { exact: false })).toHaveCount(0)
	})

	test("cannot reach another tenant by typing its URL", async ({ page }) => {
		// Hiding a row is not access control if the detail page still renders it.
		await page.goto(`/customers/${TENANT_B.code}`)

		await expect(page.getByText(TENANT_B.name)).toHaveCount(0)
	})

	test("is refused another tenant by the API, not merely by the UI", async () => {
		// What a curious analyst with devtools open would try. The UI hiding a customer
		// is cosmetic; this is the part that actually has to hold. The token is the one
		// beforeEach's sign-in put in the browser.
		const own = await apiAs(SCOPED_ANALYST, `/customers/${TENANT_A.code}`)
		expect(own.status).toBe(200)

		const foreign = await apiAs(SCOPED_ANALYST, `/customers/${TENANT_B.code}`)
		expect(foreign.status).toBe(403)

		const list = await apiAs(SCOPED_ANALYST, "/customers")
		const body = (await list.json()) as { customers: { customer_code: string }[] }
		expect(body.customers.map(c => c.customer_code)).toEqual([TENANT_A.code])
	})

	test("cannot read another tenant's data by object id either", async () => {
		// #1050 guarded routes keyed by `{customer_code}`. A tenant's data is mostly
		// addressed by something it *owns* — these are the keys that scan could not see.
		const foreignSettings = await apiAs(SCOPED_ANALYST, `/api/v1/alert_settings/${encodeURIComponent(TENANT_B.name)}`)
		expect(foreignSettings.status, "alert settings keyed by customer NAME").toBe(403)

		const ghostAgent = await apiAs(SCOPED_ANALYST, "/agent_data_store/agent/e2e-nonexistent-agent/artifacts")
		expect(ghostAgent.status, "an unknown agent id must fail closed, not open").toBe(403)
	})
})
