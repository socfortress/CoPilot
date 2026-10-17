import type { DisplayColumn } from "@/types/siem"
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import { resolveColumns } from "../eventColumns"
import EventColumnsPreview from "../EventColumnsPreview.vue"

function render(picked: DisplayColumn[] | null, timeField = "timestamp") {
	return mount(EventColumnsPreview, {
		props: { columns: resolveColumns(picked, null, timeField), timeField, title: "Network" }
	})
}

function rows(wrapper: ReturnType<typeof render>) {
	return wrapper
		.findAll("[data-testid=columns-preview-column]")
		.map(row => row.findAll("span").map(cell => cell.text()))
}

describe("eventColumnsPreview", () => {
	it("lists every column in order, with its header and the field it reads", () => {
		const columns = ["a", "b", "c", "d", "e", "f", "g"].map(key => ({
			key: `data_${key}`,
			label: key.toUpperCase()
		}))
		const wrapper = render(columns)
		expect(wrapper.text()).toContain("Network")
		expect(wrapper.text()).toContain("7 columns")
		expect(rows(wrapper)).toEqual(columns.map((column, i) => [String(i + 1), column.label, column.key]))
	})

	it("names the field behind each column of the default layout", () => {
		expect(rows(render(null, "@timestamp"))).toEqual([
			["1", "Timestamp", "@timestamp"],
			["2", "Level", "rule_level"],
			["3", "Source", "agent_name"],
			["4", "Rule", "rule_description"]
		])
	})

	it("counts one column in the singular", () => {
		expect(render([{ key: "agent_name", label: "Host" }]).text()).toContain("1 column")
	})
})
