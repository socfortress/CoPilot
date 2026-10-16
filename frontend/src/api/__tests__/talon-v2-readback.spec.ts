/**
 * The read-back (`GET /talon/v2/threads/{id}/messages`, talon-analyst M5-5t "Reading turns back")
 * mapped into the chat's UI model by `fromUIMessage`, in the shapes talon-analyst's
 * `talon.api.transcript` writes: text parts, `tool-<name>` parts in every state, approval cards
 * pending or decided, failed and cut-off turns, a resumed call's answer without an input, and
 * parts or roles the chat never shows.
 *
 * And the point of the mapping: a turn read back is the same model as the same turn streamed.
 */
import type { TalonV2UIMessage } from "@/types/talonV2"
import { describe, expect, it } from "vitest"
import {
	applyV2Chunk,
	createV2Parser,
	endAssistantMessage,
	fromUIMessage,
	fromUIMessages,
	newAssistantMessage,
	TALON_V2_FAILED
} from "../talonV2Parser"

const AT = "2026-10-16T08:00:00+00:00"
const APPROVAL = "3f1c9a2e-5b7d-4e8f-9a01-2c3d4e5f6a7b"

function assistant(id: string, parts: unknown[], metadata: Record<string, unknown> = { status: "completed" }) {
	return { id, role: "assistant", parts, metadata: { created_at: AT, ...metadata } } as TalonV2UIMessage
}

describe("the read-back's messages", () => {
	it("a user message is its prompt as one text item", () => {
		const message = fromUIMessage({
			id: "r1-user",
			role: "user",
			parts: [{ type: "text", text: "check ws-1", state: "done" }],
			metadata: { created_at: AT }
		})
		expect(message).toEqual({
			id: "r1-user",
			role: "user",
			createdAt: AT,
			status: "completed",
			items: [{ kind: "text", id: "r1-user-text", text: "check ws-1" }]
		})
	})

	it("an assistant message keeps its text and tool parts in order", () => {
		const message = fromUIMessage(
			assistant("r1-assistant", [
				{ type: "text", text: "Checking. ", state: "done" },
				{
					type: "tool-lookup",
					toolCallId: "call_1",
					state: "output-available",
					input: { host: "ws-1" },
					output: { status: "done", spilled: false, returned: 20, total: 340, truncated: true }
				},
				{ type: "text", text: "Done.", state: "done" }
			])
		)
		expect(message?.status).toBe("completed")
		expect(message?.items).toEqual([
			{ kind: "text", id: "r1-assistant-text-0", text: "Checking. " },
			{
				kind: "tool",
				toolCallId: "call_1",
				name: "lookup",
				state: "output-available",
				input: { host: "ws-1" },
				output: { status: "done", spilled: false, returned: 20, total: 340, truncated: true }
			},
			{ kind: "text", id: "r1-assistant-text-2", text: "Done." }
		])
	})

	it("tool rows that failed, were refused, or were too long to show", () => {
		const message = fromUIMessage(
			assistant("r2-assistant", [
				{
					type: "tool-lookup",
					toolCallId: "c1",
					state: "output-error",
					input: {},
					errorText: "the tool failed"
				},
				{
					type: "tool-lookup",
					toolCallId: "c2",
					state: "output-error",
					input: { q: "x" },
					errorText: "the tool asked the model to try again"
				},
				{
					type: "tool-unknown_tool",
					toolCallId: "c3",
					state: "output-error",
					errorText: "the tool's input was invalid"
				},
				{
					type: "tool-search",
					toolCallId: "c4",
					state: "output-available",
					input: { truncated: true, keys: ["q", "range"] }
				},
				{ type: "tool-release_host", toolCallId: "c5", state: "output-denied", input: { host: "ws-1" } }
			])
		)
		expect(message?.items).toEqual([
			{
				kind: "tool",
				toolCallId: "c1",
				name: "lookup",
				state: "output-error",
				input: {},
				errorText: "the tool failed"
			},
			{
				kind: "tool",
				toolCallId: "c2",
				name: "lookup",
				state: "output-error",
				input: { q: "x" },
				errorText: "the tool asked the model to try again"
			},
			{
				kind: "tool",
				toolCallId: "c3",
				name: "unknown_tool",
				state: "output-error",
				errorText: "the tool's input was invalid"
			},
			{
				kind: "tool",
				toolCallId: "c4",
				name: "search",
				state: "output-available",
				input: { truncated: true, keys: ["q", "range"] }
			},
			{ kind: "tool", toolCallId: "c5", name: "release_host", state: "output-denied", input: { host: "ws-1" } }
		])
	})

	it("an approval card while its record is pending", () => {
		const message = fromUIMessage(
			assistant("r3-assistant", [
				{ type: "text", text: "I can close it. ", state: "done" },
				{
					type: "tool-set_alert_status",
					toolCallId: "call_q",
					state: "approval-requested",
					input: { alert_id: 840, status: "CLOSED", reason: "a known scanner" },
					approval: { id: APPROVAL, status: "pending" }
				}
			])
		)
		expect(message?.items[1]).toEqual({
			kind: "tool",
			toolCallId: "call_q",
			name: "set_alert_status",
			state: "approval-requested",
			input: { alert_id: 840, status: "CLOSED", reason: "a known scanner" },
			approval: { id: APPROVAL, status: "pending" }
		})
	})

	it.each([
		["approved", true],
		["executed", true],
		["failed", true],
		["denied", false],
		["expired", false],
		["withdrawn", false]
	])("an approval card decided %s, with its approved flag", (status, approved) => {
		const message = fromUIMessage(
			assistant("r4-assistant", [
				{
					type: "tool-set_alert_status",
					toolCallId: "call_q",
					state: "approval-responded",
					input: {},
					approval: { id: APPROVAL, status, approved }
				}
			])
		)
		expect(message?.items[0]).toMatchObject({
			state: "approval-responded",
			approval: { id: APPROVAL, status, approved }
		})
	})

	it("a resumed call's answer comes without an input, in the turn that answered it", () => {
		const messages = fromUIMessages([
			assistant("r5-assistant", [
				{
					type: "tool-set_alert_status",
					toolCallId: "call_q",
					state: "output-available",
					output: { status: "done", spilled: false }
				},
				{ type: "text", text: "Closed.", state: "done" }
			])
		])
		expect(messages).toHaveLength(1)
		expect(messages[0].items[0]).toEqual({
			kind: "tool",
			toolCallId: "call_q",
			name: "set_alert_status",
			state: "output-available",
			output: { status: "done", spilled: false }
		})
		expect("input" in messages[0].items[0]).toBe(false)
	})

	it("a failed turn keeps what it recorded and shows the stream's fixed text", () => {
		const message = fromUIMessage(
			assistant(
				"r6-assistant",
				[
					{ type: "text", text: "partial ", state: "done" },
					{
						type: "tool-lookup",
						toolCallId: "c1",
						state: "output-error",
						input: {},
						errorText: "the tool failed"
					}
				],
				{ status: "failed", error_text: "Talon request failed: turn limit reached: 30 tool calls" }
			)
		)
		expect(message?.status).toBe("failed")
		expect(message?.errorText).toBe("Talon request failed: turn limit reached: 30 tool calls")
		expect(message?.items).toHaveLength(2)
	})

	it("a failed turn without a text gets the fixed one; a cut-off turn is cut off", () => {
		expect(fromUIMessage(assistant("a", [], { status: "failed" }))).toMatchObject({
			status: "failed",
			errorText: TALON_V2_FAILED
		})
		const cut = fromUIMessage(
			assistant("b", [{ type: "tool-lookup", toolCallId: "c1", state: "input-available", input: { q: 1 } }], {
				status: "cut_off"
			})
		)
		expect(cut?.status).toBe("cut_off")
		expect(cut?.errorText).toBeUndefined()
		expect(cut?.items[0]).toMatchObject({ state: "input-available", input: { q: 1 } })
	})

	it("skips parts and roles the chat never shows, and malformed ones", () => {
		const messages = fromUIMessages([
			{ id: "s", role: "system", parts: [{ type: "text", text: "instructions" }] },
			{ id: "x", role: "assistant" } as unknown as TalonV2UIMessage,
			assistant("r7-assistant", [
				{ type: "reasoning", text: "thinking" },
				{ type: "step-start" },
				{ type: "file", url: "https://example.invalid/x.png", mediaType: "image/png" },
				{ type: "dynamic-tool", toolName: "x", toolCallId: "d1", state: "output-available" },
				{ type: "tool-lookup", state: "output-available" },
				{ type: "tool-lookup", toolCallId: "c1", state: "something-new", input: {} },
				{ type: "tool-lookup", toolCallId: "c2", state: "approval-requested", approval: { id: 5 } },
				"not a part",
				{ type: "text", text: "kept", state: "done" }
			])
		])
		expect(messages).toHaveLength(1)
		expect(messages[0].items).toEqual([
			{ kind: "tool", toolCallId: "c1", name: "lookup", state: "input-available", input: {} },
			{ kind: "tool", toolCallId: "c2", name: "lookup", state: "approval-requested" },
			{ kind: "text", id: "r7-assistant-text-8", text: "kept" }
		])
		expect(fromUIMessages(null as unknown as TalonV2UIMessage[])).toEqual([])
	})
})

