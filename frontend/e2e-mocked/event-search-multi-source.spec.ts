import type { Page, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { EVENT_SOURCES, installMockBackend, selectedFilters, signIn, sourceOptionLabel } from "./mock-backend"

/**
 * Event Search across several sources at once (#1356).
 *
 * An analyst correlating one IP across a firewall and a router used to search each source
 * in turn. The source picker now takes up to five of the customer's sources; one search
 * covers them, newest first, and each event says which source it came from. These specs
 * pin what the browser does with that: what it sends, how the results read, and what it
 * refuses or warns about before anything is sent.
 *
 * The backend's side (the sources' shared time field, the token bound to the set of
 * sources, the per-event source) is pinned in `backend/tests/test_event_search_multi_source.py`.
 * `E2E_SHOTS=<dir>` saves a screenshot of each state, to look at the layout.
 */

const CUSTOMER = "ACME"
const WAZUH = "Wazuh EDR"
const OFFICE = "Office 365 Audit"
const CLOUD = "Cloud Logs"

/** A third source whose time field differs from the other two: it can't be searched with them. */
const SOURCES = [
	...EVENT_SOURCES,
	{
		...EVENT_SOURCES[1],
		id: 3,
		name: CLOUD,
		index_pattern: "cloud-acme-*",
		time_field: "@timestamp"
	}
]

const FIRST_PAGE = [
	{
		_id: "w1",
		_index: "wazuh-alerts-4.x-2026.11.20",
		_source_name: WAZUH,
		timestamp: "2026-11-20T10:00:00Z",
		agent_name: "WIN-DC01",
		rule_description: "Logon failure",
		rule_level: 5,
		src_ip: "10.0.0.5"
	},
	{
		_id: "o1",
		_index: "office365-acme-2026.11.20",
		_source_name: OFFICE,
		timestamp: "2026-11-20T09:58:00Z",
		rule_description: "Mailbox login",
		src_ip: "10.0.0.5"
	}
]

const SECOND_PAGE = [
	{
		_id: "w2",
		_index: "wazuh-alerts-4.x-2026.11.20",
		_source_name: WAZUH,
		timestamp: "2026-11-20T09:57:00Z",
		agent_name: "WIN-DC01",
		rule_description: "Logon failure",
		rule_level: 5
	}
]

interface Sent {
	path: string
	body: Record<string, unknown>
}

function json(route: Route, body: unknown, status = 200) {
	return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })
}

/** The customer's sources, and the two routes that read several of them together. */
async function installMultiSourceRoutes(page: Page): Promise<Sent[]> {
	const sent: Sent[] = []

	await page.context().route(
		url => url.pathname === `/api/siem/event_sources/${CUSTOMER}`,
		route => json(route, { success: true, event_sources: SOURCES })
	)

	await page.context().route(
		url => url.pathname === `/api/siem/events/${CUSTOMER}/search` || url.pathname === `/api/siem/events/${CUSTOMER}/fields`,
		async route => {
			const request = route.request()
			// A GET here is the single-source route of a source called "search".
			if (request.method() !== "POST") return route.fallback()

			const path = new URL(request.url()).pathname.replace(/^\/api/, "")
			const body = request.postDataJSON() as Record<string, unknown>
			sent.push({ path, body })

			if (path.endsWith("/fields")) {
				return json(route, {
					success: true,
					fields: [
						{ field: "src_ip", type: "ip, keyword", conflict: true },
						{ field: "user_id", type: "keyword", conflict: false }
					],
					total: 2,
					index_pattern: "wazuh-alerts-*,office365-acme-*"
				})
			}
			if (body.scroll_id) {
				return json(route, { success: true, events: SECOND_PAGE, total: 3, scroll_id: null, page_size: 1, warnings: [] })
			}
			return json(route, {
				success: true,
				events: FIRST_PAGE,
				total: 3,
				scroll_id: "signed-token-1",
				page_size: 50,
				warnings: ["1 of 4 shards could not answer: the results may be incomplete"]
			})
		}
	)

	return sent
}

const searches = (sent: Sent[]) => sent.filter(s => s.path === `/siem/events/${CUSTOMER}/search`)

async function shot(page: Page, name: string) {
	const dir = process.env.E2E_SHOTS
	if (!dir) return
	// Past the app's splash screen, which fades out over the first half second after a load.
	await page.waitForTimeout(1000)
	await page.screenshot({ path: `${dir}/${name}.png` })
}

/** The filter bar's Search, not the header's global search. */
const searchButton = (page: Page) => page.getByRole("button", { name: "Search", exact: true })

function eventSearchUrl(...sources: string[]) {
	const query = new URLSearchParams({ customer_code: CUSTOMER })
	for (const source of sources) query.append("source_name", source)
	return `/event-search?${query}`
}

