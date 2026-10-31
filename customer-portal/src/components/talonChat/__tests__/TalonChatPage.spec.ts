import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import { useAuthStore } from "@/stores/auth"
import TalonChatPage from "../TalonChatPage.vue"
import { testRouter, thread, withProviders } from "./fixtures"

const talonChat = vi.hoisted(() => ({
	getAvailability: vi.fn(),
	listThreads: vi.fn(),
	getMessages: vi.fn(),
	archiveThread: vi.fn()
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

	it("hides itself when the availability route fails", async () => {
		talonChat.getAvailability.mockRejectedValue(new Error("network"))
		const { wrapper } = await render()
		expect(wrapper.find("[data-testid=talon-chat-unavailable]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=talon-thread-list]").exists()).toBe(false)
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
})