describe("a turn read back is the turn streamed", () => {
	const wire = [
		{ type: "start" },
		{ type: "start-step" },
		{ type: "text-start", id: "text-1" },
		{ type: "text-delta", id: "text-1", delta: "I can close it. " },
		{ type: "text-end", id: "text-1" },
		{ type: "tool-input-start", toolCallId: "call_q", toolName: "set_alert_status" },
		{
			type: "tool-input-available",
			toolCallId: "call_q",
			toolName: "set_alert_status",
			input: { alert_id: 840, status: "CLOSED", reason: "a known scanner" }
		},
		{ type: "tool-approval-request", approvalId: APPROVAL, toolCallId: "call_q" },
		{ type: "finish-step" },
		{ type: "finish" }
	]
		.map(c => `data: ${JSON.stringify(c)}\n\n`)
		.join("")

	const readBack = assistant("r8-assistant", [
		{ type: "text", text: "I can close it. ", state: "done" },
		{
			type: "tool-set_alert_status",
			toolCallId: "call_q",
			state: "approval-requested",
			input: { alert_id: 840, status: "CLOSED", reason: "a known scanner" },
			approval: { id: APPROVAL, status: "pending" }
		}
	])

	it("has the same items and status, but for the text items' ids", () => {
		const streamed = newAssistantMessage("r8-assistant", AT)
		const parser = createV2Parser({ onChunk: chunk => applyV2Chunk(streamed, chunk) })
		parser.push(new TextEncoder().encode(wire))
		parser.end()
		endAssistantMessage(streamed, "finished")

		const read = fromUIMessage(readBack)
		const withoutTextIds = (items: typeof streamed.items) =>
			items.map(item => (item.kind === "text" ? { kind: "text", text: item.text } : item))
		expect(read?.status).toBe(streamed.status)
		expect(withoutTextIds(read?.items ?? [])).toEqual(withoutTextIds(streamed.items))
	})
})
