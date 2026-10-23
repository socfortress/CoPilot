import type { BrowserContext, Page, Route } from "@playwright/test"
import process from "node:process"
import { expect, test } from "@playwright/test"
import { installMockBackend, mintToken, signIn } from "./mock-backend"

/**
 * The AI Analyst page's Memory tab (behind the "Talon v2" setting): an analyst's one customer is
 * picked, the tiles, growth chart and breakdowns show; a search is sent once the typing stops; a
 * memory opens in a side drawer with its markdown rendered safely (raw HTML as text, an image as a
 * link, never loaded), links to its investigation and alert, and a Forget that runs only after the
 * confirm; a durable memory offers no Forget; an asset shows its timeline; "My chat memory" lists the
 * caller's own and forgets one. An older Talon gets the upgrade notice; with Talon v2 off there is no
 * tab. `E2E_SHOTS=<dir>` saves a screenshot of each state.
 */

const OLD_TALON = "This Talon has no memory API: upgrade talon-analyst, and check that its v2 API (TALON_V2_API) is on"
const ONE_OFF = "drawer_ACME_false_positives_0123456789abcdef01234567"
const DURABLE = "drawer_ACME_alerts_aaaaaaaaaaaaaaaaaaaaaaaa"
const JOB = "copilot-inv-840-1760601600000"

function day(offset: number) {
	const at = new Date(Date.UTC(2026, 9, 22 - offset))
	return at.toISOString().slice(0, 10)
}

const STATS = {
	success: true,
	customer_code: "ACME",
	total: 42,
	checked_at: "2026-10-22T08:00:00Z",
	rooms: { alerts: 10, false_positives: 12, threat_intel: 5, assets: 8, environment: 6, other: 1 },
	sources: { investigation: 20, review_durable: 6, review_one_off: 10, chat_remember: 5, other: 1 },
	testing_hidden: 3,
	complete: true,
	growth: Array.from({ length: 30 }, (_, i) => ({ date: day(29 - i), filed: i === 12 ? null : (i * 7) % 5 }))
}

function item(id: string, extra: Record<string, unknown> = {}) {
	return {
		drawer_id: id,
		customer_code: "ACME",
		wing: "ACME",
		openable: true,
		room: "false_positives",
		source: "review_one_off",
		source_ref: { job_id: JOB, alert_id: 840 },
		filed_at: "2026-10-21T10:00:00Z",
		durable: false,
		testing_hidden: false,
		visible_to_investigations: true,
		preview: "The nightly backup on SRV-01 runs vssadmin delete shadows; benign",
		...extra
	}
}

const ITEMS = [
	item(ONE_OFF),
	item(DURABLE, {
		room: "alerts",
		source: "investigation",
		durable: true,
		testing_hidden: true,
		visible_to_investigations: false,
		preview: "Credential dumping on WKS-07 during the purple-team exercise: escalated"
	})
]

const DRAWERS: Record<string, unknown> = {
	[ONE_OFF]: {
		...ITEMS[0],
		content:
			'# Backup job on SRV-01\n\nThe **nightly backup** runs `vssadmin delete shadows /all`.\n\n<img src=x onerror="window.__pwned=1">\n\n![tracker](https://tracker.invalid/p.png)\n\n- Confirmed by an analyst review',
		forgettable: true,
		why_not_forgettable: null,
		why_hidden: null
	},
	[DURABLE]: {
		...ITEMS[1],
		content: "Credential dumping on **WKS-07** was escalated.",
		forgettable: false,
		why_not_forgettable: "An investigation's own record can't be forgotten",
		why_hidden: "Filed while the purple-team exercise was running"
	}
}

interface Seen {
	requests: { method: string; path: string; query: Record<string, string> }[]
}

type Mode = "on" | "old" | "off"

