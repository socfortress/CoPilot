import type { TalonChatStreamHandlers, TalonChatStreamResult } from "@/api/endpoints/talonChat"
import type { TalonChatChunk, TalonChatUIMessage } from "@/types/talonChat"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
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

	it("shows a reply as it streams: the text and the checked line before the turn ends", async () => {
		talonChat.getMessages.mockResolvedValue(page([]))
		let handlers: TalonChatStreamHandlers | null = null
		talonChat.streamChat.mockImplementation(
			(_id: string, _text: string, h: TalonChatStreamHandlers) =>
				new Promise<void>(() => {
					handlers = h
				})
		)
		const wrapper = await render()
		await type(wrapper, "What happened?")
		await send(wrapper)
		const h = handlers as unknown as TalonChatStreamHandlers
		h.onChunk({ type: "start" })
		h.onChunk({ type: "data-checked", items: [{ kind: "alert", count: 1 }] })
		await flushPromises()
		expect(wrapper.get("[data-testid=talon-message-checked]").text()).toBe("Checked: the alert")
		expect(wrapper.find("[data-testid=talon-message-streaming]").exists()).toBe(true)

		h.onChunk({ type: "data-checked", items: [{ kind: "alert", count: 1 }, { kind: "event_search", count: 2 }] })
		h.onChunk({ type: "text-start", id: "text-1" })
		h.onChunk({ type: "text-delta", id: "text-1", delta: "The task " })
		await flushPromises()
		expect(wrapper.findAll("[data-testid=talon-message-text]").map(t => t.text())).toEqual(["What happened?", "The task"])
		expect(wrapper.get("[data-testid=talon-message-checked]").text()).toBe("Checked: the alert, 2 event searches")

		h.onChunk({ type: "text-delta", id: "text-1", delta: "was scheduled." })
		await flushPromises()
		expect(wrapper.findAll("[data-testid=talon-message-text]")[1]?.text()).toBe("The task was scheduled.")
		// Busy while it streams, and nothing announced token by token.
		expect(wrapper.get("[data-testid=talon-conversation-messages]").attributes("aria-busy")).toBe("true")
		expect(wrapper.get("[data-testid=talon-conversation-messages]").attributes("aria-live")).toBeUndefined()
		expect(wrapper.get("[data-testid=talon-conversation-announcement]").text()).toBe("")
	})

	it("announces once that Talon answered, when the reply ends", async () => {
		talonChat.getMessages.mockResolvedValue(page([]))
		streams([{ type: "text-start", id: "t" }, { type: "text-delta", id: "t", delta: "Done." }, { type: "finish" }])
		const wrapper = await render()
		await type(wrapper, "Hi")
		await send(wrapper)
		expect(wrapper.get("[data-testid=talon-conversation-messages]").attributes("aria-busy")).toBe("false")
		expect(wrapper.get("[data-testid=talon-conversation-announcement]").text()).toBe("Talon has answered.")
	})

	it("ties the composer's counter to its input", async () => {
		talonChat.getMessages.mockResolvedValue(page([]))
		const wrapper = await render()
		const counter = wrapper.get("[data-testid=talon-composer-count]").attributes("id")
		expect(counter).toBeTruthy()
		expect(wrapper.get("[data-testid=talon-composer-input] textarea").attributes("aria-describedby")).toBe(counter)
	})

	it("cuts the reply off when the conversation is left", async () => {
		talonChat.getMessages.mockResolvedValue(page([]))
		const signals: AbortSignal[] = []
		talonChat.streamChat.mockImplementation((_id: string, _t: string, _h: TalonChatStreamHandlers, signal: AbortSignal) => {
			signals.push(signal)
			return new Promise<void>(() => {})
		})
		const wrapper = await render()
		await type(wrapper, "Hi")
		await send(wrapper)
		expect(signals[0]?.aborted).toBe(false)
		wrapper.unmount()
		expect(signals[0]?.aborted).toBe(true)
	})

	it("cuts the reply off when another thread is opened, and lets the new one send", async () => {
		talonChat.getMessages.mockResolvedValue(page([]))
		const signals: AbortSignal[] = []
		talonChat.streamChat.mockImplementation((_id: string, _t: string, _h: TalonChatStreamHandlers, signal: AbortSignal) => {
			signals.push(signal)
			return new Promise<void>(() => {})
		})
		const threadId = ref("th-1")
		const streaming: boolean[] = []
		const host = defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, () =>
					h(TalonConversation, { threadId: threadId.value, onStreaming: (value: boolean) => streaming.push(value) }))
		})
		const wrapper = mount(host, { global: { plugins: [testRouter()] } })
		await flushPromises()
		await wrapper.get("[data-testid=talon-composer-input] textarea").setValue("Hi")
		await wrapper.get("[data-testid=talon-composer]").trigger("submit")
		await flushPromises()
		expect(streaming).toEqual([true])

		talonChat.getMessages.mockResolvedValue(page([], { thread: thread({ id: "th-2" }) }))
		threadId.value = "th-2"
		await flushPromises()
		expect(signals[0]?.aborted).toBe(true)
		expect(streaming).toEqual([true, false])
		expect(wrapper.findAll("[data-testid=talon-message]")).toHaveLength(0)
		expect(wrapper.get("[data-testid=talon-composer-input] textarea").attributes("disabled")).toBeUndefined()
	})

	it("offers no composer on a closed (archived) thread", async () => {
		talonChat.getMessages.mockResolvedValue(page(turn("run-1", "Q", [{ type: "text", text: "A" }]), { thread: thread({ status: "archived" }) }))
		const wrapper = await render()
		expect(wrapper.find("[data-testid=talon-composer]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=talon-conversation-archived]").text()).toBe("This conversation is closed.")
	})

	it("forgets the cached availability when a turn finds the switch off", async () => {
		talonChat.getMessages.mockResolvedValue(page([]))
		streams([], { kind: "refused", status: 403, code: "portal_off" })
		const wrapper = await render()
		expect(talonChat.getAvailability).toHaveBeenCalledTimes(1)
		await type(wrapper, "Hi")
		await send(wrapper)
		await useTalonChatAvailability().isEnabledFor("ACME")
		expect(talonChat.getAvailability).toHaveBeenCalledTimes(2)
	})

	it("keeps a draft card's edits when its turn is read back after the stream", async () => {
		talonChat.getMessages.mockResolvedValueOnce(page([]))
		let handlers: TalonChatStreamHandlers | null = null
		let finish: () => void = () => {}
		talonChat.streamChat.mockImplementation(
			(_id: string, _text: string, h: TalonChatStreamHandlers) =>
				new Promise<void>(resolve => {
					handlers = h
					finish = () => {
						h.onEnd({ kind: "finished" })
						resolve()
					}
				})
		)
		const wrapper = await render()
		await type(wrapper, "Ask the SOC for me")
		await send(wrapper)
		const h = handlers as unknown as TalonChatStreamHandlers
		h.onChunk({ type: "data-soc-draft", draftId: "d-1" })
		h.onChunk({ type: "finish" })
		await flushPromises()
		await wrapper.get("[data-testid=talon-draft-question] textarea").setValue("Edited before the read-back")

		talonChat.getMessages.mockResolvedValueOnce(page(turn("run-3", "Ask the SOC for me", [{ type: "data-soc-draft", data: { id: "d-1" } }])))
		finish()
		await flushPromises()
		expect(talonChat.getMessages).toHaveBeenCalledTimes(2)
		expect((wrapper.get("[data-testid=talon-draft-question] textarea").element as HTMLTextAreaElement).value).toBe(
			"Edited before the read-back"
		)
	})
})
