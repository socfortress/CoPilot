/**
 * One v2 thread's conversation: history from the read-back (paged by cursor), new turns from the
 * stream, and the refusals the UI must tell apart: 409 "waiting for a decision" (the message goes
 * back to the composer), the two 403s with their fixed texts (the composer disabled), a thread
 * whose customer is gone (not even read), an archived thread (read, not continued). Every text
 * from talon-analyst renders as text.
 */
import type { TalonV2StreamHandlers } from "@/api/endpoints/talonV2"
import type { TalonV2MessagesPage, TalonV2Thread } from "@/types/talonV2"
import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { NOTICE_ARCHIVED, NOTICE_PENDING, NOTICE_REVOKED, NOTICE_TAGS_NARROWED } from "../notices"
import TalonV2Conversation from "../TalonV2Conversation.vue"

type StreamChat = (
	threadId: string,
	body: { message: string; message_id?: string },
	handlers: TalonV2StreamHandlers,
	signal?: AbortSignal
) => Promise<void>

const getMessages = vi.fn()
const streamChat = vi.fn<StreamChat>()

vi.mock("@/api", () => ({
	default: {
		talonV2: {
			getMessages: (...args: unknown[]) => getMessages(...args),
			streamChat: (...args: Parameters<StreamChat>) => streamChat(...args)
		}
	}
}))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "yyyy-MM-dd HH:mm" } }) }))

Element.prototype.scrollTo = vi.fn()

const MarkdownStub = defineComponent({
	name: "Markdown",
	props: { source: { type: String, default: "" } },
	setup: props => () => h("div", { class: "markdown-stub" }, props.source)
})

const HOSTILE = `<img src=x onerror="alert(1)"> **bold** [x](https://evil.invalid)`

const THREAD: TalonV2Thread = {
	id: "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e",
	title: "ws-1 triage",
	customer_code: "ACME",
	status: "active",
	created_at: "2026-10-16T08:00:00+00:00",
	updated_at: "2026-10-16T08:00:00+00:00",
	archived_at: null,
	accessible: true,
	context_tokens: 500
}

function turn(run: string, prompt: string, reply: string) {
	return [
		{ id: `${run}-user`, role: "user", parts: [{ type: "text", text: prompt, state: "done" }], metadata: {} },
		{
			id: `${run}-assistant`,
			role: "assistant",
			parts: [{ type: "text", text: reply, state: "done" }],
			metadata: { status: "completed" }
		}
	]
}

function page(messages: unknown[], next: string | null = null, contextTokens = 883): { data: TalonV2MessagesPage } {
	return {
		data: { thread: { ...THREAD, context_tokens: contextTokens }, messages, next } as TalonV2MessagesPage
	}
}

function axiosError(status: number, data: unknown) {
	return Object.assign(new Error("Request failed"), { isAxiosError: true, response: { status, data } })
}

function render(thread: TalonV2Thread = THREAD) {
	return mount(TalonV2Conversation, {
		props: { thread },
		global: { stubs: { Markdown: MarkdownStub, Icon: true } }
	})
}

async function type(wrapper: ReturnType<typeof render>, text: string) {
	await wrapper.get("textarea").setValue(text)
}

async function send(wrapper: ReturnType<typeof render>, text: string) {
	await type(wrapper, text)
	await wrapper.get('[data-testid="talon-v2-send"]').trigger("click")
	await flushPromises()
}

function texts(wrapper: ReturnType<typeof render>) {
	return wrapper.findAll('[data-testid="talon-v2-message"]').map(m => `${m.attributes("data-role")}: ${m.text()}`)
}

