import type { Page } from "@playwright/test"
import { expect, test } from "@playwright/test"
import {
	ALERT_ID,
	ASSET,
	EXPECTED_SOURCE_NAME,
	FALLBACK_SOURCE_NAME,
	installMockBackend,
	signIn,
	sourceOptionLabel
} from "./mock-backend"

/**
 * Regression cover for #1124 — "Automatically select Source in Event Search".
 *
 * The flow from the issue: Incident Management → Alerts → View an alert → Assets →
 * View the asset → under `alert_linked`, "View in Event Search". Event Search opens
 * with the right query, but the analyst still has to pick the Source by hand before any
 * event comes back.
 *
 * The asset page is reachable by its own route (`alerts/:alertId/assets/:assetId`), so
 * these specs start there rather than clicking down from the list — the defect is in the
 * link that page renders, and the three steps above it only decide which asset is on
 * screen.
 *
 * Fixed by having the link carry `index_name` — the only handle an alert has on its
 * source — and letting `EventSearchFilters.applyRouteParams()` resolve it against the
 * source list it already loads. These specs pin the behaviour end to end; the resolver
 * itself is unit-tested in `src/components/events/__tests__/eventSearch.helpers.spec.ts`.
 */

const ASSET_PATH = `/incident-management/alerts/${ALERT_ID}/assets/${ASSET.id}`

test.beforeEach(async ({ context, page }) => {
	await installMockBackend(context)
	await signIn(page)
})

/** Opens the asset page and clicks the link, returning the popup it spawns. */
async function openEventSearchFromAsset(page: Page) {
	await page.goto(ASSET_PATH)

	const link = page.getByText("View in Event Search", { exact: false })
	await expect(link).toBeVisible()

	const popupPromise = page.context().waitForEvent("page")
	await link.click()
	const popup = await popupPromise
	await popup.waitForLoadState("domcontentloaded")

	return popup
}

test("the Event Search link carries the alert's query", async ({ page }) => {
	// The half that works today. Here so a regression in the query is told apart from
	// the missing source rather than being reported as the same failure.
	const popup = await openEventSearchFromAsset(page)
	const url = new URL(popup.url())

	expect(url.pathname).toBe("/event-search")
	expect(url.searchParams.get("customer_code")).toBe(ASSET.customer_code)
	expect(url.searchParams.get("query")).toBe(`alert_id:"${ASSET.alert_linked}"`)
})

test("#1124 — the link identifies the source the alert came from", async ({ page }) => {
	const popup = await openEventSearchFromAsset(page)
	const url = new URL(popup.url())

	// Either shape would let Event Search resolve the source: its name outright, or the
	// index the alert was read from (which matches exactly one source's index_pattern).
	// The assertion accepts both so it pins the behaviour, not one particular fix.
	const identifiesSource =
		url.searchParams.get("source_name") === EXPECTED_SOURCE_NAME ||
		url.searchParams.get("index_name") === ASSET.index_name

	expect(
		identifiesSource,
		`"View in Event Search" opened ${url.pathname}${url.search} — it names the customer and the query but ` +
			`nothing that identifies "${EXPECTED_SOURCE_NAME}", the source behind index "${ASSET.index_name}".`
	).toBe(true)
})

/**
 * What the filter bar currently shows as selected.
 *
 * naive-ui puts a single select's displayed value in the wrapper's `title`, which is the
 * only stable handle on that for a filterable select — the visible text lives in an
 * overlay that swaps out while the menu is open.
 */
function selectedFilters(page: Page) {
	return () =>
		page.locator(".n-base-selection-label[title]").evaluateAll(nodes => nodes.map(n => n.getAttribute("title") ?? ""))
}

test("#1124 — Event Search opens on the alert's own source", async ({ page }) => {
	// The symptom the analyst actually reports, asserted on the page rather than on the
	// link — whatever shape a fix gives the URL, this is what has to end up on screen.
	const popup = await openEventSearchFromAsset(page)
	const selected = selectedFilters(popup)

	// Wait for the customer to land first, so what follows describes a settled filter bar
	// rather than one still loading its sources.
	await expect.poll(selected).toContain(`#${ASSET.customer_code} - Acme Corp`)

	await expect
		.poll(selected, {
			message:
				`Event Search opened with the wrong Source. The alert was read from index ` +
				`"${ASSET.index_name}", which belongs to "${EXPECTED_SOURCE_NAME}", but the link carries no ` +
				`source — so the filter bar falls back to the first enabled EDR source ` +
				`("${FALLBACK_SOURCE_NAME}") and the analyst has to change it by hand before any event comes back.`
		})
		.toContain(sourceOptionLabel(EXPECTED_SOURCE_NAME))
})

test("an index no source claims still falls back to the first enabled EDR source", async ({ page }) => {
	// The pre-#1124 default, kept. An unrecognised index is not a reason to strand the
	// analyst on an empty Source — it is the case the fallback was written for.
	await page.goto(`/event-search?customer_code=${ASSET.customer_code}&index_name=crowdstrike-acme-2026.09.08`)
	const selected = selectedFilters(page)

	await expect.poll(selected).toContain(`#${ASSET.customer_code} - Acme Corp`)
	await expect.poll(selected).toContain(sourceOptionLabel(FALLBACK_SOURCE_NAME))
})

test("an explicit source_name wins over the index", async ({ page }) => {
	// `source_name` is what the `/event-search/:customerCode/:sourceName` routes send, and
	// a caller that names a source outright must not have it second-guessed by an index.
	const url =
		`/event-search?customer_code=${ASSET.customer_code}` +
		`&source_name=${encodeURIComponent(EXPECTED_SOURCE_NAME)}&index_name=wazuh-alerts-2026.09.08`

	await page.goto(url)
	const selected = selectedFilters(page)

	await expect.poll(selected).toContain(`#${ASSET.customer_code} - Acme Corp`)
	await expect.poll(selected).toContain(sourceOptionLabel(EXPECTED_SOURCE_NAME))
})
