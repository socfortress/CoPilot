import type { Page } from "@playwright/test"
import process from "node:process"
import { expect, test } from "@playwright/test"
import { apiAs, signIn } from "./fixtures/auth"
import { API_ORIGIN } from "./seed"

/**
 * #1291 — deleting a customer's unhealthy agents, against the real backend and MySQL.
 *
 * The backend is `backend/tests/e2e/healthcheck_delete_server.py`: the real app with Wazuh and
 * Velociraptor deletions recorded instead of sent, and no connection allowed beyond 127.0.0.1; it
 * seeds itself on `POST /e2e/reset` (see the README). What the browser asked is checked
 * where it landed: the rows left in MySQL, the audit log, and what the upstreams were asked.
 */

const ADMIN = process.env.E2E_HD_ADMIN ?? "e2e_hd_admin"
const PASSWORD = process.env.E2E_HD_PASSWORD ?? "E2ePlaywr1ght!hd"
const CUSTOMER = "E2E_HDW"
const id = (suffix: string) => `e2ehdw-${suffix}`

async function openHealthcheck(page: Page) {
	await page.goto(`/customers/${CUSTOMER}`)
	await page
		.locator(".n-tabs-tab", { hasText: /^\s*Agents\s*$/ })
		.first()
		.click()
	await page.locator(".n-tabs-tab", { hasText: "Healthcheck Wazuh" }).click()
	await expect(page.getByTestId("healthcheck-selection-bar")).toBeVisible({ timeout: 60_000 })
}

test.describe("#1291 delete unhealthy agents (real backend)", () => {
	// Every run starts from the seed's rows and an empty record of upstream calls.
	test.beforeAll(async () => {
		const reset = await fetch(`${API_ORIGIN}/e2e/reset`, { method: "POST" }).catch(() => null)
		if (!reset?.ok) {
			throw new Error(
				`This spec needs the guarded e2e backend (no request may reach a real Wazuh or Velociraptor):\n\n` +
					`  cd backend && PYTHONPATH=$PWD .venv/bin/uvicorn tests.e2e.healthcheck_delete_server:app --lifespan off --port 5102\n\n` +
					`then E2E_API_URL=http://127.0.0.1:5102 VITE_API_URL=http://127.0.0.1:5102 E2E_PORT=5199 \\\n` +
					`  E2E_ADMIN_USER=${ADMIN} E2E_ADMIN_PASSWORD='${PASSWORD}' pnpm test:e2e healthcheck-delete`
			)
		}
	})

	test("an admin deletes the agents unseen for 30 days; MySQL, the audit log and the upstreams agree", async ({
		page
	}) => {
		await signIn(page, ADMIN, PASSWORD)
		await openHealthcheck(page)

		// At the list's one-day filter, five are unhealthy: all but the fresh one.
		await expect(page.getByTestId("healthcheck-selected-count")).toHaveText(/0\s*\/\s*5 selected/)
		await page.getByTestId("healthcheck-select-all").click()
		await page.getByTestId("healthcheck-delete-selected").click()

		const dialog = page.getByTestId("unhealthy-delete-dialog")
		await dialog.locator(".n-radio-button", { hasText: "30 d" }).click()
		await expect(dialog.getByTestId("unhealthy-delete-cutoff")).toContainText("Last seen before")
		await expect(dialog.getByTestId("unhealthy-delete-count").locator(".stat-value")).toHaveText("4")
		await expect(dialog.getByTestId("unhealthy-delete-active-elsewhere")).toHaveText("1")
		await expect(dialog.locator(`[data-agent='${id("velo-alive")}']`)).toHaveAttribute(
			"data-verdict",
			"active_elsewhere"
		)
		await expect(dialog.locator(`[data-agent='${id("novelo")}']`)).toHaveAttribute("data-verdict", "deletable")

		// Four agents at 30 days: no typed count needed.
		await expect(dialog.getByTestId("unhealthy-delete-typed")).toHaveCount(0)
		await dialog.getByTestId("unhealthy-delete-confirm").click()
		await expect(dialog.getByTestId("unhealthy-delete-outcome")).toHaveText("4 agents deleted")

		// MySQL: only the agent Velociraptor still sees and the fresh one are left.
		const agents = await (await apiAs(ADMIN, `/customers/${CUSTOMER}/agents`)).json()
		expect(agents.agents.map((agent: { agent_id: string }) => agent.agent_id).sort()).toEqual([
			id("fresh"),
			id("velo-alive")
		])

		// The upstreams were asked for exactly those four; Velociraptor only for the three with a client.
		const calls = await (await fetch(`${API_ORIGIN}/e2e/upstream-calls`)).json()
		const deleted = [id("gone-1"), id("gone-2"), id("gone-3"), id("novelo")]
		expect([...calls.wazuh].sort()).toEqual([...deleted].sort())
		expect(calls.velociraptor).toHaveLength(3)

		// One audit row each, by this admin, with the threshold it was deleted under.
		for (const agentId of deleted) {
			const audit = await (await apiAs(ADMIN, `/audit?action=agent.delete&entity_id=${agentId}`)).json()
			expect(audit.audit_logs).toHaveLength(1)
			expect(audit.audit_logs[0]).toMatchObject({
				actor_username: ADMIN,
				customer_code: CUSTOMER,
				result: "success",
				new_value: {
					via: "healthcheck",
					source: "wazuh",
					not_seen_for: "30 days",
					include_active_elsewhere: false
				}
			})
		}

		// The list reads back the change.
		await dialog.getByTestId("unhealthy-delete-close").click()
		await expect(page.getByTestId("healthcheck-selected-count")).toHaveText(/0\s*\/\s*1 selected/)
	})

	test("the backend refuses what the dialog would never send", async ({ page }) => {
		await signIn(page, ADMIN, PASSWORD)
		const path = `/customers/${CUSTOMER}/agents/healthcheck/wazuh/delete`
		const body = (notSeenFor: object) =>
			JSON.stringify({ agent_ids: [id("fresh")], not_seen_for: notSeenFor, include_active_elsewhere: false })

		const tooShort = await apiAs(ADMIN, path, { method: "POST", body: body({ value: 23, unit: "hours" }) })
		expect(tooShort.status).toBe(422)
		expect((await tooShort.json()).message).toContain("at least 24 hours")

		// A fresh agent named directly is judged again, and kept.
		const fresh = await apiAs(ADMIN, path, { method: "POST", body: body({ value: 1, unit: "days" }) })
		const answer = await fresh.json()
		expect(answer.results).toEqual([
			{
				agent_id: id("fresh"),
				hostname: "HD-FRESH",
				outcome: "skipped",
				reason: "seen_recently",
				unconfirmed: []
			}
		])
	})
})
