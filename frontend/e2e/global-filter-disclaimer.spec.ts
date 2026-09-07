import { expect, test } from "@playwright/test"
import { signIn, signOut } from "./fixtures/auth"
import { SCOPED_ANALYST, tenants } from "./seed"

/**
 * The Customers page is the one view that deliberately ignores the sidebar's global
 * customers filter: it lists what the account may *access*, and narrowing it there would
 * hide customers the user is entitled to. That is reasonable and completely invisible,
 * which is how #1050 ended up with a report of "I assigned a customer and the analyst
 * still sees the others" — the reporter's screenshot has a customer picked in the sidebar.
 *
 * So the page says so, but only while a selection exists: a permanent banner is noise,
 * and the question only arises when someone has actually set the filter.
 */

const [TENANT_A] = tenants()

test.describe("the Customers page and the global customers filter", () => {
	test.beforeEach(async ({ page }) => {
		await signOut(page)
		await signIn(page, SCOPED_ANALYST)
		await page.goto("/customers")
		// Wait for the list to settle, so "no disclaimer" cannot be confused with "not rendered yet".
		await expect(page.locator('[data-testid="customers-total"]')).toHaveText("1")
	})

	test("stays quiet while no customer is selected", async ({ page }) => {
		await expect(page.getByText("is not applied here")).toHaveCount(0)
	})

	test("explains itself once a customer is selected, without changing the list", async ({ page }) => {
		await page.locator('[data-testid="global-customer-filter"]').click()
		await page.locator(".n-select-menu .n-base-select-option").first().click()
		await page.keyboard.press("Escape")

		await expect(page.getByText("is not applied here")).toBeVisible()

		// The disclaimer's whole claim is that the filter changes nothing here — assert it
		// rather than trusting the sentence.
		await expect(page.locator('[data-testid="customers-total"]')).toHaveText("1")
		await expect(page.locator(`#customer-${TENANT_A.code}`)).toBeVisible()
	})
})