async function installMemoryMock(context: BrowserContext, mode: Mode): Promise<Seen> {
	const seen: Seen = { requests: [] }
	const json = (route: Route, body: unknown, status = 200) =>
		route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })
	let items = [...ITEMS]
	let chat = [
		{
			drawer_id: `drawer_talon chat memory_user ${"a".repeat(64)}_${"b".repeat(24)}`,
			user_id: "1",
			wing: "talon chat memory",
			openable: true,
			filed_at: "2026-10-20T09:00:00Z",
			preview: "Prefers times in UTC",
			thread_id: null
		}
	]

	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const request = route.request()
			const url = new URL(request.url())
			const path = url.pathname.replace(/^\/api/, "")
			if (path.startsWith("/talon/memory")) {
				seen.requests.push({
					method: request.method(),
					path: decodeURIComponent(path),
					query: Object.fromEntries(url.searchParams)
				})
			}
			if (path === "/auth/token" || path === "/auth/refresh") {
				return json(route, {
					success: true,
					access_token: mintToken("analyst", ["analyst"]),
					token_type: "bearer"
				})
			}
			if (path === "/talon/v2/availability") {
				return json(route, { success: true, message: "", enabled: mode !== "off", run_view: false })
			}
			if (path === "/talon/actions") return json(route, { success: true, message: "", actions: [] })
			// The Overview tab opens first; it isn't under test here, so its health read just fails.
			if (path === "/talon/health") return json(route, { detail: "not under test" }, 502)
			if (path.startsWith("/talon/memory")) {
				if (mode === "off") return json(route, { detail: "Not Found" }, 404)
				if (mode === "old") return json(route, { detail: OLD_TALON, code: "unsupported" }, 404)
			}
			if (path === "/talon/memory/ACME/stats") return json(route, STATS)
			if (path === "/talon/memory/ACME/drawers") {
				const q = url.searchParams.get("q")
				const list = q ? items.filter(i => i.preview.toLowerCase().includes("backup")) : items
				return json(route, { success: true, items: list, next_cursor: null })
			}
			const drawerMatch = path.match(/^\/talon\/memory\/ACME\/drawers\/(.+)$/)
			if (drawerMatch) {
				const id = decodeURIComponent(drawerMatch[1])
				if (request.method() === "DELETE") {
					items = items.filter(i => i.drawer_id !== id)
					return json(route, { success: true, drawer_id: id, customer_code: "ACME", wing: "ACME" })
				}
				return DRAWERS[id]
					? json(route, DRAWERS[id])
					: json(route, { detail: "Talon has no such memory", code: "not_found" }, 404)
			}
			if (path === "/talon/memory/ACME/assets") {
				return json(route, {
					success: true,
					items: [
						{ asset: "SRV-01", openable: true, alerts: 4, iocs: 0, last_seen: "2026-10-21T10:00:00Z" },
						{ asset: "WKS-07", openable: true, alerts: 9, iocs: 0, last_seen: "2026-10-20T10:00:00Z" }
					]
				})
			}
			if (path === "/talon/memory/ACME/assets/SRV-01/timeline") {
				return json(route, {
					success: true,
					asset: "SRV-01",
					facts: [
						{
							subject: "SRV-01",
							predicate: "runs",
							object: "the nightly backup (vssadmin)",
							valid_from: "2026-10-02T00:00:00Z",
							valid_to: null
						},
						{
							subject: "SRV-01",
							predicate: "is owned by",
							object: "IT operations",
							valid_from: "2026-09-01T00:00:00Z",
							valid_to: "2026-10-01T00:00:00Z"
						}
					]
				})
			}
			if (path === "/talon/memory/chat/mine") return json(route, { success: true, items: chat })
			const chatMatch = path.match(/^\/talon\/memory\/chat\/mine\/(.+)$/)
			if (chatMatch && request.method() === "DELETE") {
				const id = decodeURIComponent(chatMatch[1])
				chat = chat.filter(i => i.drawer_id !== id)
				return json(route, { success: true, drawer_id: id, user_id: "1" })
			}
			return route.fallback()
		}
	)
	return seen
}

async function open(context: BrowserContext, page: Page, mode: Mode) {
	await installMockBackend(context)
	const seen = await installMemoryMock(context, mode)
	await signIn(page)
	await page.goto("/ai-analyst")
	return seen
}

/** Naive's tabs carry no ARIA tab role: find them by their own class. */
function tab(page: Page, name: string) {
	return page.locator(".n-tabs-tab", { hasText: new RegExp(`^\\s*${name}\\s*$`) })
}

async function shot(page: Page, name: string) {
	const dir = process.env.E2E_SHOTS
	if (!dir) return
	const size = page.viewportSize()
	await page.setViewportSize({ width: 1440, height: 2400 })
	await page.waitForTimeout(500)
	await page.screenshot({ path: `${dir}/${name}.png` })
	if (size) await page.setViewportSize(size)
}

