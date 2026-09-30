import type { KeyValueFilterModel } from "../KeyValueFilter.vue"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider, NSelect } from "naive-ui"
import { describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick, ref } from "vue"
import KeyValueFilter from "../KeyValueFilter.vue"

interface FilterProps {
	loadOptions: () => Promise<Record<string, string[]>>
	searchKey?: string
	search?: (term: string | null, signal: AbortSignal) => Promise<string[]>
}

function mountFilter(props: FilterProps) {
	const model = ref<KeyValueFilterModel>({ key: null, value: null })
	const loaded = vi.fn()
	const wrapper = mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, () =>
					h(KeyValueFilter, {
						"value": model.value,
						"onUpdate:value": (value: KeyValueFilterModel) => (model.value = value),
						"onLoaded": loaded,
						"testid": "things",
						...props
					}))
		})
	)
	const selects = () => wrapper.findAllComponents(NSelect)
	const options = (index: number) => (selects()[index]!.props("options") as { value: string }[]).map(o => o.value)
	return { wrapper, model, loaded, selects, options }
}

describe("keyValueFilter", () => {
	it("offers the keys that have values, and those values for the chosen key", async () => {
		const loadOptions = vi.fn().mockResolvedValue({ statuses: ["OPEN", "CLOSED"], assigned_to: [] })
		const { model, loaded, options, selects } = mountFilter({ loadOptions })
		await flushPromises()

		expect(loadOptions).toHaveBeenCalledTimes(1)
		expect(loaded).toHaveBeenCalledWith({ statuses: ["OPEN", "CLOSED"], assigned_to: [] })
		expect(options(0)).toEqual(["statuses"])
		expect(selects()[0]!.attributes("data-testid")).toBe("things-filter-key")

		model.value.key = "statuses"
		await nextTick()
		expect(options(1)).toEqual(["OPEN", "CLOSED"])
	})

	it("clears the value when the key changes", async () => {
		const { model } = mountFilter({ loadOptions: vi.fn().mockResolvedValue({ statuses: ["OPEN"], tags: ["x"] }) })
		await flushPromises()

		model.value.key = "statuses"
		await nextTick()
		model.value.value = "OPEN"
		model.value.key = "tags"
		await flushPromises()
		expect(model.value.value).toBeNull()
	})

	it("always offers the search key and searches its values on the server", async () => {
		const search = vi.fn().mockResolvedValue(["host-a1", "host-a2"])
		const { model, options } = mountFilter({
			loadOptions: vi.fn().mockResolvedValue({ sources: ["wazuh"] }),
			searchKey: "assets",
			search
		})
		await flushPromises()
		expect(options(0)).toEqual(["sources", "assets"])

		model.value.key = "assets"
		await flushPromises()
		expect(search).toHaveBeenCalledWith(null, expect.any(AbortSignal))
		expect(options(1)).toEqual(["host-a1", "host-a2"])
	})
})
