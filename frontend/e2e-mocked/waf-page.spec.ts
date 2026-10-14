import type { BrowserContext, Page, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { installMockBackend, signIn } from "./mock-backend"
import {
	EVENT_COUNT,
	OFFENDER_COUNT,
	OFFENDERS,
	TOP_OFFENDER,
	WAF_CUSTOMER,
	WAF_ID,
	WAF_INSTANCE,
	WAF_STATS,
	wafEvent
} from "./waf-fixtures"

/**
 * The WAF page's lists and chart: Events pages through the WAF with the native pagination
 * and a page-size picker (the WAF returns no total, so one extra row says whether a next
 * page exists); Threat intel ranks offenders by score, pages them client-side and is no
 * longer a list element; the requests chart's tooltip is the shared chart tooltip.
 */

const BASE = `/customer_waf/${WAF_CUSTOMER}/${WAF_ID}`

async function installWafMock(context: BrowserContext, eventRequests: URL[]) {
	const json = (route: Route, body: unknown) =>
		route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) })

	// Registered after the generic mock, so these run first; anything else falls back to it.
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const url = new URL(route.request().url())
			const path = url.pathname.replace(/^\/api/, "")

			if (path === "/customer_waf") {
				return json(route, { success: true, instances: [WAF_INSTANCE], encryption_key_configured: true })
			}
			if (path === `${BASE}/stats`) return json(route, { success: true, stats: WAF_STATS })
			if (path === `${BASE}/threat-intel`) {
				return json(route, {
					success: true,
					summary: { total_ips: OFFENDER_COUNT, last_run_at: "2026-10-14T11:00:00Z", window_days: 7, min_score: 10 },
					entries: OFFENDERS
				})
			}
			if (path === `${BASE}/events`) {
				eventRequests.push(url)
				const limit = Number(url.searchParams.get("limit"))
				const offset = Number(url.searchParams.get("offset"))
				const events = Array.from({ length: Math.max(0, Math.min(limit, EVENT_COUNT - offset)) }, (_, i) =>
					wafEvent(offset + i))
				return json(route, { success: true, events, limit, offset })
			}
			return route.fallback()
		}
	)
}

function openTab(page: Page, tab: string) {
	return page.goto(`/waf?customer=${WAF_CUSTOMER}&waf=${WAF_ID}&tab=${tab}`)
}

