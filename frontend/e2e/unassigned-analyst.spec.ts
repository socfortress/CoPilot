import process from "node:process"
import { expect, test } from "@playwright/test"
import { apiAs, signIn, signOut } from "./fixtures/auth"
import { SCOPED_ANALYST, SEED_PASSWORD, tenants, UNASSIGNED_ANALYST } from "./seed"

/**
 * Analysts and responders always have a customer (#1219).
 *
 * #1050 left an analyst with no assignments deployment-wide, so upgrading did not strip
 * access from analysts nobody had assigned yet. From the outside that was
 * indistinguishable from a tenancy bug, and this spec said that if unassigned ever came
 * to mean "no access", this is the place that would change on purpose. #1219 decided it:
 * an analyst or responder sees exactly the customers assigned to them, is never created
 * without one, and can never be left with none. (One left over from before #1219 sees
 * nothing until an admin assigns some: covered against MySQL by the backend e2e, since
 * the API can no longer produce such a user.)
 */

const ADMIN_USER = process.env.E2E_ADMIN_USER ?? "admin"
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "admin"

const [TENANT_A] = tenants()

test.describe("an analyst always has a customer", () => {
	test.beforeEach(async ({ page }) => {
		await signOut(page)
		await signIn(page, ADMIN_USER, ADMIN_PASSWORD)
	})

	test("cannot be created without one", async () => {
		for (const roleId of [2, 5]) {
			// A name no earlier run (or the pre-#1219 seed, which did create this user
			// unassigned) can have taken, so the refusal is about the customer, not a
			// duplicate username or email.
			const username = `${UNASSIGNED_ANALYST}_${roleId}_${Date.now()}`
			const res = await apiAs(ADMIN_USER, "/auth/register", {
				method: "POST",
				body: JSON.stringify({
					username,
					password: SEED_PASSWORD,
					email: `${username}@e2e.example`,
					role_id: roleId
				})
			})
			expect(res.status, `role ${roleId}`).toBe(400)
			expect(await res.text()).toMatch(/at least one customer/i)

			// ...and nothing was written.
			const users = (await (await apiAs(ADMIN_USER, "/auth/users")).json()) as { users: { username: string }[] }
			expect(users.users.some(user => user.username === username)).toBe(false)
		}
	})

	test("cannot be left without one", async () => {
		const users = (await (await apiAs(ADMIN_USER, "/auth/users")).json()) as {
			users: { id: number; username: string }[]
		}
		const analystId = users.users.find(user => user.username === SCOPED_ANALYST)?.id
		expect(analystId, "the seeded analyst").toBeTruthy()

		const emptied = await apiAs(ADMIN_USER, `/auth/users/${analystId}/customers`, {
			method: "POST",
			body: JSON.stringify([])
		})
		expect(emptied.status).toBe(400)

		// Still assigned to tenant A: the refusal changed nothing.
		const kept = await apiAs(ADMIN_USER, `/auth/users/${analystId}/customers`)
		expect(((await kept.json()) as { customer_codes: string[] }).customer_codes).toEqual([TENANT_A.code])
	})

	test("shows an admin no customer assignment to make for an admin", async ({ page }) => {
		await page.goto("/users")
		const adminRow = page.locator("tr", { hasText: ADMIN_USER }).first()
		await adminRow.getByRole("button").last().click()
		await expect(page.getByRole("button", { name: "Assign Role" })).toBeVisible()
		await expect(page.getByRole("button", { name: "Assign Customer" })).toHaveCount(0)
	})
})