test.describe("talon memory tab", () => {
	test("an analyst browses, searches, opens and forgets a memory", async ({ context, page }) => {
		const seen = await open(context, page, "on")
		await tab(page, "Memory").click()

		await expect(page.getByTestId("talon-memory-total")).toContainText("42")
		await expect(page.getByTestId("talon-memory-hidden")).toContainText("Hidden as testing")
		await expect(page.getByTestId("talon-memory-hidden")).toContainText("3")
		await expect(page.getByTestId("talon-memory-growth")).toBeVisible()
		await expect(page.locator('[data-testid="talon-memory-rooms"] [data-key="false_positives"]')).toContainText(
			"12"
		)
		await expect(page.getByTestId("talon-memory-row")).toHaveCount(2)
		await expect(page.getByTestId("talon-memory-row").nth(1)).toContainText("Hidden: testing")
		await shot(page, "memory-overview")

		// The search goes once the typing stops, as q in the query string.
		const before = seen.requests.length
		await page.getByTestId("talon-memory-search").locator("input").pressSequentially("backups", { delay: 30 })
		await expect(page.getByTestId("talon-memory-row")).toHaveCount(1)
		const searches = seen.requests.slice(before).filter(r => r.path === "/talon/memory/ACME/drawers")
		expect(searches).toHaveLength(1)
		expect(searches[0].query.q).toBe("backups")
		await page.getByTestId("talon-memory-search").locator("input").fill("")
		await expect(page.getByTestId("talon-memory-row")).toHaveCount(2)

		// A durable investigation record: why it is hidden, and no Forget.
		await page.getByTestId("talon-memory-open").nth(1).click()
		const detail = page.getByTestId("talon-memory-detail-body")
		await expect(detail.getByTestId("talon-memory-detail-hidden")).toContainText("purple-team exercise")
		await expect(detail.getByTestId("talon-memory-detail-hidden")).toContainText("never a reason to lower")
		await expect(detail.getByTestId("talon-memory-forget")).toHaveCount(0)
		await expect(detail.getByTestId("talon-memory-not-forgettable")).toContainText("can't be forgotten")
		await shot(page, "memory-detail-durable")
		await page.keyboard.press("Escape")
		await expect(page.getByTestId("talon-memory-detail-body")).toHaveCount(0)

		// A one-off review lesson: rendered markdown, safely; links; Forget after the confirm.
		await page.getByTestId("talon-memory-open").first().click()
		const content = page.getByTestId("talon-memory-detail-content")
		await expect(content.locator("h1")).toHaveText("Backup job on SRV-01")
		await expect(content.locator("strong")).toHaveText("nightly backup")
		await expect(content).toContainText('<img src=x onerror="window.__pwned=1">')
		await expect(content.locator("img")).toHaveCount(0)
		expect(await page.evaluate(() => (window as unknown as { __pwned?: number }).__pwned)).toBeUndefined()
		await expect(page.getByTestId("talon-memory-detail-job")).toHaveAttribute("href", `/ai-analyst/jobs/${JOB}`)
		await expect(page.getByTestId("talon-memory-detail-alert")).toHaveAttribute("href", /\/840$/)
		await shot(page, "memory-detail-one-off")

		page.on("dialog", () => {
			throw new Error("a browser dialog was opened")
		})
		await page.getByTestId("talon-memory-forget").click()
		await expect(page.getByTestId("talon-memory-forget-confirm")).toBeVisible()
		expect(seen.requests.filter(r => r.method === "DELETE")).toHaveLength(0)
		await shot(page, "memory-forget-confirm")
		await page.getByTestId("talon-memory-forget-confirm-button").click()
		await expect(page.getByTestId("talon-memory-row")).toHaveCount(1)
		expect(seen.requests.filter(r => r.method === "DELETE").map(r => r.path)).toEqual([
			`/talon/memory/ACME/drawers/${ONE_OFF}`
		])

		// Assets and a timeline.
		await page.getByTestId("talon-memory-view-assets").click()
		const srv = page.locator('[data-testid="talon-memory-asset"][data-asset="SRV-01"]')
		await expect(srv).toContainText("IOCs: no data yet")
		await srv.click()
		await expect(page.getByTestId("talon-memory-fact")).toHaveCount(2)
		await expect(page.getByTestId("talon-memory-fact").first()).toContainText("is owned by")
		await expect(page.getByTestId("talon-memory-fact").first()).toContainText("no longer true")
		await shot(page, "memory-assets")

		// My chat memory: the caller's own; forget after the confirm.
		await tab(page, "My chat memory").click()
		await expect(page.getByTestId("talon-memory-chat-item")).toHaveCount(1)
		await page.getByTestId("talon-memory-chat-forget").click()
		await shot(page, "memory-chat-confirm")
		await page.getByTestId("talon-memory-chat-confirm-button").click()
		await expect(page.getByTestId("talon-memory-chat-empty")).toBeVisible()
		const chatPaths = seen.requests
			.filter(r => r.path.startsWith("/talon/memory/chat"))
			.map(r => `${r.method} ${r.path}`)
		expect(chatPaths).toEqual([
			"GET /talon/memory/chat/mine",
			`DELETE /talon/memory/chat/mine/drawer_talon chat memory_user ${"a".repeat(64)}_${"b".repeat(24)}`
		])
	})

	test("an older Talon gets the upgrade notice", async ({ context, page }) => {
		await open(context, page, "old")
		await tab(page, "Memory").click()
		const problem = page.getByTestId("talon-memory-problem").first()
		await expect(problem).toHaveAttribute("data-kind", "unsupported")
		await expect(problem).toContainText(OLD_TALON)
		await expect(page.getByTestId("talon-memory-drawers")).toHaveCount(0)
		await shot(page, "memory-old-talon")
	})

	test("with Talon v2 off there is no Memory tab", async ({ context, page }) => {
		const seen = await open(context, page, "off")
		await expect(tab(page, "Overview")).toBeVisible()
		await expect(tab(page, "Memory")).toHaveCount(0)
		expect(seen.requests).toHaveLength(0)
	})
})
