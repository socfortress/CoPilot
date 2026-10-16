/**
 * A v2 thread with action proposals (M5-11b): while a card reads its record pending, or approved
 * without its result, the composer says "waiting for a decision" and is disabled. Once every open
 * card is final, the requester's open thread resumes with exactly one empty message, streamed like
 * any turn; a 400 stops it, nothing is sent twice (polls, re-renders, remounts), and a thread that
 * isn't open or whose proposals aren't the user's never resumes.
 */
import type { TalonV2StreamHandlers } from "@/api/endpoints/talonV2"
import type { TalonAction } from "@/types/talonActions"
import type { TalonV2MessagesPage, TalonV2Thread, TalonV2UIMessage } from "@/types/talonV2"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { resetTalonActions, TALON_APPROVAL_POLL_MS } from "../approvals"
import { NOTICE_PENDING } from "../notices"
import TalonV2Conversation from "../TalonV2Conversation.vue"
import { APPROVAL_ID, response, talonAction, THREAD_ID } from "./fixtures"

type StreamChat = (
	threadId: string,
	body: { message: string; message_id?: string },
	handlers: TalonV2StreamHandlers,
	signal?: AbortSignal
) => Promise<void>

const getMessages = vi.fn()
const streamChat = vi.fn<StreamChat>()
const getAction = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonV2: {
			getMessages: (...args: unknown[]) => getMessages(...args),
			streamChat: (...args: Parameters<StreamChat>) => streamChat(...args)
		},
		talonActions: {
			get: (...args: unknown[]) => getAction(...args),
			approve: vi.fn(),
			deny: vi.fn(),
			withdraw: vi.fn()
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
const RouterLinkStub = defineComponent({
	name: "RouterLink",
	setup:
		(_, { slots }) =>
		() =>
			h("a", slots.default?.())
})

const THREAD: TalonV2Thread = {
	id: THREAD_ID,
	title: "ws-1 triage",
	customer_code: "ACME",
	status: "active",
	created_at: "2026-10-16T08:00:00+00:00",
	updated_at: "2026-10-16T08:00:00+00:00",
	archived_at: null,
	accessible: true,
	context_tokens: 500
}

/** The turn that proposed it: the card, pending when the page was read. */
const PROPOSED: TalonV2UIMessage[] = [
	{ id: "r1-user", role: "user", parts: [{ type: "text", text: "close alert 840?" }], metadata: {} },
	{
		id: "r1-assistant",
		role: "assistant",
		parts: [
			{ type: "text", text: "I can close it.", state: "done" },
			{
				type: "tool-set_alert_status",
				toolCallId: "call_q",
				state: "approval-requested",
				input: { alert_id: 840, status: "CLOSED", reason: "a known scanner" },
				approval: { id: APPROVAL_ID, status: "pending" }
			}
		],
		metadata: { status: "completed" }
	}
]

/** The resumed turn: the call's answer, by the same id, without a card (no user message). */
const RESUMED: TalonV2UIMessage[] = [
	{
		id: "r2-assistant",
		role: "assistant",
		parts: [
			{
				type: "tool-set_alert_status",
				toolCallId: "call_q",
				state: "output-available",
				output: { status: "done", spilled: false }
			},
			{ type: "text", text: "Closed.", state: "done" }
		],
		metadata: { status: "completed" }
	}
]

function page(messages: TalonV2UIMessage[]): { data: TalonV2MessagesPage } {
	return { data: { thread: THREAD, messages, next: null } }
}

function render(thread: TalonV2Thread = THREAD) {
	return mount(TalonV2Conversation, {
		props: { thread },
		global: { stubs: { Markdown: MarkdownStub, Icon: true, RouterLink: RouterLinkStub } }
	})
}

function composer(wrapper: ReturnType<typeof render>) {
	return wrapper.get("textarea").element as HTMLTextAreaElement
}

const EXECUTED = { state: "executed", talon_status: "executed", can_decide: false, outcome_reported: true }

/** A resume answered by the stream: the call's answer, a text, the end. */
function resumeStream(): StreamChat {
	return async (_id, _body, handlers) => {
		handlers.onChunk({ type: "start" })
		handlers.onChunk({
			type: "tool-output-available",
			toolCallId: "call_q",
			output: { status: "done", spilled: false }
		})
		handlers.onChunk({ type: "text-start", id: "t1" })
		handlers.onChunk({ type: "text-delta", id: "t1", delta: "Closed." })
		handlers.onChunk({ type: "finish" })
		handlers.onEnd({ kind: "finished" })
	}
}

enableAutoUnmount(afterEach)

describe("talon v2 conversation with action proposals", () => {
	beforeEach(() => {
		resetTalonActions()
		getMessages.mockReset()
		streamChat.mockReset()
		getAction.mockReset()
	})
	afterEach(() => {
		vi.useRealTimers()
	})

	it("a pending proposal disables the composer with 'waiting for a decision'", async () => {
		getMessages.mockResolvedValueOnce(page(PROPOSED))
		getAction.mockResolvedValue(response(talonAction()))
		const wrapper = render()
		await flushPromises()

		expect(wrapper.get('[data-testid="talon-approval-card"]').attributes("data-state")).toBe("pending")
		const notice = wrapper.get('[data-testid="talon-v2-notice"]')
		expect(notice.text()).toBe(NOTICE_PENDING)
		expect(notice.attributes("data-kind")).toBe("pending")
		expect(composer(wrapper).disabled).toBe(true)
		expect(composer(wrapper).placeholder).toBe("Waiting for a decision in CoPilot")
		expect(streamChat).not.toHaveBeenCalled()
	})

	it("the stream's pending card holds the composer while the card reads its record", async () => {
		getMessages.mockResolvedValueOnce(page(PROPOSED))
		getAction.mockReturnValue(new Promise(() => {}))
		const wrapper = render()
		await flushPromises()
		expect(composer(wrapper).disabled).toBe(true)
	})

	it("approved but its result not with Talon yet: still waiting", async () => {
		getMessages.mockResolvedValueOnce(page(PROPOSED))
		getAction.mockResolvedValue(
			response(
				talonAction({ state: "executed", talon_status: "approved", can_decide: false, outcome_reported: false })
			)
		)
		const wrapper = render()
		await flushPromises()
		expect(composer(wrapper).disabled).toBe(true)
		expect(streamChat).not.toHaveBeenCalled()
	})

	it("a live turn's proposal locks the composer once its card reads it", async () => {
		getMessages.mockResolvedValueOnce(page([]))
		getAction.mockResolvedValue(response(talonAction()))
		streamChat.mockImplementationOnce(async (_id, _body, handlers) => {
			handlers.onChunk({ type: "tool-input-start", toolCallId: "call_q", toolName: "set_alert_status" })
			handlers.onChunk({
				type: "tool-input-available",
				toolCallId: "call_q",
				toolName: "set_alert_status",
				input: { alert_id: 999 }
			})
			handlers.onChunk({ type: "tool-approval-request", approvalId: APPROVAL_ID, toolCallId: "call_q" })
			handlers.onChunk({ type: "finish" })
			handlers.onEnd({ kind: "finished" })
		})
		const wrapper = render()
		await flushPromises()
		await wrapper.get("textarea").setValue("close 840")
		await wrapper.get('[data-testid="talon-v2-send"]').trigger("click")
		await flushPromises()

		expect(getAction).toHaveBeenCalledWith(APPROVAL_ID, expect.any(AbortSignal))
		// The card shows the GET's target, not the stream's input.
		expect(wrapper.get('[data-testid="talon-approval-target"]').text()).toBe("Alert #840")
		expect(composer(wrapper).disabled).toBe(true)
	})

	it("once final, the requester's thread resumes once with an empty message and renders the stream", async () => {
		vi.useFakeTimers()
		getMessages.mockResolvedValueOnce(page(PROPOSED))
		getAction.mockResolvedValueOnce(response(talonAction())).mockResolvedValue(response(talonAction(EXECUTED)))
		streamChat.mockImplementation(resumeStream())
		const wrapper = render()
		await flushPromises()
		expect(streamChat).not.toHaveBeenCalled()

		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS)
		await flushPromises()
		expect(streamChat).toHaveBeenCalledTimes(1)
		const [threadId, body] = streamChat.mock.calls[0]
		expect(threadId).toBe(THREAD_ID)
		expect(body).toEqual({ message: "" })

		// No user bubble for the resume; the call's answer and the text render as any turn.
		const messages = wrapper.findAll('[data-testid="talon-v2-message"]')
		expect(messages.map(m => m.attributes("data-role"))).toEqual(["user", "assistant", "assistant"])
		const reply = messages[2]
		expect(reply.attributes("data-status")).toBe("completed")
		expect(reply.get('[data-tool-call-id="call_q"]').attributes("data-state")).toBe("output-available")
		expect(reply.get('[data-testid="talon-v2-tool-name"]').text()).toBe("set_alert_status")
		expect(reply.text()).toContain("Closed.")
		expect(composer(wrapper).disabled).toBe(false)
		expect(wrapper.find('[data-testid="talon-v2-notice"]').exists()).toBe(false)
		expect(wrapper.emitted("activity")).toHaveLength(1)

		// Settled: no more reads, and nothing sent again.
		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS * 5)
		expect(getAction).toHaveBeenCalledTimes(2)
		expect(streamChat).toHaveBeenCalledTimes(1)
	})

	it("a final card read straight away resumes too, and a remount sends nothing again", async () => {
		getMessages.mockResolvedValue(page(PROPOSED))
		getAction.mockResolvedValue(
			response(talonAction({ state: "denied", talon_status: "denied", can_decide: false }))
		)
		// The resume ends without answering the call here (cut short): the thread still shows it open.
		streamChat.mockImplementation(async (_id, _body, handlers) => handlers.onEnd({ kind: "aborted" }))
		const first = render()
		await flushPromises()
		expect(streamChat).toHaveBeenCalledTimes(1)
		first.unmount()

		const second = render()
		await flushPromises()
		expect(second.get('[data-testid="talon-approval-card"]').attributes("data-state")).toBe("denied")
		expect(streamChat).toHaveBeenCalledTimes(1)
		expect(composer(second).disabled).toBe(false)
	})

	it("a 400 to the resume stops it: nothing shown, nothing sent again", async () => {
		vi.useFakeTimers()
		getMessages.mockResolvedValueOnce(page(PROPOSED))
		getAction.mockResolvedValue(response(talonAction(EXECUTED)))
		streamChat.mockImplementation(async (_id, _body, handlers) =>
			handlers.onEnd({ kind: "refused", status: 400, detail: "nothing to resume" })
		)
		const wrapper = render()
		await flushPromises()
		expect(streamChat).toHaveBeenCalledTimes(1)
		expect(wrapper.findAll('[data-testid="talon-v2-message"]')).toHaveLength(2)
		expect(wrapper.find('[data-testid="talon-v2-notice"]').exists()).toBe(false)
		expect(composer(wrapper).disabled).toBe(false)

		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS * 5)
		await wrapper.setProps({ thread: { ...THREAD, title: "renamed" } })
		await flushPromises()
		expect(streamChat).toHaveBeenCalledTimes(1)
	})

	it("another refusal of the resume shows its notice, and isn't retried", async () => {
		getMessages.mockResolvedValueOnce(page(PROPOSED))
		getAction.mockResolvedValue(response(talonAction(EXECUTED)))
		streamChat.mockImplementation(async (_id, _body, handlers) =>
			handlers.onEnd({ kind: "refused", status: 403, detail: "access to this thread's customer was removed" })
		)
		const wrapper = render()
		await flushPromises()
		expect(streamChat).toHaveBeenCalledTimes(1)
		expect(wrapper.get('[data-testid="talon-v2-notice"]').text()).toMatch(/customer was removed/)
		expect(composer(wrapper).disabled).toBe(true)
	})

	it("never resumes for a user who isn't the requester", async () => {
		getMessages.mockResolvedValueOnce(page(PROPOSED))
		getAction.mockResolvedValue(response(talonAction({ ...EXECUTED, is_requester: false })))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-approval-card"]').attributes("data-state")).toBe("executed")
		expect(streamChat).not.toHaveBeenCalled()
	})

	it.each([
		["archived", { status: "archived" }],
		["whose customer was taken away", { accessible: false }]
	])("never resumes a thread %s", async (_label, extra) => {
		getMessages.mockResolvedValue(page(PROPOSED))
		getAction.mockResolvedValue(response(talonAction(EXECUTED)))
		render({ ...THREAD, ...extra } as TalonV2Thread)
		await flushPromises()
		expect(streamChat).not.toHaveBeenCalled()
	})

	it("a thread whose calls a later turn already answered doesn't resume", async () => {
		getMessages.mockResolvedValueOnce(page([...PROPOSED, ...RESUMED]))
		getAction.mockResolvedValue(response(talonAction(EXECUTED)))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-approval-card"]').attributes("data-state")).toBe("executed")
		expect(streamChat).not.toHaveBeenCalled()
		expect(composer(wrapper).disabled).toBe(false)
	})

	it("waits for every open proposal: one final and one pending is no resume", async () => {
		const SECOND = "4a2d0b3f-6c8e-4f90-8b12-3d4e5f6a7b8c"
		const two: TalonV2UIMessage[] = [
			PROPOSED[0],
			{
				...PROPOSED[1],
				parts: [
					...PROPOSED[1].parts,
					{
						type: "tool-assign_alert",
						toolCallId: "call_r",
						state: "approval-requested",
						input: {},
						approval: { id: SECOND, status: "pending" }
					}
				]
			}
		]
		getMessages.mockResolvedValueOnce(page(two))
		getAction.mockImplementation(async (id: string) =>
			id === APPROVAL_ID
				? response(talonAction(EXECUTED))
				: response(talonAction({ id: SECOND, action: "assign_alert" } as Partial<TalonAction>))
		)
		const wrapper = render()
		await flushPromises()
		expect(wrapper.findAll('[data-testid="talon-approval-card"]')).toHaveLength(2)
		expect(composer(wrapper).disabled).toBe(true)
		expect(streamChat).not.toHaveBeenCalled()
	})
})
