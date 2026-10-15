import type { DisplayColumn, FieldMapping } from "@/types/siem"
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import EventColumnPicker from "../EventColumnPicker.vue"

const FIELDS: FieldMapping[] = [
	{ field: "timestamp", type: "date" },
	{ field: "agent_name", type: "keyword" },
	{ field: "data_srcip", type: "ip" }
]

function render(props: { current: DisplayColumn[]; personal?: boolean; sourceColumns?: DisplayColumn[] | null }) {
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
})
