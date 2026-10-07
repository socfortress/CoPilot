import type { BrowserContext, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { ALERT, ALERT_ID, ASSET, installMockBackend, signIn } from "./mock-backend"
import {
	UBA_ALERT,
	UBA_ALERT_ID,
	UBA_ENTITY,
	UBA_ENTITY_KEY,
	UBA_ENTITY_NAME,
	UBA_RISK_HISTORY,
	UBA_TIMELINE
} from "./uba-fixtures"

/**
 * The UBA alert and entity pages, reached from the CoPilot incident alert UBA raised: its
 * "user behavior" links open the pages (not the /uba drawers), the alert's page leads to its
 * entity's, and browser back retraces the way. What is asserted is the URL each step lands on
 * and the header the page shows for it.
 */

const CUSTOMER = ALERT.customer_code

async function installUbaMock(context: BrowserContext) {
	const json = (route: Route, body: unknown) =>
		route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })

	// Registered after the generic mock, so these run first; anything else falls back to it.
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const path = new URL(route.request().url()).pathname.replace(/^\/api/, "")
			const ubaBase = `/uba/${CUSTOMER}`

			if (path === `/incidents/db_operations/alert/${ALERT_ID}`) {
				return json(route, {
					success: true,
					alerts: [{ ...ALERT, source: "uba", alert_name: `UBA: ${UBA_ENTITY_NAME}` }]
				})
			}
			if (path === `/incidents/db_operations/alert/context/${ASSET.alert_context_id}`) {
				return json(route, {
					success: true,
					alert_context: {
						id: ASSET.alert_context_id,
						source: "uba",
						context: {
							uba_alert_id: UBA_ALERT_ID,
							uba_entity_key: UBA_ENTITY_KEY,
							uba_entity_name: UBA_ENTITY_NAME
						}
					}
				})
			}
			if (path === `${ubaBase}/alerts/${UBA_ALERT_ID}`) return json(route, UBA_ALERT)
			if (path === `${ubaBase}/entity`) return json(route, UBA_ENTITY)
			if (path === `${ubaBase}/entity/risk-history`) return json(route, UBA_RISK_HISTORY)
			if (path === `${ubaBase}/entity/timeline`) return json(route, UBA_TIMELINE)
			return route.fallback()
		}
	)
}

test.describe("UBA alert and entity pages", () => {
	test.beforeEach(async ({ context, page }) => {
		await installMockBackend(context)
		await installUbaMock(context)
		await signIn(page)
	})

	test("the incident alert opens the UBA alert's page, which opens its entity's", async ({ page }) => {
		await page.goto(`/incident-management/alerts/${ALERT_ID}`)

		const alertLink = page.getByTestId("alert-uba-alert-link")
		await expect(alertLink).toHaveAttribute("href", `/uba/${CUSTOMER}/alerts/${UBA_ALERT_ID}`)
		await alertLink.click()

		await expect(page).toHaveURL(new RegExp(`/uba/${CUSTOMER}/alerts/${UBA_ALERT_ID}$`))
		const hero = page.getByTestId("uba-detail-hero")
		await expect(hero.getByTestId("uba-drawer-kind")).toHaveText(/UBA alert/i)
		await expect(hero.getByTestId("uba-drawer-title")).toHaveText(UBA_ENTITY_NAME)
		await expect(page.getByTestId("uba-detail-customer")).toHaveText(CUSTOMER)

		await page.getByTestId("uba-alert-entity").click()
		await expect(page).toHaveURL(new RegExp(`/uba/${CUSTOMER}/entities/${UBA_ENTITY_KEY}$`))
		await expect(hero.getByTestId("uba-drawer-kind")).toHaveText(/Entity/i)
		await expect(hero.getByTestId("uba-drawer-title")).toHaveText(UBA_ENTITY_NAME)

		await page.goBack()
		await expect(page).toHaveURL(new RegExp(`/uba/${CUSTOMER}/alerts/${UBA_ALERT_ID}$`))
		await page.goBack()
		await expect(page).toHaveURL(new RegExp(`/incident-management/alerts/${ALERT_ID}$`))
	})

	test("the entity link goes straight to the entity's page", async ({ page }) => {
		await page.goto(`/incident-management/alerts/${ALERT_ID}`)
		const entityLink = page.getByTestId("alert-uba-entity-link")
		await expect(entityLink).toContainText(UBA_ENTITY_NAME)
		await entityLink.click()

		await expect(page).toHaveURL(new RegExp(`/uba/${CUSTOMER}/entities/${UBA_ENTITY_KEY}$`))
		await expect(page.getByTestId("uba-detail-hero").getByTestId("uba-drawer-title")).toHaveText(UBA_ENTITY_NAME)
	})
})
