import { mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import FileAnalysisBatchList from "../FileAnalysisBatchList.vue"

// Never resolves: the point of these tests is the window BEFORE the jobs arrive,
// which is exactly the state that used to render an empty drawer.
const getJob = vi.fn(() => new Promise(() => {}))

vi.mock("@/api", () => ({ default: { fileAnalysis: { getJob: (...a: unknown[]) => getJob(...(a as [])) } } }))
vi.mock("vue-router", () => ({ useRouter: () => ({ push: vi.fn() }) }))

// The visual shell is irrelevant here; stubbing it keeps the test about the
// loading contract rather than about Naive's card internals.
vi.mock("@/components/common/cards/CardEntity.vue", () => ({
	default: defineComponent({
		name: "CardEntity",
		setup: (_p, { slots }) => () => h("div", { class: "card-entity" }, [slots.header?.(), slots.default?.()])
	})
}))

function mountList(jobIds: string[]) {
	return mount(FileAnalysisBatchList, {
		props: { jobIds, activeJobId: jobIds[0] },
		global: {
			stubs: {
				Icon: true,
				Badge: true,
				"n-tag": true,
				"n-spin": true,
				"n-skeleton": { template: `<span class="n-skeleton" />` }
			}
		}
	})
}

describe("fileAnalysisBatchList while jobs are still loading", () => {
	beforeEach(() => {
		// Block body on purpose: returning mockClear()'s value makes vitest treat the
		// hook as async and time it out.
		getJob.mockClear()
	})

	it("renders one row per job immediately, before any job has answered", async () => {
		const wrapper = mountList(["a", "b", "c"])
		await nextTick()
		expect(wrapper.findAll(".card-entity")).toHaveLength(3)
	})

	// The bug this guards: the list waited for Promise.all, so opening the drawer
	// showed nothing at all and read as a failure rather than as loading.
	it("fills those rows with placeholders rather than leaving them blank", async () => {
		const wrapper = mountList(["a", "b", "c"])
		await nextTick()
		expect(wrapper.findAll(".n-skeleton").length).toBeGreaterThanOrEqual(3)
	})

	it("says it is loading instead of claiming nothing is running", async () => {
		const wrapper = mountList(["a", "b"])
		await nextTick()
		expect(wrapper.text()).toContain("loading")
		expect(wrapper.text()).toContain("2 files analysed together")
	})

	it("asks the backend once per job", async () => {
		mountList(["a", "b", "c"])
		await nextTick()
		expect(getJob).toHaveBeenCalledTimes(3)
	})
})
