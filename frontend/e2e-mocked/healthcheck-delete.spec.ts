import type { Locator, Page } from "@playwright/test"
import { expect, test } from "@playwright/test"
import { installHealthcheckMock } from "./healthcheck-fixtures"
import { installMockBackend, signIn } from "./mock-backend"

/**
 * Deleting a customer's unhealthy agents from the healthcheck lists (#1291): an analyst picks the
 * unhealthy agents, chooses how long they must have gone unseen, sees what the backend would delete,
 * confirms, and the list reads back without them. The backend is a stateful stand-in that judges
 * the agents as CoPilot does (healthcheck-fixtures.ts); what is asserted is each request sent.
 */

async function openHealthcheck(page: Page, tab = "Healthcheck Wazuh") {
	await page.goto("/customers/ACME")
	await page
		.locator(".n-tabs-tab", { hasText: /^\s*Agents\s*$/ })
		.first()
		.click()
	await page.locator(".n-tabs-tab", { hasText: tab }).click()
	await expect(page.getByTestId("healthcheck-selection-bar")).toBeVisible({ timeout: 60_000 })
}

function dialogOf(page: Page) {
	return page.getByTestId("unhealthy-delete-dialog")
}

async function deletableCount(dialog: Locator) {
	return (await dialog.getByTestId("unhealthy-delete-count").locator(".stat-value").textContent())?.trim() ?? ""
}

