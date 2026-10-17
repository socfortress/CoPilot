import type { DisplayColumn, EventSearchColumnTemplate } from "@/types/siem"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it } from "vitest"
import { resolveColumns } from "../eventColumns"
import EventColumnTemplates from "../EventColumnTemplates.vue"

function template(id: number, name: string, columns: DisplayColumn[]): EventSearchColumnTemplate {
	return {
		id,
		source_name: "Wazuh",
		name,
		columns,
		updated_at: ""
	}
}
const TRIAGE = template(1, "Triage", [
	{ key: "agent_name", label: "Host" },
	{ key: "rule_level", label: "Level" }
])
const NETWORK = template(2, "Network", [
	{ key: "data_srcip", label: "Source IP" },
	{ key: "data_dstip", label: "Destination" },
	{ key: "data_dstport", label: "Port" },
	{ key: "agent_name", label: "Host" },
	{ key: "rule_description", label: "Rule" }
])

function render(activeKey: string | null, templates = [TRIAGE, NETWORK]) {
	return mount(EventColumnTemplates, {
		props: {
			templates,
			activeKey,
			sourceName: "SOC layout",
			sourceColumns: resolveColumns([{ key: "timestamp", label: "Time" }], null, "timestamp"),
			resolve: (columns: DisplayColumn[]) => resolveColumns(columns, null, "timestamp"),
			timeField: "timestamp"
		},
		attachTo: document.body
	})
}

const all = (selector: string) => [...document.body.querySelectorAll<HTMLElement>(selector)]
/** The previewed layout: each column's header and field, in order. */
function preview() {
	return all("[data-testid=columns-preview-column]").map(row =>
		[...row.querySelectorAll("span")].slice(1).map(el => el.textContent?.trim())
	)
}

describe("eventColumnTemplates", () => {
	let wrapper: ReturnType<typeof render> | null = null
	beforeEach(() => setActivePinia(createPinia()))
	afterEach(() => {
		wrapper?.unmount()
		wrapper = null
		document.body.innerHTML = ""
	})

	it("names the layout in force, or says the columns are custom", () => {
		wrapper = render("1")
		expect(wrapper.find("[data-testid=column-layouts-current]").text()).toBe("Triage")
		wrapper.unmount()
		wrapper = render("source")
		expect(wrapper.find("[data-testid=column-layouts-current]").text()).toBe("SOC layout")
		wrapper.unmount()
		wrapper = render(null)
		expect(wrapper.find("[data-testid=column-layouts-current]").text()).toBe("Custom")
	})

	it("lists the source's layout first, then the templates, marking the one in force", async () => {
		wrapper = render("1")
		await wrapper.find("[data-testid=column-layouts-toggle]").trigger("click")
		await flushPromises()
		const rows = all("[data-testid=column-layout]")
		expect(
			rows.map(row => [...row.querySelectorAll(":scope > span > span")].map(el => el.textContent?.trim()))
		).toEqual([
			["SOC layout", "Time"],
			["Triage", "Host · Level"],
			["Network", "Source IP · Destination · Port · +2"]
		])
		expect(rows.map(row => row.dataset.active)).toEqual(["false", "true", "false"])
	})

	it("previews every column of the layout in force, then of whichever one is hovered or focused", async () => {
		wrapper = render("1")
		await wrapper.find("[data-testid=column-layouts-toggle]").trigger("click")
		await flushPromises()
		expect(preview()).toEqual([
			["Host", "agent_name"],
			["Level", "rule_level"]
		])

		all("[data-testid=column-layout]")[2]!.dispatchEvent(new Event("mouseenter"))
		await flushPromises()
		expect(preview()).toEqual([
			["Source IP", "data_srcip"],
			["Destination", "data_dstip"],
			["Port", "data_dstport"],
			["Host", "agent_name"],
			["Rule", "rule_description"]
		])

		all("[data-testid=column-layout]")[0]!.dispatchEvent(new Event("focus"))
		await flushPromises()
		expect(preview()).toEqual([["Time", "timestamp"]])
	})

	it.each([
		["the one already in force", 1, undefined],
		["a template", 2, [[NETWORK]]],
		["the source's layout", 0, [[null]]]
	])("applies a layout when picked: %s", async (_name, index, emitted) => {
		wrapper = render("1")
		await wrapper.find("[data-testid=column-layouts-toggle]").trigger("click")
		await flushPromises()
		all("[data-testid=column-layout]")[index]!.click()
		expect(wrapper.emitted("apply")).toEqual(emitted)
	})

	it("points to the column dialog, saying how to make a first template", async () => {
		wrapper = render("source", [])
		await wrapper.find("[data-testid=column-layouts-toggle]").trigger("click")
		await flushPromises()
		expect(document.body.textContent).toContain("No template yet")
		all("[data-testid=column-layouts-manage]")[0]!.click()
		expect(wrapper.emitted("manage")).toHaveLength(1)
	})

	it("deletes a template from the menu only once confirmed", async () => {
		wrapper = render("1")
		await wrapper.find("[data-testid=column-layouts-toggle]").trigger("click")
		await flushPromises()
		// The source's own layout cannot be deleted.
		expect(
			all("[data-testid=column-layout-row]")[0]!.querySelector("[data-testid=column-layout-delete]")
		).toBeNull()

		all("[data-testid=column-layout-delete]")[1]!.click()
		await flushPromises()
		expect(wrapper.emitted("delete")).toBeUndefined()
		const confirm = all("[data-testid=template-delete-confirm]")
		expect(confirm).toHaveLength(1)
		expect(confirm[0]!.textContent).toContain("Delete “Network”?")
		expect(document.activeElement?.textContent?.trim()).toBe("Cancel")

		all("[data-testid=template-delete-cancel]")[0]!.click()
		await flushPromises()
		expect(all("[data-testid=template-delete-confirm]")).toHaveLength(0)
		expect(all("[data-testid=column-layout]")).toHaveLength(3)

		all("[data-testid=column-layout-delete]")[1]!.click()
		await flushPromises()
		all("[data-testid=template-delete-confirm-button]")[0]!.click()
		expect(wrapper.emitted("delete")).toEqual([[2]])
		// Deleting is not picking: the menu applies nothing.
		expect(wrapper.emitted("apply")).toBeUndefined()

		await wrapper.setProps({ templates: [TRIAGE] })
		await flushPromises()
		expect(all("[data-testid=template-delete-confirm]")).toHaveLength(0)
		expect(all("[data-testid=column-layout]")).toHaveLength(2)
	})

	it("cancels a confirmation with Escape, and never keeps one when the menu closes", async () => {
		wrapper = render("1")
		await wrapper.find("[data-testid=column-layouts-toggle]").trigger("click")
		await flushPromises()
		all("[data-testid=column-layout-delete]")[0]!.click()
		await flushPromises()
		all("[data-testid=template-delete-confirm]")[0]!.dispatchEvent(
			new KeyboardEvent("keydown", { key: "Escape", bubbles: true })
		)
		await flushPromises()
		expect(all("[data-testid=template-delete-confirm]")).toHaveLength(0)
		expect(wrapper.emitted("delete")).toBeUndefined()
	})
})
