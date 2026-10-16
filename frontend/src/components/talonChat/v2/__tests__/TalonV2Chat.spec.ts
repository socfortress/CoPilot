/**
 * The v2 chat shell: it lists the caller's threads and opens the newest, starts with the picker
 * when there are none, opens a thread it just created, and drops one it archived.
 */
import type { TalonV2Thread } from "@/types/talonV2"
import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import TalonV2Chat from "../TalonV2Chat.vue"

const listThreads = vi.fn()
const createThread = vi.fn()
const archiveThread = vi.fn()
const renameThread = vi.fn()
const toastError = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonV2: {
			listThreads: (...a: unknown[]) => listThreads(...a),
			createThread: (...a: unknown[]) => createThread(...a),
			archiveThread: (...a: unknown[]) => archiveThread(...a),
			renameThread: (...a: unknown[]) => renameThread(...a)
		}
	}
}))
vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => ({ success: vi.fn(), error: toastError })
}))

const ConversationStub = defineComponent({
	name: "TalonV2Conversation",
	props: { thread: { type: Object, required: true } },
	setup: props => () => h("div", { "data-testid": "conversation" }, (props.thread as TalonV2Thread).id)
})
const PickerStub = defineComponent({
	name: "TalonNewThread",
	props: { creating: Boolean, error: { type: String, default: null }, cancellable: Boolean },
	emits: ["create", "cancel"],
	setup: props => () => h("div", { "data-testid": "picker" }, props.error ?? "")
})

function thread(id: string, extra: Partial<TalonV2Thread> = {}): TalonV2Thread {
	return {
		id,
		title: id,
		customer_code: null,
		status: "active",
		created_at: null,
		updated_at: null,
		archived_at: null,
		accessible: true,
		...extra
	}
}

async function render() {
	const wrapper = mount(TalonV2Chat, {
		global: { stubs: { TalonV2Conversation: ConversationStub, TalonNewThread: PickerStub, Icon: true } }
	})
	await flushPromises()
	return wrapper
}

describe("talon v2 chat shell", () => {
	beforeEach(() => {
		for (const fn of [listThreads, createThread, archiveThread, renameThread, toastError]) fn.mockReset()
	})

	it("lists the active threads and opens the newest", async () => {
		listThreads.mockResolvedValueOnce({ data: { threads: [thread("t1"), thread("t2")], next: null } })
		const wrapper = await render()
		expect(listThreads).toHaveBeenCalledWith({ status: "active", limit: 50, cursor: null }, expect.any(AbortSignal))
		expect(wrapper.get('[data-testid="conversation"]').text()).toBe("t1")
		expect(wrapper.find('[data-testid="picker"]').exists()).toBe(false)
	})

	it("starts with the picker when there is no thread, and opens the one it creates", async () => {
		listThreads.mockResolvedValueOnce({ data: { threads: [], next: null } })
		createThread.mockResolvedValueOnce({ data: thread("new", { customer_code: "ACME" }) })
		const wrapper = await render()
		expect(wrapper.find('[data-testid="picker"]').exists()).toBe(true)

		wrapper.getComponent(PickerStub).vm.$emit("create", { title: null, customer_code: "ACME" })
		await flushPromises()
		expect(createThread).toHaveBeenCalledWith({ title: null, customer_code: "ACME" })
		expect(wrapper.get('[data-testid="conversation"]').text()).toBe("new")
		expect(wrapper.findAll('[data-testid="talon-v2-thread"]').map(r => r.attributes("data-thread-id"))).toEqual([
			"new"
		])
	})

	it("a refused creation stays in the picker with the reason", async () => {
		listThreads.mockResolvedValueOnce({ data: { threads: [], next: null } })
		createThread.mockRejectedValueOnce(
			Object.assign(new Error("x"), {
				isAxiosError: true,
				response: { status: 409, data: { detail: "thread limit reached: archive a thread first" } }
			})
		)
		const wrapper = await render()
		wrapper.getComponent(PickerStub).vm.$emit("create", { title: null, customer_code: null })
		await flushPromises()
		expect(wrapper.get('[data-testid="picker"]').text()).toBe("thread limit reached: archive a thread first")
	})

	it("archiving the open thread drops it and opens the next", async () => {
		listThreads.mockResolvedValueOnce({ data: { threads: [thread("t1"), thread("t2")], next: null } })
		archiveThread.mockResolvedValueOnce({ data: thread("t1", { status: "archived" }) })
		const wrapper = await render()
		const row = wrapper.get('[data-testid="talon-v2-thread"][data-thread-id="t1"]')
		await row.get('[data-testid="talon-v2-thread-archive"]').trigger("click")
		await row.get('[data-testid="talon-v2-archive-confirm"]').trigger("click")
		await flushPromises()
		expect(archiveThread).toHaveBeenCalledWith("t1")
		expect(wrapper.findAll('[data-testid="talon-v2-thread"]').map(r => r.attributes("data-thread-id"))).toEqual([
			"t2"
		])
		expect(wrapper.get('[data-testid="conversation"]').text()).toBe("t2")
	})

	it("a rename shows the new title; a refused one says why", async () => {
		listThreads.mockResolvedValueOnce({ data: { threads: [thread("t1")], next: null } })
		renameThread.mockResolvedValueOnce({ data: thread("t1", { title: "renamed" }) })
		const wrapper = await render()
		await wrapper.get('[data-testid="talon-v2-thread-rename"]').trigger("click")
		await wrapper.get('[data-testid="talon-v2-rename-input"] input').setValue("renamed")
		await wrapper.get('[data-testid="talon-v2-rename-save"]').trigger("click")
		await flushPromises()
		expect(renameThread).toHaveBeenCalledWith("t1", "renamed")
		expect(wrapper.get('[data-testid="talon-v2-thread-title"]').text()).toBe("renamed")

		renameThread.mockRejectedValueOnce(
			Object.assign(new Error("x"), {
				isAxiosError: true,
				response: { status: 422, data: { detail: "invalid request" } }
			})
		)
		await wrapper.get('[data-testid="talon-v2-thread-rename"]').trigger("click")
		await wrapper.get('[data-testid="talon-v2-rename-input"] input').setValue("bad‮title")
		await wrapper.get('[data-testid="talon-v2-rename-save"]').trigger("click")
		await flushPromises()
		expect(toastError).toHaveBeenCalledWith("invalid request")
	})

	it("the archived filter lists archived threads", async () => {
		listThreads
			.mockResolvedValueOnce({ data: { threads: [thread("t1")], next: null } })
			.mockResolvedValueOnce({ data: { threads: [thread("old", { status: "archived" })], next: null } })
		const wrapper = await render()
		await wrapper.get('[data-testid="talon-v2-thread-filter-archived"]').trigger("click")
		await flushPromises()
		expect(listThreads).toHaveBeenLastCalledWith(
			{ status: "archived", limit: 50, cursor: null },
			expect.any(AbortSignal)
		)
		expect(wrapper.get('[data-testid="conversation"]').text()).toBe("old")
	})
})