test.describe("delete unhealthy agents from the healthcheck", () => {
	test("an analyst deletes the selected agents unseen for 30 days, and the list reads back without them", async ({
		context,
		page
	}) => {
		await installMockBackend(context)
		const backend = await installHealthcheckMock(context)
		await signIn(page)
		await openHealthcheck(page)

		// The list's default filter is one day: 14 unhealthy, nothing selected, nothing to delete yet.
		await expect(page.getByTestId("healthcheck-selected-count")).toHaveText(/0\s*\/\s*14 selected/)
		await expect(page.getByTestId("healthcheck-delete-selected")).toBeDisabled()

		await page.getByTestId("healthcheck-select-all").click()
		await page.getByTestId("healthcheck-delete-selected").click()
		const dialog = dialogOf(page)
		await expect(dialog.getByTestId("unhealthy-delete-agents")).toBeVisible()
		expect(backend.recorded.previews[0].not_seen_for).toEqual({ value: 1, unit: "days" })
		expect(backend.recorded.previews[0].agent_ids).toHaveLength(14)

		await dialog.locator(".n-radio-button", { hasText: "30 d" }).click()
		await expect(dialog.getByTestId("unhealthy-delete-cutoff")).toContainText("Last seen before")
		await expect.poll(() => deletableCount(dialog)).toBe("12")
		await expect(dialog.getByTestId("unhealthy-delete-active-elsewhere")).toHaveText("1")
		await expect(dialog.getByTestId("unhealthy-delete-kept")).toHaveText("1")
		await expect(dialog.getByTestId("unhealthy-delete-caution")).toHaveCount(0)
		// build-agent-02 is still seen by Velociraptor: kept, and said so.
		await expect(dialog.locator("[data-agent='005']")).toHaveAttribute("data-verdict", "active_elsewhere")

		// The count is typed before every deletion.
		const confirm = dialog.getByTestId("unhealthy-delete-confirm")
		await expect(confirm).toBeDisabled()
		await dialog.getByTestId("unhealthy-delete-typed").locator("input").fill("12")
		await expect(confirm).toHaveText(/Delete 12 agents/)
		await confirm.click()

		await expect(dialog.getByTestId("unhealthy-delete-outcome")).toHaveText("12 agents deleted")
		expect(backend.recorded.deletes.map(body => body.agent_ids.length)).toEqual([10, 2])
		for (const body of backend.recorded.deletes) {
			expect(body.not_seen_for).toEqual({ value: 30, unit: "days" })
			expect(body.include_active_elsewhere).toBe(false)
		}
		expect(backend.remaining().sort()).toEqual(["001", "002", "005", "006"])

		await dialog.getByTestId("unhealthy-delete-close").click()
		await expect(dialog).toBeHidden()
		// The two kept (fresh, or still seen by Velociraptor) are listed, and not picked again.
		await expect(page.getByTestId("healthcheck-selected-count")).toHaveText(/0\s*\/\s*2 selected/)
	})

	test("under a week the dialog cautions, and only the typed count confirms", async ({ context, page }) => {
		await installMockBackend(context)
		const backend = await installHealthcheckMock(context)
		await signIn(page)
		await openHealthcheck(page)

		await page.locator("[data-testid=healthcheck-select]").first().click()
		await page.getByTestId("healthcheck-delete-selected").click()
		const dialog = dialogOf(page)
		await expect(dialog.getByTestId("unhealthy-delete-caution")).toBeVisible()

		const confirm = dialog.getByTestId("unhealthy-delete-confirm")
		await expect(confirm).toBeDisabled()
		await dialog.getByTestId("unhealthy-delete-typed").locator("input").fill("2")
		await expect(confirm).toBeDisabled()
		await dialog.getByTestId("unhealthy-delete-typed").locator("input").fill("1")
		await expect(confirm).toBeEnabled()

		// Under 24 hours is refused in the dialog, and nothing is asked of the backend.
		const previews = backend.recorded.previews.length
		await dialog.getByTestId("unhealthy-delete-unit").click()
		await page.locator(".n-base-select-option", { hasText: "hours" }).click()
		await dialog.getByTestId("unhealthy-delete-value").locator("input").fill("23")
		await expect(dialog.getByTestId("unhealthy-delete-problem")).toContainText("At least 24 hours")
		await expect(confirm).toBeDisabled()
		expect(backend.recorded.previews.length).toBe(previews)
		expect(backend.recorded.deletes).toEqual([])
	})

	test("agents the other tool still sees are deleted only when included", async ({ context, page }) => {
		await installMockBackend(context)
		const backend = await installHealthcheckMock(context)
		await signIn(page)
		await openHealthcheck(page)

		await page.getByTestId("healthcheck-select-all").click()
		await page.getByTestId("healthcheck-delete-selected").click()
		const dialog = dialogOf(page)
		await dialog.locator(".n-radio-button", { hasText: "30 d" }).click()
		await expect.poll(() => deletableCount(dialog)).toBe("12")

		// The row's text toggles it, and the switch itself toggles it once, not twice.
		await dialog.getByTestId("unhealthy-delete-include").getByText("Also delete the 1 agent").click()
		await expect.poll(() => deletableCount(dialog)).toBe("13")
		await dialog.getByTestId("unhealthy-delete-include-switch").click()
		await expect.poll(() => deletableCount(dialog)).toBe("12")
		await dialog.getByTestId("unhealthy-delete-include-switch").click()
		await expect.poll(() => deletableCount(dialog)).toBe("13")
		await expect(dialog.getByTestId("unhealthy-delete-include-switch")).toHaveAttribute("aria-checked", "true")
		await dialog.getByTestId("unhealthy-delete-typed").locator("input").fill("13")
		await dialog.getByTestId("unhealthy-delete-confirm").click()

		await expect(dialog.getByTestId("unhealthy-delete-outcome")).toHaveText("13 agents deleted")
		expect(backend.recorded.deletes.flatMap(body => body.agent_ids)).toContain("005")
		expect(backend.recorded.deletes.every(body => body.include_active_elsewhere)).toBe(true)
		expect(backend.remaining()).not.toContain("005")
	})

	test("a request that fails stops the run, says why, and keeps what was not sent", async ({ context, page }) => {
		await installMockBackend(context)
		const backend = await installHealthcheckMock(context, { failDeleteFrom: 2 })
		await signIn(page)
		await openHealthcheck(page)

		await page.getByTestId("healthcheck-select-all").click()
		await page.getByTestId("healthcheck-delete-selected").click()
		const dialog = dialogOf(page)
		await dialog.locator(".n-radio-button", { hasText: "30 d" }).click()
		await expect.poll(() => deletableCount(dialog)).toBe("12")
		await dialog.getByTestId("unhealthy-delete-typed").locator("input").fill("12")
		await dialog.getByTestId("unhealthy-delete-confirm").click()

		await expect(dialog.getByTestId("unhealthy-delete-outcome")).toHaveText("Stopped after 10 of 12 deleted")
		await expect(dialog).toContainText("Upstream timeout")
		await expect(dialog.getByTestId("unhealthy-delete-total-notSent")).toHaveText("2")
		expect(backend.recorded.deletes).toHaveLength(2)
	})

	test("on a 360 px phone the whole flow fits the screen", async ({ context, page }) => {
		await page.setViewportSize({ width: 360, height: 780 })
		await installMockBackend(context)
		const backend = await installHealthcheckMock(context, { deleteDelayMs: 800 })
		await signIn(page)
		await openHealthcheck(page, "Healthcheck Velociraptor")

		const noSidewaysScroll = () =>
			page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)
		expect(await noSidewaysScroll()).toBe(true)
		// The sub-tabs sit on top: the list gets the screen's width.
		const bar = await page.getByTestId("healthcheck-selection-bar").boundingBox()
		expect(bar?.width ?? 0).toBeGreaterThan(280)

		await page.getByTestId("healthcheck-select-all").click()
		await page.getByTestId("healthcheck-delete-selected").click()
		const dialog = dialogOf(page)
		await expect(dialog.getByTestId("unhealthy-delete-agents")).toBeVisible()
		const box = await dialog.boundingBox()
		expect(box).not.toBeNull()
		expect(box?.x ?? 0).toBeGreaterThanOrEqual(15)
		expect((box?.x ?? 0) + (box?.width ?? Number.POSITIVE_INFINITY)).toBeLessThanOrEqual(345)
		expect(await noSidewaysScroll()).toBe(true)

		await dialog.locator(".n-radio-button", { hasText: "30 d" }).click()
		await expect.poll(() => deletableCount(dialog)).not.toBe("—")
		const count = await deletableCount(dialog)
		await dialog.getByTestId("unhealthy-delete-typed").locator("input").fill(count)
		await dialog.getByTestId("unhealthy-delete-confirm").click()
		// While it runs, the count stays on one line: "0 / 12", never "0 /" above "12".
		const progress = dialog.getByTestId("unhealthy-delete-progress")
		await expect(progress).toBeVisible()
		const progressBox = await progress.boundingBox()
		expect(progressBox?.height ?? 0).toBeLessThan(36)
		await expect(dialog.getByTestId("unhealthy-delete-outcome")).toHaveText(`${count} agents deleted`)
		expect(backend.recorded.deletes.every(body => body.agent_ids.length <= 10)).toBe(true)
	})
})
