import type { TalonChatStreamHandlers } from "@/api/endpoints/talonChat"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import { useAuthStore } from "@/stores/auth"
import TalonChatPage from "../TalonChatPage.vue"
import TalonConversation from "../TalonConversation.vue"
import TalonThreadList from "../TalonThreadList.vue"
import { testRouter, thread, withProviders } from "./fixtures"

const talonChat = vi.hoisted(() => ({
	getAvailability: vi.fn(),
	listThreads: vi.fn(),
	getMessages: vi.fn(),
	archiveThread: vi.fn(),
	streamChat: vi.fn()
}))
vi.mock("@/api", () => ({ default: { talonChat } }))

function availability(enabledFor: string[]) {
	talonChat.getAvailability.mockImplementation((code?: string) =>
		Promise.resolve({
			data: {
				customer_code: code ?? null,
				enabled: code ? enabledFor.includes(code) : enabledFor.length > 0,
				log_search: false,
				can_draft: true,
				can_request_analysis: true
			}
		})
	)
}

async function render(path = "/talon") {
	const router = testRouter()
	await router.push(path)
	const wrapper = mount(withProviders(TalonChatPage), { global: { plugins: [router] } })
	await flushPromises()
	return { wrapper, router }
}

beforeEach(() => {
	setActivePinia(createPinia())
	useTalonChatAvailability().reset()
	for (const fn of Object.values(talonChat)) fn.mockReset()
	useAuthStore().customers = [
		{ customer_code: "ACME", customer_name: "Acme Corp" },
		{ customer_code: "BETA", customer_name: "Beta Ltd" }
	]
	talonChat.listThreads.mockResolvedValue({ data: { threads: [thread()], next: null } })
	talonChat.getMessages.mockResolvedValue({ data: { thread: thread(), messages: [], next: null } })
})

