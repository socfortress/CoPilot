import type { RecentQuery, SavedQuery } from "../eventSearchMemory"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it } from "vitest"
import EventSearchQueries from "../EventSearchQueries.vue"

const BASE = {
	sourceName: "Wazuh",
	timeMode: "relative" as const,
	time: 24,
	unit: "h" as const,
	timeFrom: null,
	timeTo: null,
	pageSize: 50
}
const SAVED: SavedQuery[] = [{ ...BASE, id: "s1", name: "High level", query: "rule_level:>=10", savedAt: 1 }]
const RECENT: RecentQuery[] = [
	{ ...BASE, query: "", ranAt: Date.now() - 60_000 },
	{ ...BASE, query: "agent_name:web", time: 7, unit: "d", ranAt: Date.now() - 120_000 }
]

function render(props: Partial<{ saved: SavedQuery[]; recent: RecentQuery[]; available: boolean; canSave: boolean }> = {}) {
	return mount(EventSearchQueries, {
		props: { saved: SAVED, recent: RECENT, available: true, canSave: true, ...props },
		attachTo: document.body
	})
}

const all = (selector: string) => [...document.body.querySelectorAll<HTMLElement>(selector)]

describe("eventSearchQueries", () => {
	let wrapper: ReturnType<typeof render> | null = null
	beforeEach(() => setActivePinia(createPinia()))
	afterEach(() => {
		wrapper?.unmount()
		wrapper = null
		document.body.innerHTML = ""
	})

	it("lists saved and recent searches, and hands back the one picked", async () => {
		wrapper = render()
		expect(wrapper.find("[data-testid=saved-queries-toggle]").text()).toContain("1")
		await wrapper.find("[data-testid=saved-queries-toggle]").trigger("click")
		await flushPromises()

		const saved = all("[data-testid=saved-query]")
		expect(saved).toHaveLength(1)
		expect(saved[0]!.textContent).toContain("High level")
		expect(saved[0]!.textContent).toContain("Wazuh · last 24 hours")
		const recent = all("[data-testid=recent-query]")
		expect(recent.map(r => r.textContent)).toEqual([
			expect.stringContaining("*"),
			expect.stringContaining("last 7 days · 2 minutes ago")
		])

		recent[1]!.click()
		expect(wrapper.emitted("restore")?.[0]?.[0]).toMatchObject({ query: "agent_name:web", time: 7, unit: "d" })
		saved[0]!.querySelector("button")!.click()
		expect(wrapper.emitted("restore")?.[1]?.[0]).toMatchObject({ name: "High level" })
	})

	it("deletes a saved search and clears the recent ones", async () => {
		wrapper = render()
		await wrapper.find("[data-testid=saved-queries-toggle]").trigger("click")
		await flushPromises()
		all("[data-testid=saved-query-delete]")[0]!.click()
		all("[data-testid=recent-queries-clear]")[0]!.click()
		expect(wrapper.emitted("delete")).toEqual([["s1"]])
		expect(wrapper.emitted("clearRecent")).toHaveLength(1)
	})

	it("says when there is nothing remembered yet", async () => {
		wrapper = render({ saved: [], recent: [] })
		expect(wrapper.find("[data-testid=saved-queries-toggle]").text()).toBe("Queries")
		await wrapper.find("[data-testid=saved-queries-toggle]").trigger("click")
		await flushPromises()
		expect(document.body.textContent).toContain("No saved query yet")
		expect(document.body.textContent).toContain("The searches you run show up here")
		expect(all("[data-testid=recent-queries-clear]")).toHaveLength(0)
	})

	it("saves under a name, warning when the name is already used", async () => {
		wrapper = render()
		await wrapper.find("[data-testid=save-query-toggle]").trigger("click")
		await flushPromises()
		const input = all("[data-testid=save-query-name] input")[0] as HTMLInputElement
		const submit = all("[data-testid=save-query-submit]")[0] as HTMLButtonElement
		expect(submit.disabled).toBe(true)

		input.value = "high LEVEL"
		input.dispatchEvent(new Event("input"))
		await flushPromises()
		expect(document.body.textContent).toContain("Updates the query saved under this name.")
		submit.click()
		await flushPromises()
		expect(wrapper.emitted("save")).toEqual([["high LEVEL"]])
	})

	it("cannot be used without a customer, nor save without a source", () => {
		wrapper = render({ available: false })
		expect(wrapper.find("[data-testid=saved-queries-toggle]").attributes("disabled")).toBeDefined()
		expect(wrapper.find("[data-testid=save-query-toggle]").attributes("disabled")).toBeDefined()
		wrapper.unmount()
		wrapper = render({ canSave: false })
		expect(wrapper.find("[data-testid=saved-queries-toggle]").attributes("disabled")).toBeUndefined()
		expect(wrapper.find("[data-testid=save-query-toggle]").attributes("disabled")).toBeDefined()
	})
})
