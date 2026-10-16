import type { DisplayColumn, EventSearchColumnTemplate, FieldMapping } from "@/types/siem"
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import EventColumnPicker from "../EventColumnPicker.vue"

const FIELDS: FieldMapping[] = [
	{ field: "timestamp", type: "date" },
	{ field: "agent_name", type: "keyword" },
	{ field: "data_srcip", type: "ip" }
]

function render(props: {
	current: DisplayColumn[]
	personal?: boolean
	sourceColumns?: DisplayColumn[] | null
	templates?: EventSearchColumnTemplate[]
}) {
	return mount(EventColumnPicker, { props: { personal: false, fields: FIELDS, ...props } })
}

function keys(wrapper: ReturnType<typeof render>) {
  return wrapper.findAll("[data-testid=picked-column]").map(row => row.find("[title]").attributes("title"))
}

describe("eventColumnPicker", () => {
	it("starts from the columns on screen, in order", () => {
		const wrapper = render({
			current: [
				{ key: "timestamp", label: "Time" },
				{ key: "agent_name", label: "Host" }
			]
		})
		expect(keys(wrapper)).toEqual(["timestamp", "agent_name"])
		expect(wrapper.findAll("[data-testid=picked-column-label] input").map(i => (i.element as HTMLInputElement).value)).toEqual([
			"Time",
			"Host"
		])
	})

	it("moves and removes columns, and applies them with blank headers falling back to the field", async () => {
		const wrapper = render({
			current: [
				{ key: "timestamp", label: "Time" },
				{ key: "agent_name", label: "Host" }
			]
		})
		await wrapper.find("[data-testid=picked-column-down]").trigger("click")
		expect(keys(wrapper)).toEqual(["agent_name", "timestamp"])

		await wrapper.findAll("[data-testid=picked-column-label] input")[0]!.setValue("   ")
		await wrapper.find("[data-testid=column-picker-save]").trigger("click")
		expect(wrapper.emitted("save")?.[0]).toEqual([
			[
				{ key: "agent_name", label: "agent_name" },
				{ key: "timestamp", label: "Time" }
			]
		])

		await wrapper.findAll("[data-testid=picked-column-remove]")[1]!.trigger("click")
		expect(keys(wrapper)).toEqual(["agent_name"])
	})

	it("offers only the fields not shown yet, and adds one at the end", async () => {
		const wrapper = render({ current: [{ key: "timestamp", label: "Time" }] })
		const select = wrapper.findComponent({ name: "Select" })
		expect((select.props("options") as { value: string }[]).map(o => o.value)).toEqual(["agent_name", "data_srcip"])
		select.vm.$emit("update:value", "data_srcip")
		await wrapper.vm.$nextTick()
		expect(keys(wrapper)).toEqual(["timestamp", "data_srcip"])
	})

	it("goes back to the SOC's layout only from a personal choice", async () => {
		const soc = [{ key: "timestamp", label: "Time" }]
		const shared = render({ current: soc, sourceColumns: soc })
		expect(shared.find("[data-testid=column-picker-reset]").attributes("disabled")).toBeDefined()
		expect(shared.text()).toContain("Back to the SOC's layout")

		const mine = render({ current: soc, personal: true })
		expect(mine.text()).toContain("Back to the default")
		await mine.find("[data-testid=column-picker-reset]").trigger("click")
		expect(mine.emitted("save")?.[0]).toEqual([null])
	})

	describe("templates", () => {
		const TRIAGE: EventSearchColumnTemplate = {
			id: 3,
			source_name: "Wazuh",
			name: "Triage",
			columns: [
				{ key: "agent_name", label: "Host" },
				{ key: "data_srcip", label: "IP" }
			],
			updated_at: ""
		}

		it("lists the source's templates and loads one into the columns being edited", async () => {
			const wrapper = render({ current: [{ key: "timestamp", label: "Time" }], templates: [TRIAGE] })
			const row = wrapper.find("[data-testid=column-template]")
			expect(row.text()).toContain("Triage")
			expect(row.text()).toContain("Host · IP")
			await row.find("[data-testid=column-template-load]").trigger("click")
			expect(keys(wrapper)).toEqual(["agent_name", "data_srcip"])
			// Loading changes nothing yet: Apply does.
			expect(wrapper.emitted("save")).toBeUndefined()
		})

		it("saves the columns being edited as a template, saying when the name is taken", async () => {
			const wrapper = render({ current: [{ key: "timestamp", label: " " }], templates: [TRIAGE] })
			const name = wrapper.find("[data-testid=column-template-name] input")
			expect(wrapper.find("[data-testid=column-template-save]").attributes("disabled")).toBeDefined()

			await name.setValue("triage")
			expect(wrapper.text()).toContain("Updates the template saved under this name.")
			await name.setValue("  Morning ")
			expect(wrapper.text()).not.toContain("Updates the template")
			await wrapper.find("[data-testid=column-template-form]").trigger("submit")
			expect(wrapper.emitted("saveTemplate")).toEqual([["Morning", [{ key: "timestamp", label: "timestamp" }]]])

			// Saved: the list now holds it, and the name is cleared for the next one.
			await wrapper.setProps({ templates: [TRIAGE, { ...TRIAGE, id: 4, name: "Morning" }] })
			expect((name.element as HTMLInputElement).value).toBe("")
		})

		it("cannot save a template without columns", async () => {
			const wrapper = render({ current: [], templates: [TRIAGE] })
			await wrapper.find("[data-testid=column-template-name] input").setValue("Empty")
			expect(wrapper.find("[data-testid=column-template-save]").attributes("disabled")).toBeDefined()
		})

		it("deletes a template only once confirmed, and can be talked out of it", async () => {
			const wrapper = render({ current: [], templates: [TRIAGE] })
			await wrapper.find("[data-testid=column-template-delete]").trigger("click")
			expect(wrapper.emitted("deleteTemplate")).toBeUndefined()
			expect(wrapper.find("[data-testid=template-delete-confirm]").text()).toContain("Delete “Triage”?")

			await wrapper.find("[data-testid=template-delete-cancel]").trigger("click")
			expect(wrapper.find("[data-testid=template-delete-confirm]").exists()).toBe(false)
			expect(wrapper.find("[data-testid=column-template-load]").exists()).toBe(true)

			await wrapper.find("[data-testid=column-template-delete]").trigger("click")
			await wrapper.find("[data-testid=template-delete-confirm-button]").trigger("click")
			expect(wrapper.emitted("deleteTemplate")).toEqual([[3]])

			// Gone from the list: nothing left to confirm.
			await wrapper.setProps({ templates: [] })
			expect(wrapper.find("[data-testid=template-delete-confirm]").exists()).toBe(false)
		})
	})
})