test.beforeEach(async ({ context, page }) => {
	await installMockBackend(context)
	await signIn(page)
})

test("a link naming two sources searches them together", async ({ page }) => {
	const sent = await installMultiSourceRoutes(page)
	await page.goto(eventSearchUrl(WAZUH, OFFICE))

	await expect.poll(selectedFilters(page)).toEqual(expect.arrayContaining([WAZUH, OFFICE]))
	await expect.poll(() => searches(sent).length).toBe(1)
	expect(searches(sent)[0].body).toEqual({ sources: [WAZUH, OFFICE], page_size: 50, timerange: "24h" })

	await expect(page.getByText("from 2 sources")).toBeVisible()
	await expect(page.getByText("1 of 4 shards could not answer: the results may be incomplete")).toBeVisible()
	await expect(page.locator("thead th").nth(1)).toHaveText("Event source")

	const rows = page.locator("tbody tr")
	await expect(rows).toHaveCount(2)
	await expect(rows.nth(0)).toContainText(WAZUH)
	await expect(rows.nth(1)).toContainText(OFFICE)
	// Each event's page is under the source it came from.
	await expect(rows.nth(0).locator("a[href]")).toHaveAttribute(
		"href",
		"/event-search/ACME/Wazuh%20EDR/wazuh-alerts-4.x-2026.11.20/w1"
	)
	await expect(rows.nth(1).locator("a[href]")).toHaveAttribute(
		"href",
		"/event-search/ACME/Office%20365%20Audit/office365-acme-2026.11.20/o1"
	)
	await shot(page, "event-search-two-sources")
})

test("the next page continues the same search", async ({ page }) => {
	const sent = await installMultiSourceRoutes(page)
	await page.goto(eventSearchUrl(WAZUH, OFFICE))
	await expect(page.locator("tbody tr")).toHaveCount(2)

	await page.getByRole("button", { name: "Load More" }).click()

	await expect(page.locator("tbody tr")).toHaveCount(3)
	expect(searches(sent).at(-1)?.body).toEqual({ sources: [WAZUH, OFFICE], scroll_id: "signed-token-1" })
	await expect(page.getByRole("button", { name: "Load More" })).toHaveCount(0)
})

test("sources picked by hand are searched together", async ({ page }) => {
	const sent = await installMultiSourceRoutes(page)
	// No source named: the first enabled EDR source is picked and searched on its own route.
	await page.goto(`/event-search?customer_code=${CUSTOMER}`)
	await expect.poll(selectedFilters(page)).toContain(WAZUH)

	// The sidebar's customer filter is a multiple select too: take the one holding the source.
	await page.locator(".n-base-selection-tags", { hasText: WAZUH }).click()
	await shot(page, "event-search-source-menu")
	await page.locator(".n-base-select-option", { hasText: sourceOptionLabel(OFFICE) }).click()
	await page.keyboard.press("Escape")
	await searchButton(page).click()

	await expect.poll(() => searches(sent).length).toBe(1)
	expect(searches(sent)[0].body.sources).toEqual([WAZUH, OFFICE])
	await expect(page.locator("thead th").nth(1)).toHaveText("Event source")
})

test("a field typed differently across the sources is called out", async ({ page }) => {
	const sent = await installMultiSourceRoutes(page)
	await page.goto(eventSearchUrl(WAZUH, OFFICE))
	await expect.poll(() => sent.filter(s => s.path.endsWith("/fields")).length).toBe(1)
	expect(sent.find(s => s.path.endsWith("/fields"))?.body).toEqual({ sources: [WAZUH, OFFICE] })

	const warning = page.getByText("a different type in some of these sources")
	await expect(warning).toHaveCount(0)

	await page.getByPlaceholder("e.g. agent_name:web-server AND rule_level:>=10").fill("src_ip:10.0.0.0/8 AND user_id:jdoe")

	await expect(warning).toBeVisible()
	await shot(page, "event-search-field-types-differ")
	await expect(page.locator(".n-alert").filter({ hasText: "different type" })).toContainText("src_ip")
	await expect(page.locator(".n-alert").filter({ hasText: "different type" })).not.toContainText("user_id")
})

test("sources with different time fields are not searched together", async ({ page }) => {
	const sent = await installMultiSourceRoutes(page)
	await page.goto(eventSearchUrl(WAZUH, CLOUD))

	await expect(
		page.getByText("These sources use different time fields (Wazuh EDR: timestamp, Cloud Logs: @timestamp)")
	).toBeVisible()
	await expect(searchButton(page)).toBeDisabled()
	expect(searches(sent)).toHaveLength(0)
	await shot(page, "event-search-time-fields-differ")
})
