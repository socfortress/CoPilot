import { describe, expect, it, vi } from "vitest"
import { effectScope, nextTick, ref } from "vue"
import { usePaginatedLoad } from "../usePaginatedLoad"

/** A list's state and a counting loader, wired through the composable inside a scope. */
function setup(initialPage = 1) {
	const page = ref(initialPage)
	const pageSize = ref(25)
	const filter = ref<string | null>(null)
	const customers = ref<string[] | undefined>(undefined)
	const pagesLoaded: number[] = []
	const load = vi.fn(() => {
		pagesLoaded.push(page.value)
	})

	const scope = effectScope()
	scope.run(() => usePaginatedLoad({ page, resetOn: [pageSize, filter, customers], load }))

	return { page, pageSize, filter, customers, load, pagesLoaded, stop: () => scope.stop() }
}

describe("usePaginatedLoad", () => {
	it("loads once on mount", async () => {
		const { load } = setup()
		await nextTick()
		expect(load).toHaveBeenCalledTimes(1)
	})

	it("mounting on a later page loads that page, not page 1", async () => {
		// Vue's first "previous" value for a multi-source watch is [], which once read as a
		// filter change and sent a list restored on page 3 back to page 1.
		const list = setup(3)
		await nextTick()
		expect(list.page.value).toBe(3)
		expect(list.pagesLoaded).toEqual([3])
	})

	it("loads once when the page changes", async () => {
		const list = setup()
		list.page.value = 2
		await nextTick()
		expect(list.load).toHaveBeenCalledTimes(2)
		expect(list.pagesLoaded).toEqual([1, 2])
	})

	it("a filter change on page 1 loads once and stays on page 1", async () => {
		const list = setup()
		list.filter.value = "OPEN"
		await nextTick()
		expect(list.load).toHaveBeenCalledTimes(2)
		expect(list.page.value).toBe(1)
	})

	it("a filter change on a later page goes back to page 1 and loads once, for page 1", async () => {
		const list = setup(3)
		list.filter.value = "OPEN"
		await nextTick()
		await nextTick()
		expect(list.page.value).toBe(1)
		// Mount (page 3) + the reset (page 1) — never a load for the stale page after the change.
		expect(list.pagesLoaded).toEqual([3, 1])
	})

	it("several changes in the same tick load once", async () => {
		const list = setup(2)
		list.filter.value = "OPEN"
		list.pageSize.value = 50
		list.customers.value = ["ACME"]
		await nextTick()
		await nextTick()
		expect(list.pagesLoaded).toEqual([2, 1])
	})

	it("stops loading once its scope is disposed", async () => {
		const list = setup()
		list.stop()
		list.page.value = 2
		await nextTick()
		expect(list.load).toHaveBeenCalledTimes(1)
	})
})
