import process from "node:process"
import { expect, test } from "@playwright/test"
import { apiAs, signIn, signOut } from "./fixtures/auth"
import { SCOPED_ANALYST, SEED_PASSWORD, tenants } from "./seed"

/**
 * The responder role (#1219) against the real backend.
 *
 * An admin promotes an analyst to responder from the Users page, which is where the
 * customers are confirmed in the same step; the role the backend stores is what the
 * next sign-in's token carries, so the responder's menu and tabs here come from the
 * server, not from a planted token. Below the UI, the response routes serve the
 * responder's own customer and refuse the other one — and refuse an analyst outright.
 */

const ADMIN_USER = process.env.E2E_ADMIN_USER ?? "admin"
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "admin"

const [TENANT_A, TENANT_B] = tenants()

// One user per run: the promotion is the thing under test, so it must start as an analyst.
const RESPONDER = `e2e_pw_responder_${Date.now()}`

interface ListedUser {
	id: number
	username: string
	role_name: string | null
	customer_codes?: string[] | null
}

async function listed(username: string): Promise<ListedUser | undefined> {
	const res = await apiAs(ADMIN_USER, "/auth/users")
	const body = (await res.json()) as { users: ListedUser[] }
	return body.users.find(user => user.username === username)
}

test.describe.configure({ mode: "serial" })

test.describe("a responder", () => {
	test("is made from an analyst by an admin, keeping their customers", async ({ page }) => {
		await signOut(page)
		await signIn(page, ADMIN_USER, ADMIN_PASSWORD)

		const created = await apiAs(ADMIN_USER, "/auth/register", {
			method: "POST",
			body: JSON.stringify({
				username: RESPONDER,
				password: SEED_PASSWORD,
				email: `${RESPONDER}@e2e.example`,
				role_id: 2,
				customer_codes: [TENANT_A.code]
			})
		})
		expect(created.status, await created.text()).toBe(201)

		await page.goto("/users")
		const row = page.locator("tr", { hasText: RESPONDER })
		await row.getByRole("button").last().click()
		await page.getByRole("button", { name: "Assign Role" }).click()

		await page.getByTestId("assign-role-select").click()
		await page.locator(".n-base-select-option", { hasText: "Responder" }).click()

		// The analyst's customer is already there: promoting keeps it.
		const submit = page.getByTestId("assign-role-submit")
		await expect(submit).toBeEnabled()
		const saved = page.waitForResponse(res => res.url().includes("/role/by-name") && res.request().method() === "PUT")
		await submit.click()
		expect((await saved).status()).toBe(200)

		await expect.poll(async () => (await listed(RESPONDER))?.role_name).toBe("responder")
		expect((await listed(RESPONDER))?.customer_codes).toEqual([TENANT_A.code])
	})

	test("is offered the response actions once signed in", async ({ page }) => {
		await signOut(page)
		await signIn(page, RESPONDER)

		await page.getByText("Respond", { exact: true }).first().click()
		await expect(page.getByRole("menuitem", { name: "CoPilot Actions" })).toBeVisible()

		await page.goto("/artifacts")
		await expect(page.locator(".n-tabs-tab", { hasText: /^\s*Command\s*$/ })).toBeVisible({ timeout: 60_000 })
		await expect(page.locator(".n-tabs-tab", { hasText: /^\s*Quarantine\s*$/ })).toBeVisible()
	})

	test("may act, but is refused the other customer below the UI", async ({ page }) => {
		await signOut(page)
		await signIn(page, RESPONDER)

		// The role opens the response routes (what each one does with its own customer's
		// endpoints is covered against MySQL by backend/tests/e2e/responder_role_e2e.py,
		// with Velociraptor and MinIO stubbed out)...
		const actions = await apiAs(RESPONDER, "/copilot_action/technologies")
		expect(actions.status).toBe(200)

		// ...and the tenant check refuses the other customer before anything runs.
		const other = await apiAs(RESPONDER, `/sysmon_config/content/${TENANT_B.code}`)
		expect(other.status).toBe(403)
		const deploy = await apiAs(RESPONDER, `/sysmon_config/deploy/${TENANT_B.code}`, { method: "POST" })
		expect(deploy.status).toBe(403)

		// Uploading a config and administering users stay an admin's.
		const users = await apiAs(RESPONDER, "/auth/users/1/customers", { method: "POST", body: JSON.stringify([]) })
		expect([401, 403]).toContain(users.status)
	})
})

test.describe("an analyst", () => {
	test("is offered no response actions and is refused them below the UI", async ({ page }) => {
		await signOut(page)
		await signIn(page, SCOPED_ANALYST)

		await page.getByText("Respond", { exact: true }).first().click()
		await expect(page.getByRole("menuitem", { name: "Active Response" })).toBeVisible()
		await expect(page.getByRole("menuitem", { name: "CoPilot Actions" })).toHaveCount(0)

		const actions = await apiAs(SCOPED_ANALYST, "/copilot_action/technologies")
		expect(actions.status).toBe(403)
		const deploy = await apiAs(SCOPED_ANALYST, `/sysmon_config/deploy/${TENANT_A.code}`, { method: "POST" })
		expect(deploy.status).toBe(403)
	})
})
