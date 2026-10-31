import type { TalonChatChunk, TalonChatUIMessage } from "@/types/talonChat"
import { describe, expect, it } from "vitest"
import {
	applyChunk,
	createTalonChatParser,
	endAssistantMessage,
	fromUIMessage,
	fromUIMessages,
	newAssistantMessage,
	toChunk
} from "../talonChatStream"

const encoder = new TextEncoder()

/** Parse `text` as the stream, fed in `pieces` reads, and fold it into one assistant message. */
function parse(text: string, pieces = 1) {
	const chunks: TalonChatChunk[] = []
	const parser = createTalonChatParser(chunk => chunks.push(chunk))
	const bytes = encoder.encode(text)
	const size = Math.ceil(bytes.length / pieces)
	for (let i = 0; i < bytes.length; i += size) parser.push(bytes.slice(i, i + size))
	parser.end()
	const message = newAssistantMessage("a")
	for (const chunk of chunks) applyChunk(message, chunk)
	return { chunks, message, parser }
}

function sse(...events: (object | string)[]) {
	return events.map(event => `data: ${typeof event === "string" ? event : JSON.stringify(event)}\n\n`).join("")
}

// talon-analyst SPEC FR-CHAT-9 "Sent cumulatively", first sample: the alert, two event searches,
// one IP looked up, then the answer.
const SAMPLE_ANSWER = sse(
	{ type: "start" },
	{ type: "start-step" },
	{ type: "data-checked", id: "checked", data: { items: [{ kind: "alert", count: 1 }] } },
	{ type: "finish-step" },
	{ type: "start-step" },
	{
		type: "data-checked",
		id: "checked",
		data: {
			items: [
				{ kind: "alert", count: 1 },
				{ kind: "event_search", count: 2 },
				{ kind: "intel", type: "ip", count: 1 }
			]
		}
	},
	{ type: "finish-step" },
	{ type: "start-step" },
	{ type: "text-start", id: "text-1" },
	{ type: "text-delta", id: "text-1", delta: "The alert on HOST-A was " },
	{ type: "text-delta", id: "text-1", delta: "a scheduled task.\nNothing else ran." },
	{ type: "text-end", id: "text-1" },
	{ type: "finish-step" },
	{ type: "finish", finishReason: "stop" },
	"[DONE]"
)

// The second sample: the analysis button, then a SOC draft (the turn ends at the deferred call).
const SAMPLE_CARDS = sse(
	{ type: "start" },
	{ type: "start-step" },
	{ type: "data-ai-analysis-offer", data: { alert_id: 4127 } },
	{ type: "data-checked", id: "checked", data: { items: [{ kind: "analysis_offer", count: 1 }] } },
	{ type: "finish-step" },
	{ type: "start-step" },
	{ type: "text-start", id: "text-1" },
	{ type: "text-delta", id: "text-1", delta: "I have drafted a question for your SOC …" },
	{ type: "text-end", id: "text-1" },
	{ type: "data-soc-draft", data: { id: "6f1c2a9e-0b1d-4c55-9d7e-1f2a3b4c5d6e" } },
	{
		type: "data-checked",
		id: "checked",
		data: {
			items: [
				{ kind: "analysis_offer", count: 1 },
				{ kind: "soc_draft", count: 1 }
			]
		}
	},
	{ type: "finish-step" },
	{ type: "finish", finishReason: "stop" },
	"[DONE]"
)

