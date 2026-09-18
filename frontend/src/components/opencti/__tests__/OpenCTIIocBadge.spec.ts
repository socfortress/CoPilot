import type { OpenCTIObservable, OpenCTIObservableLookup } from "@/types/opencti"
import { mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ref } from "vue"
import OpenCTIIocBadge from "../OpenCTIIocBadge.vue"

const available = ref(true)
const loading = ref(false)
const error = ref(false)
const result = ref<OpenCTIObservableLookup | null>(null)
const retry = vi.fn()

vi.mock("@/composables/useOpenCTIAvailability", () => ({
	useOpenCTIAvailability: () => ({ available })
}))

vi.mock("@/composables/useOpenCTIIocLookup", () => ({
	useOpenCTIIocLookup: () => ({ loading, error, result, retry })
}))

function observable(over: Partial<OpenCTIObservable>): OpenCTIObservable {
	return {
		id: "o",
		standard_id: null,
		entity_type: "Domain-Name",
		created_at: null,
		updated_at: null,
		created_by: null,
		labels: [],
		markings: [],
		value: "evil.com",
		description: null,
		score: null,
		file_name: null,
		hashes: [],
		indicators: [],
		indicators_count: 0,
		reports: [],
		reports_count: 0,
		...over
	}
}

function render() {
	return mount(OpenCTIIocBadge, {
		props: { value: "evil.com" },
		global: { stubs: { OpenCTILookupResult: true, NModal: true } }
	})
}

describe("openCTIIocBadge", () => {
	beforeEach(() => {
		available.value = true
		loading.value = false
		error.value = false
		result.value = null
	})

	it("renders nothing without a verified OpenCTI connector", () => {
		available.value = false
		expect(render().text()).toBe("")
	})

	it("shows that it is checking", () => {
		loading.value = true
		expect(render().text()).toContain("checking")
	})

	it("says not found plainly", () => {
		result.value = { value: "evil.com", found: false, total: 0, observables: [] }
		expect(render().text()).toContain("not found")
	})

	it("summarises across every matching observable", () => {
		result.value = {
			value: "evil.com",
			found: true,
			total: 2,
			observables: [
				observable({
					id: "a",
					score: 60,
					reports_count: 1,
					labels: [
						{ value: "botnet", color: null },
						{ value: "mirai", color: null }
					]
				}),
				observable({
					id: "b",
					entity_type: "Hostname",
					score: 80,
					reports_count: 3,
					labels: [
						{ value: "mirai", color: null },
						{ value: "c2", color: null }
					]
				})
			]
		}
		const text = render().text()
		expect(text).toContain("Known")
		expect(text).toContain("score 80")
		expect(text).toContain("3 reports")
		expect(text).toContain("botnet, mirai")
		expect(text).toContain("+1")
	})

	it("offers a retry after a failed lookup", async () => {
		error.value = true
		const wrapper = render()
		expect(wrapper.text()).toContain("retry")
		await wrapper.find(".badge").trigger("click")
		expect(retry).toHaveBeenCalled()
	})
})