test.describe("WAF page", () => {
	let eventRequests: URL[]

	test.beforeEach(async ({ context, page }) => {
		eventRequests = []
		await installMockBackend(context)
		await installWafMock(context, eventRequests)
		await signIn(page)
	})

	test("header: the selected WAF's state and facts, labels over values", async ({ page }) => {
		await openTab(page, "overview")
		const panel = page.getByTestId("waf-instance-panel")
		await expect(panel).toContainText(WAF_INSTANCE.name)
		await expect(panel).toContainText("Can block")
		await expect(page.getByTestId("waf-status-dot")).toHaveAttribute("title", "Enabled and verified")
		await expect(page.getByTestId("waf-fact-customer")).toContainText("Acme Corp")
		await expect(page.getByTestId("waf-fact-customer")).toContainText(WAF_CUSTOMER)
		await expect(page.getByTestId("waf-fact-endpoint")).toContainText(WAF_INSTANCE.api_url)
		await expect(page.getByTestId("waf-fact-token")).toContainText(WAF_INSTANCE.token_prefix)
		await expect(page.getByTestId("waf-fact-forwarding")).toContainText("not set up")
	})

	test("overview: the rank lists number their rows, carry no list element, and keep their actions", async ({
		page
	}) => {
		await openTab(page, "overview")
		const lists = page.getByTestId("waf-rank-list")
		await expect(lists).toHaveCount(4)
		await expect(lists.locator("ol, ul, li")).toHaveCount(0)

		const ips = lists.filter({ hasText: "Top client IPs" })
		const first = ips.getByTestId("waf-rank-row").first()
		await expect(first).toContainText("01")
		await expect(first).toContainText(WAF_STATS.top_ips[0].client_ip)
		await expect(first).toContainText(WAF_STATS.top_ips[0].count.toLocaleString("en-US"))

		// "Events from this IP" still opens Events pre-filtered on it.
		await first.getByRole("button").first().click()
		await expect(page).toHaveURL(new RegExp(`tab=events.*ip=${WAF_STATS.top_ips[0].client_ip}`))
	})

	test("events: page by page with a page size, saying whether there is more, never a page count that grows", async ({
		page
	}) => {
		await openTab(page, "events")
		const rows = page.getByTestId("waf-event-row")
		const pageLabel = page.getByTestId("waf-events-page")
		await expect(rows).toHaveCount(50)
		await expect(page.getByTestId("waf-events-range")).toContainText("1–50")
		await expect(pageLabel).toHaveText(/Page 1\s*· more available/)
		await expect(page.getByTestId("waf-events-prev")).toBeDisabled()
		// One row more than a page: it only says whether a next page exists.
		expect(eventRequests.at(-1)?.searchParams.get("limit")).toBe("51")
		expect(eventRequests.at(-1)?.searchParams.get("offset")).toBe("0")

		await page.getByTestId("waf-events-next").click()
		await expect(page.getByTestId("waf-events-range")).toContainText("51–100")
		await expect(pageLabel).toHaveText(/Page 2\s*· more available/)
		expect(eventRequests.at(-1)?.searchParams.get("offset")).toBe("50")

		// The last page is short, says so, and offers nothing after it.
		await page.getByTestId("waf-events-next").click()
		await expect(rows).toHaveCount(EVENT_COUNT - 100)
		await expect(pageLabel).toHaveText(/Page 3\s*· last page/)
		await expect(page.getByTestId("waf-events-next")).toBeDisabled()

		// Back one, then straight to the newest.
		await page.getByTestId("waf-events-prev").click()
		await expect(pageLabel).toHaveText(/Page 2/)
		await page.getByTestId("waf-events-first").click()
		await expect(pageLabel).toHaveText(/Page 1/)
		expect(eventRequests.at(-1)?.searchParams.get("offset")).toBe("0")

		// A new page size starts again from the newest page.
		await page.getByTestId("waf-events-next").click()
		await expect(pageLabel).toHaveText(/Page 2/)
		await page.getByTestId("waf-events-page-size").click()
		await page.locator(".n-base-select-option").filter({ hasText: "25 / page" }).click()
		await expect(rows).toHaveCount(25)
		await expect(pageLabel).toHaveText(/Page 1/)
		await expect(page.getByTestId("waf-events-range")).toContainText("1–25")
		expect(eventRequests.at(-1)?.searchParams.get("limit")).toBe("26")
		expect(eventRequests.at(-1)?.searchParams.get("offset")).toBe("0")
	})

	test("events: the whole row opens its detail with every matched rule", async ({ page }) => {
		await openTab(page, "events")
		const first = page.getByTestId("waf-event-row").first()
		const row = first.getByRole("button")
		await expect(row).toHaveCSS("cursor", "pointer")

		// Anywhere on the row toggles it: the client column, far from the chevron, opens it…
		await row.getByText(wafEvent(0).client_ip).click()
		const detail = first.getByTestId("waf-event-detail")
		await expect(detail).toBeVisible()
		await expect(detail).toContainText(wafEvent(0).transaction_id)
		await expect(detail).toContainText("Matched rules · 2")
		await expect(detail).toContainText("Inbound Anomaly Score Exceeded")

		// …and the time column closes it again.
		await row.getByText(/^\d{2}:\d{2}:\d{2}$/).click()
		await expect(detail).toHaveCount(0)
	})

	test("threat intel: ranked by score, paged client-side, and no list element", async ({ page }) => {
		await openTab(page, "threat-intel")
		const section = page.getByTestId("waf-threat-intel")
		const rows = page.getByTestId("waf-offender-row")
		await expect(rows).toHaveCount(25)
		await expect(rows.first()).toContainText("01")
		await expect(rows.first()).toContainText(TOP_OFFENDER.ip_address)
		await expect(page.getByTestId("waf-offenders-range")).toContainText(`1–25 of ${OFFENDER_COUNT}`)
		await expect(section.locator("ul, li")).toHaveCount(0)

		await page.getByTestId("waf-offenders-pagination").locator(".n-pagination-item").filter({ hasText: /^3$/ }).click()
		await expect(rows).toHaveCount(OFFENDER_COUNT - 50)
		await expect(rows.first()).toContainText("51")

		// Narrowing the list starts again from the top.
		await page.getByPlaceholder("Filter by IP or country").fill("Bulgaria")
		await expect(page.getByTestId("waf-offenders-range")).toContainText(`1–25 of ${OFFENDER_COUNT / 2}`)
	})

	test("overview: the requests chart's tooltip is the shared chart tooltip", async ({ page }) => {
		await openTab(page, "overview")
		const chart = page.locator("[aria-label^='Requests per hour']")
		await expect(chart).toBeVisible()
		const box = await chart.boundingBox()
		if (!box) throw new Error("chart has no box")

		// The shared formatter: a muted title band (the hour range), then "label: value".
		// ECharts mounts the tooltip outside the chart's own element, and only once its first
		// render is done: hover again until it shows.
		await expect(async () => {
			await page.mouse.move(box.x + box.width / 2 - 10, box.y + box.height / 2)
			await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
			await expect(page.getByText(/^Requests: [\d,]+$/)).toBeVisible({ timeout: 1000 })
		}).toPass()
		await expect(page.getByText(/^\w{3} \d{1,2} \w{3}, \d{2}:\d{2}–\d{2}:\d{2}$/)).toBeVisible()
	})
})
