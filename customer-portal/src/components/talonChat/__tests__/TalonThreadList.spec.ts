import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it } from "vitest"
import { useAuthStore } from "@/stores/auth"
import TalonThreadList from "../TalonThreadList.vue"
import { thread, withProviders } from "./fixtures"

function render(props: Record<string, unknown> = {}) {
	return mount(withProviders(TalonThreadList, { threads: [thread()], selectedId: "th-1", ...props }), { attachTo: document.body })
}

/** Opens the row's menu and picks "Close conversation"; the confirmation is a dialog. */
async function chooseClose(id = "th-1") {
	document.querySelector<HTMLElement>(`[data-testid=talon-thread-actions-${id}]`)?.click()
	await flushPromises()
	const option = [...document.querySelectorAll<HTMLElement>(".n-dropdown-option-body")].find(el =>
		el.textContent?.includes("Close conversation")
	)
	option?.click()
	await flushPromises()
	// The dialog mounts after its own tick.
	await new Promise(resolve => setTimeout(resolve, 20))
}

function dialogButton(text: string) {
	return [...document.querySelectorAll<HTMLButtonElement>(".n-dialog button")].find(el => el.textContent?.includes(text))
}

beforeEach(() => {
	setActivePinia(createPinia())
	useAuthStore().customers = [{ customer_code: "ACME", customer_name: "Acme Corp" }]
	document.body.innerHTML = ""
})

describe("the conversation inbox", () => {
	it("closes a conversation only once the dialog is confirmed", async () => {
		const wrapper = render()
		await chooseClose()
		expect(document.querySelector(".n-dialog")?.textContent).toContain("Close conversation: Scheduled task on HOST-A")
		expect(wrapper.findComponent(TalonThreadList).emitted("archive")).toBeUndefined()

		dialogButton("Close conversation")?.click()
		await flushPromises()
		expect(wrapper.findComponent(TalonThreadList).emitted("archive")).toEqual([["th-1"]])
		wrapper.unmount()
	})

	it("closes nothing when the dialog is cancelled", async () => {
		const wrapper = render()
		await chooseClose()
		dialogButton("Cancel")?.click()
		await flushPromises()
		expect(wrapper.findComponent(TalonThreadList).emitted("archive")).toBeUndefined()
		wrapper.unmount()
	})

	it("shows each row's organization and the alert it is about, and marks the open one", () => {
		const wrapper = render({ threads: [thread({ context_alert_id: 2370 }), thread({ id: "th-2", title: "Other" })] })
		const row = wrapper.get("[data-testid=talon-thread-th-1]")
		expect(row.text()).toContain("Acme Corp")
		expect(row.text()).toContain("Alert #2370")
		expect(row.attributes("aria-current")).toBe("true")
		expect(wrapper.get("[data-testid=talon-thread-th-2]").attributes("aria-current")).toBeUndefined()
		wrapper.unmount()
	})

	it("says what an empty list of closed conversations is", () => {
		const wrapper = render({ threads: [], filter: "archived" })
		expect(wrapper.get("[data-testid=talon-thread-list-empty]").text()).toBe("No closed conversations.")
		expect(wrapper.get("[data-testid=talon-thread-search] input").attributes("disabled")).toBeDefined()
		wrapper.unmount()
	})

	it("asks for the other filter only, never the one already shown", async () => {
		const wrapper = render()
		await wrapper.get("[data-testid=talon-thread-filter-active]").trigger("click")
		await wrapper.get("[data-testid=talon-thread-filter-archived]").trigger("click")
		expect(wrapper.findComponent(TalonThreadList).emitted("filter")).toEqual([["archived"]])
		wrapper.unmount()
	})
})
