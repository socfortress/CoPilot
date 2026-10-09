import type { BrowserContext, Page, Route } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { ASSET, installMockBackend, signIn } from "./mock-backend"

/**
 * #1217 — saving an agent's Velociraptor ID left a loading spinner next to it for good,
 * with no word of success.
 *
 * The save itself was fine: the spinner was an icon that arrived late. The app fetches
 * icons from the Iconify API on first use, so after "Save" the spinner icon (never shown
 * before) was still downloading when the request finished and the edit icon (cached)
 * came back at once — and the spinner then landed on top of it. Here the Iconify API is
 * served by the test, with the spinner deliberately slower than the save, which is that
 * race made deterministic.
 */

const AGENT_ID = ASSET.agent_id
const OLD_ID = "C.0000000000000001"
const NEW_ID = "C.1234567890abcdef"

/** A recognisable SVG body per icon, so the test can tell which one is on screen. */
function iconSet(prefix: string, names: string[]) {
	return {
		prefix,
		width: 24,
		height: 24,
		icons: Object.fromEntries(
			names.map(name => [name, { body: `<path data-icon="${prefix}:${name}" d="M2 2h20v20H2z"/>` }])
		)
	}
}

async function serveIcons(context: BrowserContext, slowPrefix: string, delayMs: number) {
	await context.route(
		url => url.hostname.endsWith("iconify.design") || url.hostname.endsWith("simplesvg.com") || url.hostname.endsWith("unisvg.com"),
		async (route: Route) => {
			const url = new URL(route.request().url())
			const prefix = url.pathname.replace(/^\//, "").replace(/\.json$/, "")
			const names = (url.searchParams.get("icons") ?? "").split(",").filter(Boolean)
			if (prefix === slowPrefix) await new Promise(resolve => setTimeout(resolve, delayMs))
			await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(iconSet(prefix, names)) })
		}
	)
}

async function installAgentMock(context: BrowserContext, { failSave = false } = {}) {
	const saves: string[] = []
	let velociraptorId = OLD_ID
	const json = (route: Route, body: unknown, status = 200) =>
		route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })

	// Registered after the generic mock, so these run first; anything else falls back to it.
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const url = new URL(route.request().url())
			const path = url.pathname.replace(/^\/api/, "")

			if (path === `/agents/${AGENT_ID}`) {
				return json(route, {
					success: true,
					message: "",
					agents: [
						{
							agent_id: AGENT_ID,
							hostname: ASSET.asset_name,
							ip_address: "10.0.0.5",
							os: "Windows Server 2022",
							label: "ACME",
							critical_asset: false,
							wazuh_last_seen: "2026-10-09T10:00:00",
							velociraptor_id: velociraptorId,
							velociraptor_id_pinned: saves.length > 0,
							velociraptor_last_seen: "2026-10-09T10:00:00",
							wazuh_agent_version: "4.9.0",
							wazuh_agent_status: "active",
							velociraptor_agent_version: "0.7.1",
							customer_code: ASSET.customer_code
						}
					]
				})
			}
			if (path === `/agents/${AGENT_ID}/update` && route.request().method() === "PUT") {
				const value = url.searchParams.get("velociraptor_id") ?? ""
				saves.push(value)
				if (failSave) return json(route, { success: false, message: "Invalid Velociraptor client id" }, 400)
				velociraptorId = value
				return json(route, { success: true, message: `Agent ${AGENT_ID} updated with Velociraptor ID: ${value}` })
			}
			return route.fallback()
		}
	)
	return saves
}

async function saveVelociraptorId(page: Page) {
	const field = page.getByTestId("agent-velociraptor-id")
	await expect(field).toContainText(OLD_ID, { timeout: 60_000 })
	await field.getByText(OLD_ID).click()
	await field.locator("input").fill(NEW_ID)
	await field.getByRole("button", { name: "Save" }).click()
	return field
}

test.describe("saving an agent's Velociraptor ID", () => {
	test.beforeEach(async ({ context, page }) => {
		await installMockBackend(context)
		// The spinner icon takes 1.5 s to arrive, far longer than the save.
		await serveIcons(context, "eos-icons", 1500)
		await signIn(page)
	})

	test("ends on the edit icon, not a spinner, and says it was saved", async ({ context, page }) => {
		const saves = await installAgentMock(context)
		await page.goto(`/agents/${AGENT_ID}`)

		const field = await saveVelociraptorId(page)
		await expect.poll(() => saves).toEqual([NEW_ID])
		await expect(page.getByText("Velociraptor ID updated successfully")).toBeVisible()
		await expect(field).toContainText(NEW_ID)

		// Wait out the slow spinner download: it must not replace the edit icon when it lands.
		await page.waitForTimeout(2500)
		await expect(field.locator('[data-icon="uil:edit-alt"]')).toHaveCount(1)
		await expect(field.locator('[data-icon="eos-icons:loading"]')).toHaveCount(0)
	})

	test("says why when the save is refused, and stops loading", async ({ context, page }) => {
		const saves = await installAgentMock(context, { failSave: true })
		await page.goto(`/agents/${AGENT_ID}`)

		const field = await saveVelociraptorId(page)
		await expect.poll(() => saves).toEqual([NEW_ID])
		await expect(page.getByText("Invalid Velociraptor client id")).toBeVisible()
		await expect(field.getByRole("button", { name: "Save" })).toBeEnabled()
		await expect(field.locator("input")).toBeEnabled()
	})
})
