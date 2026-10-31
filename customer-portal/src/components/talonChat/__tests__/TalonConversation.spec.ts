import type { TalonChatStreamHandlers, TalonChatStreamResult } from "@/api/endpoints/talonChat"
import type { TalonChatChunk, TalonChatUIMessage } from "@/types/talonChat"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import i18n from "@/lang"
import { useAuthStore } from "@/stores/auth"
import TalonConversation from "../TalonConversation.vue"
import { draft, testRouter, thread, turn, withProviders } from "./fixtures"

const talonChat = vi.hoisted(() => ({
	getAvailability: vi.fn(),
	getMessages: vi.fn(),
	streamChat: vi.fn(),
	sendFeedback: vi.fn(),
	getDraft: vi.fn()
}))
const aiReports = vi.hoisted(() => ({ getAlertAnalysis: vi.fn(), requestAnalysis: vi.fn() }))
vi.mock("@/api", () => ({ default: { talonChat, aiReports } }))

function page(messages: TalonChatUIMessage[], overrides: Record<string, unknown> = {}) {
	return { data: { thread: thread(), messages, next: null, ...overrides } }
}

/** streamChat that sends `chunks`, then ends with `result`. */
function streams(chunks: TalonChatChunk[], result: TalonChatStreamResult = { kind: "finished" }) {
	talonChat.streamChat.mockImplementation(async (_id: string, _text: string, handlers: TalonChatStreamHandlers) => {
		for (const chunk of chunks) handlers.onChunk(chunk)
		handlers.onEnd(result)
	})
}

async function render() {
	const wrapper = mount(withProviders(TalonConversation, { threadId: "th-1" }), { global: { plugins: [testRouter()] } })
	await flushPromises()
	return wrapper
}

async function type(wrapper: Awaited<ReturnType<typeof render>>, text: string) {
	await wrapper.get("[data-testid=talon-composer-input] textarea").setValue(text)
}

async function send(wrapper: Awaited<ReturnType<typeof render>>) {
	await wrapper.get("[data-testid=talon-composer]").trigger("submit")
	await flushPromises()
}

beforeEach(() => {
	setActivePinia(createPinia())
	useTalonChatAvailability().reset()
	for (const fn of [...Object.values(talonChat), ...Object.values(aiReports)]) fn.mockReset()
	useAuthStore().customers = [{ customer_code: "ACME", customer_name: "Acme Corp" }]
	talonChat.getAvailability.mockResolvedValue({
		data: { customer_code: "ACME", enabled: true, log_search: false, can_draft: true, can_request_analysis: true }
	})
	talonChat.getDraft.mockResolvedValue({ data: draft() })
	aiReports.getAlertAnalysis.mockResolvedValue({
		data: { alert_id: 9, enabled: true, can_request: true, has_analysis: false, investigation: null, report: null, iocs: [] }
	})
})

