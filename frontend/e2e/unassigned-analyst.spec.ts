import { expect, test } from "@playwright/test"
import { signIn, signOut } from "./fixtures/auth"
import { tenants, UNSCOPED_ANALYST } from "./seed"

/**
 * The other half of the rule, and the likeliest explanation for the follow-up report.
 *
 * #1050 deliberately left an analyst with *no* assignments deployment-wide, so that
 * upgrading a deployment does not strip access from every analyst that already exists.
 * From the outside that is indistinguishable from the bug: the analyst sees every
 * customer, and picking one in the sidebar filter looks like an assignment while it is
 * only a view filter.
 *
 * So the behaviour is pinned *and* the warning that explains it is pinned. If someone
 * later decides unassigned should mean "no access", the first test here is the one
 * that has to be changed on purpose.
 */

const [TENANT_A, TENANT_B] = tenants()

test.describe("an analyst with no customer assigned", () => {
	test.beforeEach(async ({ page }) => {
		await signOut(page)
		await signIn(page, UNSCOPED_ANALYST)
	})

	test("still sees every customer — the documented upgrade compromise", async ({ page }) => {
		await page.goto("/customers")

		await expect(page.locator(`#customer-${TENANT_A.code}`)).toBeVisible()
		await expect(page.locator(`#customer-${TENANT_B.code}`)).toBeVisible()
	})

	test("is told why, so it is not mistaken for the bug", async ({ page }) => {
		await page.goto("/customers")

		const warning = page.locator('[data-testid="global-filter-unassigned-warning"]')
		await expect(warning).toBeVisible()

		await warning.hover()
		await expect(page.getByText(/No customer is assigned to your account/i)).toBeVisible()
	})
})
