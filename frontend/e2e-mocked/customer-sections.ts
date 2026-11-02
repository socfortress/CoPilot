import type { Page } from "@playwright/test"
import { expect } from "@playwright/test"

/**
 * Opens one section of the customer page (#1325) the way an analyst would without knowing its
 * group: from the bar's "Find a section" search. `id` is the section's id, which is the name its
 * tab had before the groups ("Portal Languages", "Healthcheck Wazuh", …).
 */
export async function openCustomerSection(page: Page, id: string) {
	const search = page.getByTestId("sections-search").locator("input")
	await expect(search).toBeVisible({ timeout: 60_000 })
	await search.fill(id)
	await page.getByTestId(`sections-search-option-${id}`).click()
	await expect(page.locator(`[data-section="${id}"]`)).toBeVisible()
}
