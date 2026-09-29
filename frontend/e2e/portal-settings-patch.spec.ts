import process from "node:process"
import { expect, test } from "@playwright/test"
import { apiAs, signIn, signOut } from "./fixtures/auth"

/**
 * The Customer Portal settings editor saves with PATCH (#1188): only what changed is
 * sent, so renaming the portal no longer re-uploads a logo of up to 5MB, and a cleared
 * field is an explicit `reset`.
 */

const ADMIN_USER = process.env.E2E_ADMIN_USER ?? "admin"
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "admin"

const LOGO = "iVBORw0KGgo="
const SAVED = { title: "E2E Portal", logo_base64: LOGO, logo_mime_type: "image/png", brand_color: "#112233" }

interface StoredSettings {
	title: string
	logo_base64: string | null
	logo_mime_type: string | null
	brand_color: string | null
}

async function stored(): Promise<StoredSettings> {
	const res = await apiAs(ADMIN_USER, "/customer_portal/settings/global")
	return ((await res.json()) as { settings: StoredSettings }).settings
}

async function replace(settings: Partial<StoredSettings>) {
	const res = await apiAs(ADMIN_USER, "/customer_portal/settings", { method: "POST", body: JSON.stringify(settings) })
	expect(res.status).toBe(200)
}

test.describe("portal settings editor", () => {
	let original: StoredSettings

	test.beforeEach(async ({ page }) => {
		await signOut(page)
		await signIn(page, ADMIN_USER, ADMIN_PASSWORD)
		original ??= await stored()
		await replace(SAVED)
		await page.goto("/customer-portal")
		await expect(page.locator('[data-testid="portal-settings-title"] input')).toHaveValue(SAVED.title)
	})

	test.afterAll(async () => {
		if (original) {
			const { title, logo_base64, logo_mime_type, brand_color } = original
			await replace({ title, logo_base64, logo_mime_type, brand_color })
		}
	})

	test("renaming sends only the title, never the logo", async ({ page }) => {
		await page.locator('[data-testid="portal-settings-title"] input').fill("Renamed by E2E")

		const request = page.waitForRequest(req => req.url().includes("/customer_portal/settings") && req.method() !== "GET")
		await page.locator('[data-testid="portal-settings-save"]').click()

		const sent = await request
		expect(sent.method()).toBe("PATCH")
		expect(sent.postDataJSON()).toEqual({ title: "Renamed by E2E" })
		await expect.poll(async () => (await stored()).title).toBe("Renamed by E2E")
		expect((await stored()).logo_base64).toBe(LOGO)
	})

	test("clearing the brand color is a reset", async ({ page }) => {
		await page.getByRole("button", { name: "Reset" }).click()

		const request = page.waitForRequest(req => req.url().includes("/customer_portal/settings") && req.method() === "PATCH")
		await page.locator('[data-testid="portal-settings-save"]').click()

		expect((await request).postDataJSON()).toEqual({ reset: ["brand_color"] })
		await expect.poll(async () => (await stored()).brand_color).toBeNull()
		expect((await stored()).logo_base64).toBe(LOGO)
	})

	test("saving without changes sends nothing", async ({ page }) => {
		let writes = 0
		page.on("request", req => {
			if (req.url().includes("/customer_portal/settings") && req.method() !== "GET") writes++
		})

		await page.locator('[data-testid="portal-settings-save"]').click()

		await expect(page.getByText("No changes to save")).toBeVisible()
		expect(writes).toBe(0)
	})
})