describe("talon v2 conversation", () => {
	beforeEach(() => {
		getMessages.mockReset()
		streamChat.mockReset()
	})

	it("renders the thread's newest page from the read-back", async () => {
		getMessages.mockResolvedValueOnce(page(turn("r1", "check ws-1", "ws-1 is clean")))
		const wrapper = render()
		await flushPromises()

		expect(getMessages).toHaveBeenCalledWith(THREAD.id, { limit: 20 }, expect.any(AbortSignal))
		expect(texts(wrapper)).toEqual(["user: check ws-1", "assistant: Talon:ws-1 is clean"])
		expect(wrapper.get('[data-testid="talon-v2-context"]').text()).toBe("context 883")
		expect(wrapper.find('[data-testid="talon-v2-load-older"]').exists()).toBe(false)
	})

	it("loads older turns by cursor, before the ones shown", async () => {
		getMessages
			.mockResolvedValueOnce(page(turn("r2", "second", "two"), "cursor-1"))
			.mockResolvedValueOnce(page(turn("r1", "first", "one"), null))
		const wrapper = render()
		await flushPromises()

		await wrapper.get('[data-testid="talon-v2-load-older"]').trigger("click")
		await flushPromises()
		expect(getMessages).toHaveBeenLastCalledWith(THREAD.id, { limit: 20, before: "cursor-1" })
		expect(texts(wrapper)).toEqual(["user: first", "assistant: Talon:one", "user: second", "assistant: Talon:two"])
		expect(wrapper.find('[data-testid="talon-v2-load-older"]').exists()).toBe(false)
	})

	it("streams a new turn into the same rendering, and reports the activity", async () => {
		getMessages.mockResolvedValueOnce(page([]))
		streamChat.mockImplementationOnce(async (_id, _body, handlers) => {
			handlers.onChunk({ type: "text-start", id: "text-1" })
			handlers.onChunk({ type: "text-delta", id: "text-1", delta: "Checking. " })
			handlers.onChunk({ type: "tool-input-start", toolCallId: "c1", toolName: "lookup" })
			handlers.onChunk({
				type: "tool-input-available",
				toolCallId: "c1",
				toolName: "lookup",
				input: { host: "ws-1" }
			})
			handlers.onChunk({
				type: "tool-output-available",
				toolCallId: "c1",
				output: { status: "done", spilled: false }
			})
			handlers.onChunk({
				type: "data-usage",
				data: {
					input_tokens: 9,
					output_tokens: 2,
					requests: 1,
					tool_calls: 1,
					context_tokens: 2400,
					cost_usd: "0"
				}
			})
			handlers.onChunk({ type: "finish" })
			handlers.onEnd({ kind: "finished" })
		})
		const wrapper = render()
		await flushPromises()
		await send(wrapper, "  check ws-1  ")

		const [threadId, body] = streamChat.mock.calls[0]
		expect(threadId).toBe(THREAD.id)
		expect(body.message).toBe("check ws-1")
		expect(body.message_id).toMatch(/^copilot-[\w-]+$/)
		const [user, reply] = wrapper.findAll('[data-testid="talon-v2-message"]')
		expect(user.text()).toContain("check ws-1")
		expect(reply.attributes("data-status")).toBe("completed")
		expect(reply.get('[data-testid="talon-v2-tool"]').attributes("data-state")).toBe("output-available")
		expect(wrapper.get('[data-testid="talon-v2-context"]').text()).toBe("context 2k")
		expect(wrapper.emitted("activity")).toEqual([[{ id: THREAD.id, context_tokens: 2400 }]])
		expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe("")
	})

	it("an error after some text keeps the text and shows talon-analyst's fixed text", async () => {
		getMessages.mockResolvedValueOnce(page([]))
		streamChat.mockImplementationOnce(async (_id, _body, handlers) => {
			handlers.onChunk({ type: "text-delta", id: "text-1", delta: "partial " })
			handlers.onChunk({ type: "error", errorText: "Talon request failed: turn limit reached: 30 tool calls" })
			handlers.onChunk({ type: "finish", finishReason: "error" })
			handlers.onEnd({ kind: "finished" })
		})
		const wrapper = render()
		await flushPromises()
		await send(wrapper, "go")

		const reply = wrapper.findAll('[data-testid="talon-v2-message"]')[1]
		expect(reply.attributes("data-status")).toBe("failed")
		expect(reply.text()).toContain("partial")
		expect(reply.get('[data-testid="talon-v2-error"]').text()).toBe(
			"Talon request failed: turn limit reached: 30 tool calls"
		)
		expect(wrapper.emitted("activity")).toBeUndefined()
	})

	it("409: waiting for a decision; the message goes back to the composer", async () => {
		getMessages.mockResolvedValueOnce(page([]))
		streamChat.mockImplementationOnce(async (_id, _body, handlers) =>
			handlers.onEnd({
				kind: "refused",
				status: 409,
				detail: "an action in this thread is waiting for a decision in CoPilot"
			})
		)
		const wrapper = render()
		await flushPromises()
		await send(wrapper, "and now?")

		expect(wrapper.get('[data-testid="talon-v2-notice"]').text()).toBe(NOTICE_PENDING)
		expect(NOTICE_PENDING).toMatch(/waiting for a decision/i)
		expect(wrapper.findAll('[data-testid="talon-v2-message"]')).toHaveLength(0)
		const textarea = wrapper.get("textarea").element as HTMLTextAreaElement
		expect(textarea.value).toBe("and now?")
		expect(textarea.disabled).toBe(false)
	})

	it.each([
		["access to this thread's customer was removed", NOTICE_REVOKED],
		["your alert access changed since this thread began; start a new thread", NOTICE_TAGS_NARROWED]
	])("a 403 on the chat (%s) shows its fixed text and disables the composer", async (detail, notice) => {
		getMessages.mockResolvedValueOnce(page([]))
		streamChat.mockImplementationOnce(async (_id, _body, handlers) =>
			handlers.onEnd({ kind: "refused", status: 403, detail })
		)
		const wrapper = render()
		await flushPromises()
		await send(wrapper, "hello")

		expect(wrapper.get('[data-testid="talon-v2-notice"]').text()).toBe(notice)
		expect((wrapper.get("textarea").element as HTMLTextAreaElement).disabled).toBe(true)
		expect(wrapper.get('[data-testid="talon-v2-send"]').attributes("disabled")).toBeDefined()
	})

	it.each([
		["access to this thread's customer was removed", NOTICE_REVOKED],
		["your alert access changed since this thread began; start a new thread", NOTICE_TAGS_NARROWED]
	])("a 403 on the read-back (%s) shows its fixed text and disables the composer", async (detail, notice) => {
		getMessages.mockRejectedValueOnce(axiosError(403, { detail }))
		const wrapper = render()
		await flushPromises()

		expect(wrapper.get('[data-testid="talon-v2-notice"]').text()).toBe(notice)
		expect(wrapper.findAll('[data-testid="talon-v2-message"]')).toHaveLength(0)
		expect((wrapper.get("textarea").element as HTMLTextAreaElement).disabled).toBe(true)
	})

	it("a thread whose customer is gone isn't read, and can't be continued", async () => {
		const wrapper = render({ ...THREAD, accessible: false })
		await flushPromises()

		expect(getMessages).not.toHaveBeenCalled()
		expect(wrapper.get('[data-testid="talon-v2-notice"]').text()).toBe(NOTICE_REVOKED)
		expect((wrapper.get("textarea").element as HTMLTextAreaElement).disabled).toBe(true)
	})

	it("an archived thread is read but not continued", async () => {
		getMessages.mockResolvedValueOnce(page(turn("r1", "q", "a")))
		const wrapper = render({ ...THREAD, status: "archived", archived_at: "2026-10-16T09:00:00+00:00" })
		await flushPromises()

		expect(texts(wrapper)).toHaveLength(2)
		expect(wrapper.get('[data-testid="talon-v2-notice"]').text()).toBe(NOTICE_ARCHIVED)
		expect((wrapper.get("textarea").element as HTMLTextAreaElement).disabled).toBe(true)
	})

	it("a thread that is gone says so and tells the list", async () => {
		getMessages.mockRejectedValueOnce(axiosError(404, { detail: "thread not found" }))
		const wrapper = render()
		await flushPromises()

		expect(wrapper.get('[data-testid="talon-v2-notice"]').attributes("data-kind")).toBe("gone")
		expect(wrapper.emitted("gone")).toEqual([[THREAD.id]])
	})

	it("a refusal's detail and a load error are shown as text", async () => {
		getMessages.mockRejectedValueOnce(axiosError(400, { detail: HOSTILE }))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-v2-load-error"]').text()).toContain(HOSTILE)

		getMessages.mockResolvedValueOnce(page([]))
		await wrapper.get('[data-testid="talon-v2-load-error"] button').trigger("click")
		await flushPromises()
		streamChat.mockImplementationOnce(async (_id, _body, handlers) =>
			handlers.onEnd({ kind: "refused", status: 400, detail: HOSTILE })
		)
		await send(wrapper, "x")
		expect(wrapper.get('[data-testid="talon-v2-notice"]').text()).toBe(HOSTILE)
		expect(wrapper.find("img").exists()).toBe(false)
		expect(wrapper.find("strong").exists()).toBe(false)
		expect(wrapper.find("a").exists()).toBe(false)
	})

	it("stop aborts the stream; the reply is kept as cut off", async () => {
		getMessages.mockResolvedValueOnce(page([]))
		streamChat.mockImplementationOnce(
			(_id, _body, handlers, signal) =>
				new Promise<void>(resolve => {
					handlers.onChunk({ type: "text-delta", id: "text-1", delta: "half" })
					signal?.addEventListener("abort", () => {
						handlers.onEnd({ kind: "aborted" })
						resolve()
					})
				})
		)
		const wrapper = render()
		await flushPromises()
		await send(wrapper, "long one")
		await wrapper.get('[data-testid="talon-v2-send"]').trigger("click")
		await flushPromises()

		const reply = wrapper.findAll('[data-testid="talon-v2-message"]')[1]
		expect(reply.attributes("data-status")).toBe("cut_off")
		expect(reply.text()).toContain("half")
	})
})