describe("an Ask Talon conversation", () => {
	it("shows the thread's turns as read back, with the checked line", async () => {
		talonChat.getMessages.mockResolvedValue(
			page(
				turn("run-1", "What happened?", [
					{ type: "text", text: "A scheduled task ran." },
					{ type: "data-checked", id: "checked", data: { items: [{ kind: "alert", count: 1 }] } }
				])
			)
		)
		const wrapper = await render()
		expect(talonChat.getMessages).toHaveBeenCalledWith("th-1", { limit: 20 }, expect.any(AbortSignal))
		expect(wrapper.get("[data-testid=talon-conversation-title]").text()).toBe("Scheduled task on HOST-A")
		const texts = wrapper.findAll("[data-testid=talon-message-text]").map(t => t.text())
		expect(texts).toEqual(["What happened?", "A scheduled task ran."])
		expect(wrapper.get("[data-testid=talon-message-checked]").text()).toBe("Checked: the alert")
	})

	it("streams a reply in as text, then reads the turn back", async () => {
		talonChat.getMessages.mockResolvedValueOnce(page([]))
		streams([
			{ type: "start" },
			{ type: "data-checked", items: [{ kind: "event_search", count: 2 }] },
			{ type: "text-start", id: "text-1" },
			{ type: "text-delta", id: "text-1", delta: "<img src=x onerror=alert(1)>\nNo." },
			{ type: "finish" }
		])
		talonChat.getMessages.mockResolvedValueOnce(
			page(turn("run-7", "Hello?", [{ type: "text", text: "<img src=x onerror=alert(1)>\nNo." }]))
		)
		const wrapper = await render()
		await type(wrapper, "  Hello?  ")
		await send(wrapper)

		expect(talonChat.streamChat).toHaveBeenCalledWith("th-1", "Hello?", expect.any(Object), expect.any(AbortSignal))
		expect(wrapper.find("img").exists()).toBe(false)
		expect(wrapper.findAll("[data-testid=talon-message-text]").map(t => t.text())).toEqual([
			"Hello?",
			"<img src=x onerror=alert(1)>\nNo."
		])
		// Read back: the turn now has its run id, so it can be rated.
		expect(talonChat.getMessages).toHaveBeenCalledTimes(2)
		expect(wrapper.find("[data-testid=talon-feedback-up]").exists()).toBe(true)
		expect((wrapper.get("[data-testid=talon-composer-input] textarea").element as HTMLTextAreaElement).value).toBe("")
	})

	it("says why a turn was refused, by its code in the user's language, and gives the message back", async () => {
		talonChat.getMessages.mockResolvedValue(page([]))
		streams([], { kind: "refused", status: 409, code: "messages_user" })
		i18n.global.locale.value = "fr"
		const wrapper = await render()
		await type(wrapper, "Again")
		await send(wrapper)
		expect(wrapper.get("[data-testid=talon-send-error]").text()).toBe(
			"Vous avez atteint votre nombre quotidien de messages à Talon."
		)
		expect(wrapper.findAll("[data-testid=talon-message]")).toHaveLength(0)
		expect((wrapper.get("[data-testid=talon-composer-input] textarea").element as HTMLTextAreaElement).value).toBe("Again")
		expect(talonChat.getMessages).toHaveBeenCalledTimes(1)
	})

	it("keeps a turn that failed mid-stream on screen with its code", async () => {
		talonChat.getMessages.mockResolvedValue(page([]))
		streams([
			{ type: "text-start", id: "t" },
			{ type: "text-delta", id: "t", delta: "Looking" },
			{ type: "error", code: "portal_off" }
		])
		const wrapper = await render()
		await type(wrapper, "Hi")
		await send(wrapper)
		expect(wrapper.get("[data-testid=talon-message-error]").text()).toBe("Ask Talon is turned off for this organization.")
		expect(talonChat.getMessages).toHaveBeenCalledTimes(1)
	})

	it("sends nothing over the message limit", async () => {
		talonChat.getMessages.mockResolvedValue(page([]))
		const wrapper = await render()
		await type(wrapper, "a".repeat(4001))
		expect(wrapper.get("[data-testid=talon-composer-send]").attributes("disabled")).toBeDefined()
		await send(wrapper)
		expect(talonChat.streamChat).not.toHaveBeenCalled()
	})

	it("records thumbs up and down on a turn by its run id, and undoes a failed one", async () => {
		talonChat.getMessages.mockResolvedValue(page(turn("run-1", "Q", [{ type: "text", text: "A" }])))
		talonChat.sendFeedback.mockResolvedValueOnce({ status: 204 })
		const wrapper = await render()
		await wrapper.get("[data-testid=talon-feedback-up]").trigger("click")
		await flushPromises()
		expect(talonChat.sendFeedback).toHaveBeenCalledWith("th-1", "run-1", "up")
		expect(wrapper.get("[data-testid=talon-feedback-up]").attributes("aria-pressed")).toBe("true")

		talonChat.sendFeedback.mockRejectedValueOnce({ response: { status: 404, data: { code: "thread_not_found" } } })
		await wrapper.get("[data-testid=talon-feedback-down]").trigger("click")
		await flushPromises()
		expect(talonChat.sendFeedback).toHaveBeenLastCalledWith("th-1", "run-1", "down")
		expect(wrapper.get("[data-testid=talon-feedback-up]").attributes("aria-pressed")).toBe("true")
	})

	it("shows the cards to a user who may change the customer's data", async () => {
		talonChat.getMessages.mockResolvedValue(
			page(
				turn("run-1", "Q", [
					{ type: "data-soc-draft", data: { id: "d-1" } },
					{ type: "data-ai-analysis-offer", data: { alert_id: 9 } }
				])
			)
		)
		const wrapper = await render()
		expect(wrapper.find("[data-testid=talon-draft-form]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=talon-analysis-offer]").exists()).toBe(true)
	})

	it("hides both cards from a read-only user, who may still chat", async () => {
		useAuthStore().customers = [{ customer_code: "ACME", customer_name: "Acme Corp", read_only: true }]
		talonChat.getMessages.mockResolvedValue(
			page(
				turn("run-1", "Q", [
					{ type: "text", text: "Drafted." },
					{ type: "data-soc-draft", data: { id: "d-1" } },
					{ type: "data-ai-analysis-offer", data: { alert_id: 9 } }
				])
			)
		)
		const wrapper = await render()
		expect(wrapper.find("[data-testid=talon-draft-card]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=talon-analysis-offer]").exists()).toBe(false)
		expect(talonChat.getDraft).not.toHaveBeenCalled()
		expect(wrapper.find("[data-testid=talon-composer]").exists()).toBe(true)
	})

	it("says why the conversation can't be read, by code", async () => {
		talonChat.getMessages.mockRejectedValue({ response: { status: 403, data: { detail: "x", code: "access_removed" } } })
		const wrapper = await render()
		expect(wrapper.get("[data-testid=talon-conversation-load-error]").text()).toContain(
			"Your access to this conversation's organization was removed."
		)
	})

	it("offers no composer for a conversation that isn't available any more", async () => {
		talonChat.getMessages.mockResolvedValue(page([], { thread: thread({ accessible: false }) }))
		const wrapper = await render()
		expect(wrapper.find("[data-testid=talon-composer]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=talon-conversation-not-accessible]").exists()).toBe(true)
	})
})