describe("the Ask Talon stream (FR-API-38)", () => {
	it("folds text by id, keeping its line breaks", () => {
		const { message, parser } = parse(SAMPLE_ANSWER)
		expect(parser.done && parser.finished).toBe(true)
		expect(message.status).toBe("completed")
		expect(message.items).toEqual([
			{ kind: "text", id: "text-1", text: "The alert on HOST-A was a scheduled task.\nNothing else ran." }
		])
	})

	it("keeps only the newest checked summary: it is cumulative", () => {
		const { message, chunks } = parse(SAMPLE_ANSWER)
		expect(chunks.filter(c => c.type === "data-checked")).toHaveLength(2)
		expect(message.checked).toEqual([
			{ kind: "alert", count: 1 },
			{ kind: "event_search", count: 2 },
			{ kind: "intel", type: "ip", count: 1 }
		])
	})

	it("reads both cards, in the order they came, each once", () => {
		const doubled = SAMPLE_CARDS.replace(
			"data: [DONE]",
			`${sse({ type: "data-ai-analysis-offer", data: { alert_id: 4127 } }).trim()}\n\ndata: [DONE]`
		)
		const { message } = parse(doubled)
		expect(message.items.map(item => item.kind)).toEqual(["analysis-offer", "text", "soc-draft"])
		expect(message.items[0]).toEqual({ kind: "analysis-offer", alertId: 4127 })
		expect(message.items[2]).toEqual({ kind: "soc-draft", draftId: "6f1c2a9e-0b1d-4c55-9d7e-1f2a3b4c5d6e" })
		expect(message.checked?.map(item => item.kind)).toEqual(["analysis_offer", "soc_draft"])
	})

	it("reads the same whatever the reads split, CRLF and keepalives included", () => {
		const crlf = `: keepalive\r\n\r\n${SAMPLE_CARDS.replace(/\n/g, "\r\n")}`
		for (const pieces of [1, 3, 17, 200]) {
			expect(parse(crlf, pieces).message).toEqual(parse(SAMPLE_CARDS).message)
		}
	})

	it("ends a turn on an error chunk with its code, keeping the text so far", () => {
		const { message } = parse(
			sse(
				{ type: "start" },
				{ type: "text-start", id: "text-1" },
				{ type: "text-delta", id: "text-1", delta: "Partial" },
				{ type: "error", errorText: "portal chat is turned off for this customer", code: "portal_off" },
				{ type: "finish", finishReason: "error" },
				"[DONE]"
			)
		)
		expect(message.status).toBe("failed")
		expect(message.errorCode).toBe("portal_off")
		expect(message.items).toEqual([{ kind: "text", id: "text-1", text: "Partial" }])
	})

	it("reads an error without a usable code as the generic failure, never its text", () => {
		for (const code of [undefined, "", "Portal Off", "x".repeat(80), 42]) {
			const { message } = parse(sse({ type: "error", errorText: "turned off", code }, "[DONE]"))
			expect(message.errorCode).toBe("failed")
		}
	})

	it("ignores what the portal never shows: tool chunks, approvals, reasoning, usage, unknown types", () => {
		const { chunks, message } = parse(
			sse(
				{ type: "tool-input-start", toolCallId: "c1", toolName: "portal_get_alert" },
				{ type: "tool-input-available", toolCallId: "c1", toolName: "portal_get_alert", input: { alert_id: 1 } },
				{ type: "tool-output-available", toolCallId: "c1", output: { status: "done" } },
				{ type: "tool-approval-request", approvalId: "a", toolCallId: "c1" },
				{ type: "reasoning-delta", id: "r", delta: "secret" },
				{ type: "data-usage", data: { cost_usd: "0.01" } },
				{ type: "data-something", data: {} },
				"not json",
				{ type: "finish" },
				"[DONE]"
			)
		)
		expect(chunks.map(c => c.type)).toEqual(["finish"])
		expect(message.items).toEqual([])
	})

	it("drops malformed cards and checked items field by field", () => {
		expect(toChunk({ type: "data-soc-draft", data: { id: "<img src=x>" } })).toBeNull()
		expect(toChunk({ type: "data-soc-draft", data: {} })).toBeNull()
		expect(toChunk({ type: "data-ai-analysis-offer", data: { alert_id: "4127" } })).toBeNull()
		expect(toChunk({ type: "data-ai-analysis-offer", data: { alert_id: -1 } })).toBeNull()
		expect(
			toChunk({
				type: "data-checked",
				data: { items: [{ kind: "alert", count: 0 }, { kind: "Bad Kind", count: 1 }, { kind: "event", count: 2, type: "<b>" }] }
			})
		).toEqual({ type: "data-checked", items: [{ kind: "event", count: 2 }] })
	})

	it("reads nothing after [DONE]", () => {
		const { chunks } = parse(sse({ type: "finish" }, "[DONE]", { type: "text-start", id: "late" }))
		expect(chunks.map(c => c.type)).toEqual(["finish"])
	})

	it("says how a stream that stopped early ended", () => {
		const closed = parse(sse({ type: "text-start", id: "t" })).message
		endAssistantMessage(closed, "closed")
		expect([closed.status, closed.errorCode]).toEqual(["failed", "stream_closed"])

		const aborted = parse(sse({ type: "text-start", id: "t" })).message
		endAssistantMessage(aborted, "aborted")
		expect(aborted.status).toBe("cut_off")

		const failed = parse(sse({ type: "error", code: "busy_user" })).message
		endAssistantMessage(failed, "closed")
		expect(failed.errorCode).toBe("busy_user")
	})
})

