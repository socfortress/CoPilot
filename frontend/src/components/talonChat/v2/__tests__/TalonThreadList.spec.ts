/**
 * The thread rail's list: the customer badge or "General", a lock when the customer is no longer
 * the caller's, and rename / archive asked of the parent. Titles are text.
 */
import type { TalonV2Thread } from "@/types/talonV2"
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import TalonThreadList from "../TalonThreadList.vue"

function thread(id: string, extra: Partial<TalonV2Thread> = {}): TalonV2Thread {
	return {
		id,
		title: `thread ${id}`,
		customer_code: null,
		status: "active",
		created_at: null,
		updated_at: null,
		archived_at: null,
		accessible: true,
		...extra
	}
}

const THREADS = [
	thread("a", { customer_code: "ACME" }),
	thread("b"),
	thread("c", { customer_code: "GLOBEX", accessible: false, title: null }),
	thread("d", { title: `<img src=x onerror=alert(1)>`, status: "archived" })
]

function render(props: Partial<InstanceType<typeof TalonThreadList>["$props"]> = {}) {
	return mount(TalonThreadList, { props: { threads: THREADS, ...props }, global: { stubs: { Icon: true } } })
}

function row(wrapper: ReturnType<typeof render>, id: string) {
	return wrapper.get(`[data-testid="talon-v2-thread"][data-thread-id="${id}"]`)
}

describe("talon v2 thread list", () => {
	it("shows each thread's customer, or General, and a lock for an inaccessible one", () => {
		const wrapper = render({ selectedId: "a" })
		const customers = wrapper.findAll('[data-testid="talon-v2-thread-customer"]').map(t => t.text())
		expect(customers).toEqual(["ACME", "General", "GLOBEX", "General"])
		expect(row(wrapper, "c").find('[data-testid="talon-v2-thread-locked"]').exists()).toBe(true)
		expect(row(wrapper, "a").find('[data-testid="talon-v2-thread-locked"]').exists()).toBe(false)
		expect(row(wrapper, "c").get('[data-testid="talon-v2-thread-title"]').text()).toBe("Untitled thread")
		expect(row(wrapper, "a").attributes("aria-current")).toBe("true")
	})

	it("renders a title with markup as text", () => {
		const wrapper = render()
		expect(row(wrapper, "d").get('[data-testid="talon-v2-thread-title"]').text()).toBe(
			"<img src=x onerror=alert(1)>"
		)
		expect(wrapper.find("img").exists()).toBe(false)
	})

	it("a click selects the thread", async () => {
		const wrapper = render()
		await row(wrapper, "b").trigger("click")
		expect(wrapper.emitted("select")).toEqual([[THREADS[1]]])
	})

	it("rename asks the parent with the trimmed title, or null to clear it", async () => {
		const wrapper = render()
		await row(wrapper, "a").get('[data-testid="talon-v2-thread-rename"]').trigger("click")
		await wrapper.get('[data-testid="talon-v2-rename-input"] input').setValue("  ws-1 triage  ")
		await wrapper.get('[data-testid="talon-v2-rename-save"]').trigger("click")
		expect(wrapper.emitted("rename")).toEqual([[THREADS[0], "ws-1 triage"]])
		expect(wrapper.emitted("select")).toBeUndefined()

		await row(wrapper, "b").get('[data-testid="talon-v2-thread-rename"]').trigger("click")
		await wrapper.get('[data-testid="talon-v2-rename-input"] input').setValue("   ")
		await wrapper.get('[data-testid="talon-v2-rename-input"] input').trigger("keydown", { key: "Enter" })
		expect(wrapper.emitted("rename")?.[1]).toEqual([THREADS[1], null])
	})

	it("an unchanged title asks for nothing", async () => {
		const wrapper = render()
		await row(wrapper, "a").get('[data-testid="talon-v2-thread-rename"]').trigger("click")
		await wrapper.get('[data-testid="talon-v2-rename-save"]').trigger("click")
		expect(wrapper.emitted("rename")).toBeUndefined()
	})

	it("archive asks for a confirmation first; an archived thread offers none", async () => {
		const wrapper = render()
		expect(row(wrapper, "d").find('[data-testid="talon-v2-thread-archive"]').exists()).toBe(false)
		await row(wrapper, "a").get('[data-testid="talon-v2-thread-archive"]').trigger("click")
		expect(wrapper.emitted("archive")).toBeUndefined()
		await row(wrapper, "a").get('[data-testid="talon-v2-archive-confirm"]').trigger("click")
		expect(wrapper.emitted("archive")).toEqual([[THREADS[0]]])
		expect(wrapper.emitted("select")).toBeUndefined()
	})

	it("offers more when the list has another page, and says when there is none", async () => {
		const more = render({ hasMore: true })
		await more.get('[data-testid="talon-v2-threads-more"]').trigger("click")
		expect(more.emitted("load-more")).toHaveLength(1)

		const empty = render({ threads: [] })
		expect(empty.find('[data-testid="talon-v2-no-threads"]').exists()).toBe(true)
	})
})