describe("the Ask Talon page", () => {
	it("says Ask Talon isn't available when the route says it is off, and loads nothing", async () => {
		availability([])
		const { wrapper } = await render()
		expect(wrapper.get("[data-testid=talon-chat-unavailable]").text()).toContain("Ask Talon isn't available")
		expect(talonChat.listThreads).not.toHaveBeenCalled()
	})

	it("says it couldn't check, not that it is off, when the availability route fails; and tries again", async () => {
		talonChat.getAvailability.mockRejectedValue(new Error("network"))
		const { wrapper } = await render()
		expect(wrapper.get("[data-testid=talon-chat-check-failed]").text()).toContain("Ask Talon couldn't be checked")
		expect(wrapper.find("[data-testid=talon-chat-unavailable]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=talon-thread-list]").exists()).toBe(false)

		availability(["ACME"])
		await wrapper.get("[data-testid=talon-chat-check-retry]").trigger("click")
		await flushPromises()
		expect(wrapper.find("[data-testid=talon-thread-list]").exists()).toBe(true)
	})

	it("ignores a malformed thread id in the address", async () => {
		availability(["ACME"])
		const { wrapper } = await render("/talon?thread=..%2F..%2Fadmin")
		expect(talonChat.getMessages).not.toHaveBeenCalled()
		expect(wrapper.find("[data-testid=talon-conversation]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=talon-new-thread]").exists()).toBe(true)
	})

	it("names the conversation on its actions button", async () => {
		availability(["ACME"])
		const { wrapper } = await render()
		expect(wrapper.get("[data-testid=talon-thread-actions-th-1]").attributes("aria-label")).toBe(
			"Actions for: Scheduled task on HOST-A"
		)
	})

	it("lists the closed conversations on their own, read only and without actions", async () => {
		availability(["ACME"])
		const { wrapper } = await render()
		talonChat.listThreads.mockResolvedValue({
			data: { threads: [thread({ id: "th-9", title: "Old one", status: "archived", archived_at: "2026-10-31T10:00:00Z" })], next: null }
		})
		await wrapper.get("[data-testid=talon-thread-filter-archived]").trigger("click")
		await flushPromises()
		expect(talonChat.listThreads).toHaveBeenLastCalledWith({ status: "archived", limit: 20, cursor: null }, expect.any(AbortSignal))
		expect(wrapper.get("[data-testid=talon-thread-filter-archived]").classes()).toContain("n-tabs-tab--active")
		expect(wrapper.find("[data-testid=talon-thread-th-1]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=talon-thread-th-9]").text()).toContain("Old one")
		expect(wrapper.find("[data-testid=talon-thread-actions-th-9]").exists()).toBe(false)

		talonChat.listThreads.mockResolvedValue({ data: { threads: [], next: null } })
		await wrapper.get("[data-testid=talon-thread-filter-active]").trigger("click")
		await flushPromises()
		expect(talonChat.listThreads).toHaveBeenLastCalledWith({ status: "active", limit: 20, cursor: null }, expect.any(AbortSignal))
		expect(wrapper.get("[data-testid=talon-thread-list-empty]").text()).toContain("No conversations yet.")
	})

	it("searches the listed conversations by title and organization", async () => {
		availability(["ACME"])
		talonChat.listThreads.mockResolvedValue({
			data: { threads: [thread(), thread({ id: "th-2", title: "Phishing click", customer_code: "BETA" })], next: null }
		})
		const { wrapper } = await render()
		const search = wrapper.get("[data-testid=talon-thread-search] input")
		await search.setValue("phish")
		expect(wrapper.find("[data-testid=talon-thread-th-1]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=talon-thread-th-2]").exists()).toBe(true)
		await search.setValue("acme corp")
		expect(wrapper.find("[data-testid=talon-thread-th-1]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=talon-thread-th-2]").exists()).toBe(false)
		await search.setValue("nothing like it")
		expect(wrapper.get("[data-testid=talon-thread-no-match]").text()).toBe("No conversation matches “nothing like it”.")
	})

	it("closes the open conversation from its own menu, as from its row", async () => {
		availability(["ACME"])
		talonChat.archiveThread.mockResolvedValue({ data: thread({ status: "archived", archived_at: "2026-10-31T10:00:00Z" }) })
		const { wrapper, router } = await render("/talon?thread=th-1")
		expect(wrapper.find("[data-testid=talon-conversation-actions]").exists()).toBe(true)
		wrapper.findComponent(TalonConversation).vm.$emit("archive", "th-1")
		await flushPromises()
		expect(talonChat.archiveThread).toHaveBeenCalledWith("th-1")
		expect(router.currentRoute.value.query.thread).toBeUndefined()
	})

	it("goes back to the list from a conversation, taking it out of the address", async () => {
		availability(["ACME"])
		const { wrapper, router } = await render("/talon?thread=th-1")
		expect(wrapper.get("[data-testid=talon-inbox]").classes()).toContain("has-detail")
		await wrapper.get("[data-testid=talon-inbox-back]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query.thread).toBeUndefined()
		expect(wrapper.get("[data-testid=talon-inbox]").classes()).not.toContain("has-detail")
	})

	it("keeps a streaming reply's conversation open: no new conversation, no other thread, no close", async () => {
		availability(["ACME"])
		talonChat.listThreads.mockResolvedValue({ data: { threads: [thread(), thread({ id: "th-2", title: "Other" })], next: null } })
		let finish: (() => void) | null = null
		talonChat.streamChat.mockImplementation(
			(_id: string, _text: string, handlers: TalonChatStreamHandlers, signal: AbortSignal) =>
				new Promise<void>(resolve => {
					handlers.onChunk({ type: "text-start", id: "t" })
					handlers.onChunk({ type: "text-delta", id: "t", delta: "Working" })
					finish = () => {
						handlers.onEnd({ kind: signal.aborted ? "aborted" : "finished" })
						resolve()
					}
				})
		)
		const { wrapper, router } = await render("/talon?thread=th-1")
		await wrapper.get("[data-testid=talon-composer-input] textarea").setValue("Hi")
		await wrapper.get("[data-testid=talon-composer]").trigger("submit")
		await flushPromises()

		expect(wrapper.get("[data-testid=talon-thread-new]").attributes("disabled")).toBeDefined()
		expect(wrapper.get("[data-testid=talon-thread-th-2]").attributes("disabled")).toBeDefined()
		expect(wrapper.get("[data-testid=talon-thread-actions-th-1]").attributes("disabled")).toBeDefined()
		expect(wrapper.get("[data-testid=talon-inbox-back]").attributes("disabled")).toBeDefined()
		await wrapper.get("[data-testid=talon-thread-new]").trigger("click")
		await wrapper.get("[data-testid=talon-thread-th-2]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query.thread).toBe("th-1")
		expect(wrapper.find("[data-testid=talon-conversation]").exists()).toBe(true)
		expect(wrapper.text()).toContain("Working")

		;(finish as unknown as () => void)()
		await flushPromises()
		expect(wrapper.get("[data-testid=talon-thread-new]").attributes("disabled")).toBeUndefined()
	})

	it("shows the conversations, the review notice and what Talon can't do", async () => {
		availability(["ACME"])
		const { wrapper } = await render()
		expect(talonChat.listThreads).toHaveBeenCalledWith({ status: "active", limit: 20, cursor: null }, expect.any(AbortSignal))
		expect(wrapper.get("[data-testid=talon-chat-review-notice]").text()).toBe("Chats may be reviewed by your SOC.")
		expect(wrapper.get("[data-testid=talon-chat-no-actions]").text()).toContain("Talon can't take actions.")
		expect(wrapper.get("[data-testid=talon-thread-th-1]").text()).toContain("Scheduled task on HOST-A")
	})

	it("offers a new conversation only for the organizations with Ask Talon on", async () => {
		availability(["ACME"])
		const { wrapper } = await render()
		// One of the two has it on: preselected, nothing to choose.
		expect(wrapper.get("[data-testid=talon-new-thread-customer]").text()).toBe("Acme Corp")
	})

	it("opens the conversation in the address", async () => {
		availability(["ACME"])
		const { wrapper, router } = await render()
		await wrapper.get("[data-testid=talon-thread-th-1]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query.thread).toBe("th-1")
		expect(wrapper.find("[data-testid=talon-conversation]").exists()).toBe(true)
		expect(talonChat.getMessages).toHaveBeenCalledWith("th-1", { limit: 20 }, expect.any(AbortSignal))
	})

	it.each(["archived", "deleted"] as const)("drops a closed conversation (%s) from the list and the address", async status => {
		availability(["ACME"])
		talonChat.listThreads.mockResolvedValue({ data: { threads: [thread(), thread({ id: "th-2", title: "Other" })], next: null } })
		talonChat.archiveThread.mockResolvedValue({ data: thread({ status, archived_at: "2026-10-31T10:00:00Z" }) })
		const { wrapper, router } = await render("/talon?thread=th-1")
		expect(wrapper.find("[data-testid=talon-conversation]").exists()).toBe(true)

		wrapper.findComponent(TalonThreadList).vm.$emit("archive", "th-1")
		await flushPromises()
		expect(talonChat.archiveThread).toHaveBeenCalledWith("th-1")
		expect(wrapper.find("[data-testid=talon-thread-th-1]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=talon-thread-th-2]").exists()).toBe(true)
		expect(router.currentRoute.value.query.thread).toBeUndefined()
		expect(wrapper.find("[data-testid=talon-conversation]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=talon-new-thread]").exists()).toBe(true)
	})
})