describe("the read-back (FR-API-37)", () => {
	const turn: TalonChatUIMessage[] = [
		{ id: "run-1-user", role: "user", parts: [{ type: "text", text: "What happened?" }], metadata: { created_at: "t0" } },
		{
			id: "run-1-assistant",
			role: "assistant",
			parts: [
				{ type: "text", text: "It was a scheduled task.", state: "done" },
				{ type: "tool-portal_get_alert", toolCallId: "c1", state: "output-available", input: { alert_id: 1 } },
				{ type: "data-checked", id: "checked", data: { items: [{ kind: "alert", count: 1 }] } },
				{ type: "data-soc-draft", data: { id: "d-1", status: "pending" } },
				{ type: "data-ai-analysis-offer", data: { alert_id: 9 } },
				{ type: "reasoning", text: "hidden" }
			],
			metadata: { created_at: "t1", status: "completed", feedback: "up" }
		}
	]

	it("maps a turn to the stream's model, with the run id for feedback and no tool part", () => {
		const [user, assistant] = fromUIMessages(turn)
		expect(user?.items).toEqual([{ kind: "text", id: "run-1-user-text", text: "What happened?" }])
		expect(assistant?.runId).toBe("run-1")
		expect(assistant?.feedback).toBe("up")
		expect(fromUIMessage({ ...turn[1]!, metadata: { feedback: "sideways" } })?.feedback).toBeNull()
		expect(assistant?.checked).toEqual([{ kind: "alert", count: 1 }])
		expect(assistant?.items.map(item => item.kind)).toEqual(["text", "soc-draft", "analysis-offer"])
	})

	it("keeps a failed turn's code when there is one, else the generic failure", () => {
		const failed = fromUIMessage({
			id: "run-2-assistant",
			role: "assistant",
			parts: [],
			metadata: { status: "failed", error_text: "Talon request failed: refused", code: "messages_user" }
		})
		expect([failed?.status, failed?.errorCode]).toEqual(["failed", "messages_user"])
		const generic = fromUIMessage({ id: "x-assistant", role: "assistant", parts: [], metadata: { status: "failed" } })
		expect(generic?.errorCode).toBe("failed")
		// Only the contract's `metadata.code` is read.
		const other = fromUIMessage({
			id: "y-assistant",
			role: "assistant",
			parts: [],
			metadata: { status: "failed", error_code: "busy_user" }
		})
		expect(other?.errorCode).toBe("failed")
	})

	it("drops a role the chat doesn't show and a malformed message", () => {
		expect(fromUIMessage({ id: "s", role: "system", parts: [] })).toBeNull()
		expect(fromUIMessages([{ id: 1 } as unknown as TalonChatUIMessage])).toEqual([])
	})
})
