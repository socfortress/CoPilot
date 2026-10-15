/**
 * How the Talon chat ends a reply.
 *
 * Talon can fail part-way through a reply (a turn limit, a busy conversation, a
 * dropped connection). The chat used to discard the text that had already
 * streamed and show only a generic toast, so the analyst lost the partial answer
 * and never saw why it stopped. These tests pin the replacement: the partial
 * reply is kept, the error's own text is shown in the chat, and the input works
 * again afterwards.
 */

import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import TalonChatContainer from "../TalonChatContainer.vue"
import TalonChatQuery from "../TalonChatQuery.vue"

type StreamMessage = (
	message: string,
	onChunk: (text: string) => void,
	onDone: () => void,
	onError: (error: string) => void,
	signal?: AbortSignal
) => Promise<void>

const streamMessage = vi.fn<StreamMessage>()
const toastError = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talon: {
			streamMessage: (...args: Parameters<StreamMessage>) => streamMessage(...args),
			getSessionContext: async () => ({ data: { input_tokens: null } }),
			resetSession: async () => ({ data: {} })
		}
	}
}))
vi.mock("@/utils/secure-storage", () => ({ secureLocalStorage: () => window.sessionStorage }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "yyyy-MM-dd HH:mm" } }) }))
vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => ({ success: vi.fn(), error: toastError })
}))

// jsdom has no layout, so no `scrollTo`; the chat scrolls to the newest message.
Element.prototype.scrollTo = vi.fn()

const MarkdownStub = defineComponent({
	props: { source: { type: String, default: "" } },
	setup: props => () => h("div", { class: "markdown" }, props.source)
})

function render() {
	return mount(TalonChatContainer, {
		global: { stubs: { Markdown: MarkdownStub, Icon: true, TalonChatExample: true } }
	})
}

async function send(wrapper: ReturnType<typeof render>, text: string) {
	wrapper.findComponent(TalonChatQuery).vm.$emit("message", { input: text })
	await flushPromises()
}

describe("talon chat reply endings", () => {
	beforeEach(() => {
		window.sessionStorage.clear()
		streamMessage.mockReset()
		toastError.mockReset()
	})

	it("keeps the partial reply and shows the error text after it", async () => {
		streamMessage.mockImplementationOnce(async (_message, onChunk, _onDone, onError) => {
			onChunk("Partial ")
			onChunk("reply")
			onError("Talon request failed: turn limit reached: 30 tool calls")
		})
		const wrapper = render()

		await send(wrapper, "investigate host-1")

		const replies = wrapper.findAll(".markdown").map(node => node.text())
		expect(replies).toEqual(["investigate host-1", "Partial reply"])
		const error = wrapper.get("[data-testid='talon-chat-error']")
		expect(error.text()).toContain("Talon request failed: turn limit reached: 30 tool calls")
		expect(wrapper.text().indexOf("Partial reply")).toBeLessThan(wrapper.text().indexOf("turn limit reached"))
		expect(toastError).not.toHaveBeenCalled()
	})

	it("shows an error that arrives before any text", async () => {
		streamMessage.mockImplementationOnce(async (_message, _onChunk, _onDone, onError) => {
			onError("Talon request failed: a reply is still streaming")
		})
		const wrapper = render()

		await send(wrapper, "hello")

		expect(wrapper.findAll(".markdown").map(node => node.text())).toEqual(["hello"])
		expect(wrapper.get("[data-testid='talon-chat-error']").text()).toContain("a reply is still streaming")
	})

	it("leaves the input usable after an error", async () => {
		streamMessage.mockImplementationOnce(async (_message, _onChunk, _onDone, onError) => {
			onError("Talon request failed")
		})
		streamMessage.mockImplementationOnce(async (_message, onChunk, onDone) => {
			onChunk("Second answer")
			onDone()
		})
		const wrapper = render()

		await send(wrapper, "first")
		expect(wrapper.findComponent(TalonChatQuery).props("loading")).toBe(false)

		await send(wrapper, "second")

		expect(streamMessage).toHaveBeenCalledTimes(2)
		expect(wrapper.findAll(".markdown").map(node => node.text())).toEqual(["first", "second", "Second answer"])
	})

	it("shows no error for a reply that finishes", async () => {
		streamMessage.mockImplementationOnce(async (_message, onChunk, onDone) => {
			onChunk("All good")
			onDone()
		})
		const wrapper = render()

		await send(wrapper, "hello")

		expect(wrapper.findAll(".markdown").map(node => node.text())).toEqual(["hello", "All good"])
		expect(wrapper.find("[data-testid='talon-chat-error']").exists()).toBe(false)
	})
})
