/**
 * The Talon v2 stream parser (`createV2Parser`) and the UI model it folds into (`applyV2Chunk`).
 *
 * Each golden stream (talon-analyst `tests/contract/golden/v2_*.txt`, copied into
 * `fixtures/talon-v2/`, see its README) must give the same UI model however the bytes arrive: in
 * one piece, split at every byte, one byte at a time, with CRLF line endings, with keepalive
 * comments, and without the closing `[DONE]`. A stream that just stops is a failed reply with its
 * partial text kept; unknown chunk types are ignored.
 */
import type { TalonV2ChatMessage, TalonV2Chunk } from "@/types/talonV2"
import { describe, expect, it } from "vitest"
import {
	applyV2Chunk,
	createV2Parser,
	endAssistantMessage,
	newAssistantMessage,
	TALON_V2_FAILED,
	TALON_V2_STREAM_CLOSED,
	toV2Chunk
} from "../talonV2Parser"

const encoder = new TextEncoder()

const FIXTURES = import.meta.glob("./fixtures/talon-v2/v2_*.txt", {
	query: "?raw",
	import: "default",
	eager: true
}) as Record<string, string>

function fixture(name: string): string {
	const wire = FIXTURES[`./fixtures/talon-v2/${name}`]
	if (typeof wire !== "string") throw new TypeError(`no fixture ${name}`)
	return wire
}

interface Folded {
	message: TalonV2ChatMessage
	done: boolean
	finished: boolean
	chunks: TalonV2Chunk[]
}

/** Feed `pieces` (bytes) through a parser into a fresh assistant message, then end it as the reader would. */
function fold(pieces: Uint8Array[]): Folded {
	const message = newAssistantMessage("reply")
	const chunks: TalonV2Chunk[] = []
	const parser = createV2Parser({
		onChunk: chunk => {
			chunks.push(chunk)
			applyV2Chunk(message, chunk)
		}
	})
	for (const piece of pieces) parser.push(piece)
	parser.end()
	endAssistantMessage(message, parser.done || parser.finished ? "finished" : "closed")
	return { message, done: parser.done, finished: parser.finished, chunks }
}

function whole(wire: string) {
	return fold([encoder.encode(wire)])
}

function splitAt(bytes: Uint8Array, at: number): Uint8Array[] {
	return [bytes.slice(0, at), bytes.slice(at)]
}

const USAGE_TEXT = {
	input_tokens: 51,
	output_tokens: 2,
	requests: 1,
	tool_calls: 0,
	context_tokens: 883,
	cost_usd: "0"
}

const EXPECTED: Record<string, TalonV2ChatMessage> = {
	"v2_text.txt": {
		id: "reply",
		role: "assistant",
		createdAt: null,
		status: "completed",
		items: [{ kind: "text", id: "text-1", text: "hello analyst" }],
		usage: USAGE_TEXT
	},
	"v2_tool.txt": {
		id: "reply",
		role: "assistant",
		createdAt: null,
		status: "completed",
		items: [
			{ kind: "text", id: "text-1", text: "Checking. " },
			{
				kind: "tool",
				toolCallId: "call_1",
				name: "lookup",
				state: "output-available",
				input: { host: "ws-1" },
				output: { status: "done", spilled: false }
			},
			{ kind: "text", id: "text-2", text: "Done." }
		],
		usage: { input_tokens: 100, output_tokens: 8, requests: 2, tool_calls: 1, context_tokens: 57, cost_usd: "0" }
	},
	"v2_approval.txt": {
		id: "reply",
		role: "assistant",
		createdAt: null,
		status: "completed",
		items: [
			{ kind: "text", id: "text-1", text: "I can close it. " },
			{
				kind: "tool",
				toolCallId: "call_q",
				name: "set_alert_status",
				state: "approval-requested",
				input: { alert_id: 840, status: "CLOSED", reason: "a known scanner" },
				approval: { id: "3f1c9a2e-5b7d-4e8f-9a01-2c3d4e5f6a7b", status: "pending" }
			}
		],
		usage: { input_tokens: 50, output_tokens: 15, requests: 1, tool_calls: 0, context_tokens: 1055, cost_usd: "0" }
	},
	"v2_error.txt": {
		id: "reply",
		role: "assistant",
		createdAt: null,
		status: "failed",
		errorText: TALON_V2_FAILED,
		items: [{ kind: "text", id: "text-1", text: "partial " }]
	}
}

const GOLDEN = Object.keys(EXPECTED)

describe("the golden v2 streams", () => {
	it("are the four talon-analyst files, each ending with [DONE] and a blank line", () => {
		expect(Object.keys(FIXTURES).sort()).toEqual(GOLDEN.map(name => `./fixtures/talon-v2/${name}`).sort())
		for (const name of GOLDEN) expect(fixture(name).endsWith("data: [DONE]\n\n")).toBe(true)
	})

	it.each(GOLDEN)("%s gives the expected UI model in one piece", name => {
		const folded = whole(fixture(name))
		expect(folded.message).toEqual(EXPECTED[name])
		expect(folded.done).toBe(true)
		expect(folded.finished).toBe(true)
	})

	it.each(GOLDEN)("%s gives the same model split at every byte", name => {
		const bytes = encoder.encode(fixture(name))
		for (let at = 0; at <= bytes.length; at++) {
			expect(fold(splitAt(bytes, at)).message, `split at ${at}`).toEqual(EXPECTED[name])
		}
	})

	it.each(GOLDEN)("%s gives the same model one byte at a time", name => {
		const bytes = encoder.encode(fixture(name))
		const pieces = Array.from(bytes, (_, i) => bytes.slice(i, i + 1))
		expect(fold(pieces).message).toEqual(EXPECTED[name])
	})

	it.each(GOLDEN)("%s with CRLF line endings gives the same model at every split", name => {
		const bytes = encoder.encode(fixture(name).replace(/\n/g, "\r\n"))
		expect(fold([bytes]).message).toEqual(EXPECTED[name])
		for (let at = 0; at <= bytes.length; at++) {
			expect(fold(splitAt(bytes, at)).message, `split at ${at}`).toEqual(EXPECTED[name])
		}
	})

	it.each(GOLDEN)("%s with keepalive comments between chunks gives the same model", name => {
		const wire = fixture(name).replace(/\n\n/g, "\n\n: keepalive\n\n")
		const bytes = encoder.encode(wire)
		expect(fold([bytes]).message).toEqual(EXPECTED[name])
		for (let at = 0; at <= bytes.length; at += 7) {
			expect(fold(splitAt(bytes, at)).message, `split at ${at}`).toEqual(EXPECTED[name])
		}
	})

	it.each(GOLDEN)("%s without [DONE] still ends the turn on its finish chunk", name => {
		const wire = fixture(name).replace("data: [DONE]\n\n", "")
		const folded = whole(wire)
		expect(folded.done).toBe(false)
		expect(folded.finished).toBe(true)
		expect(folded.message).toEqual(EXPECTED[name])
	})

	it.each(GOLDEN)("%s whose last event has no trailing blank line is read whole", name => {
		const folded = whole(fixture(name).replace(/\n\n$/, ""))
		expect(folded.done).toBe(true)
		expect(folded.message).toEqual(EXPECTED[name])
	})

	it("hands on the chunks in order, keeping only what the UI reads", () => {
		const types = whole(fixture("v2_tool.txt")).chunks.map(c => c.type)
		expect(types).toEqual([
			"start",
			"start-step",
			"text-start",
			"text-delta",
			"text-end",
			"tool-input-start",
			"tool-input-available",
			"tool-output-available",
			"finish-step",
			"start-step",
			"text-start",
			"text-delta",
			"text-end",
			"finish-step",
			"data-usage",
			"finish"
		])
	})
})

describe("a stream that doesn't end properly", () => {
	it("without finish and without [DONE] is a failed reply with its partial text kept", () => {
		const cut = fixture("v2_tool.txt").split('data: {"type":"tool-output-available"')[0]
		const folded = whole(cut)
		expect(folded.done).toBe(false)
		expect(folded.finished).toBe(false)
		expect(folded.message.status).toBe("failed")
		expect(folded.message.errorText).toBe(TALON_V2_STREAM_CLOSED)
		expect(folded.message.items[0]).toEqual({ kind: "text", id: "text-1", text: "Checking. " })
		// The call never got its answer: left as it was, its input shown.
		expect(folded.message.items[1]).toMatchObject({ toolCallId: "call_1", state: "input-available" })
	})

	it("cut off mid-chunk keeps what came before the broken event", () => {
		const wire = fixture("v2_text.txt")
		const cut = wire.slice(0, wire.indexOf('"analyst"') + 4)
		const folded = whole(cut)
		expect(folded.message.items).toEqual([{ kind: "text", id: "text-1", text: "hello " }])
		expect(folded.message.status).toBe("failed")
	})

	it("aborted by the reader is cut off, with its partial text kept", () => {
		const message = newAssistantMessage("reply")
		const parser = createV2Parser({ onChunk: chunk => applyV2Chunk(message, chunk) })
		const wire = fixture("v2_text.txt")
		parser.push(encoder.encode(wire.slice(0, wire.indexOf('"analyst"'))))
		endAssistantMessage(message, "aborted")
		expect(message.status).toBe("cut_off")
		expect(message.items).toEqual([{ kind: "text", id: "text-1", text: "hello " }])
	})

	it("an error chunk decides the turn: a later finish doesn't make it completed", () => {
		const folded = whole(fixture("v2_error.txt"))
		expect(folded.message.status).toBe("failed")
		expect(folded.message.usage).toBeUndefined()
	})

	it("reads nothing after [DONE]", () => {
		const wire = `${fixture("v2_text.txt")}data: {"type":"text-delta","id":"text-1","delta":" more"}\n\n`
		const folded = whole(wire)
		expect(folded.message.items).toEqual([{ kind: "text", id: "text-1", text: "hello analyst" }])
	})
})

function chunkWire(...chunks: unknown[]): string {
	return `${chunks.map(c => `data: ${typeof c === "string" ? c : JSON.stringify(c)}\n\n`).join("")}data: [DONE]\n\n`
}

describe("each chunk type", () => {
	it("text deltas go to their own text part by id", () => {
		const folded = whole(
			chunkWire(
				{ type: "text-start", id: "text-1" },
				{ type: "text-delta", id: "text-1", delta: "a" },
				{ type: "text-start", id: "text-2" },
				{ type: "text-delta", id: "text-2", delta: "b" },
				{ type: "text-delta", id: "text-1", delta: "c" },
				{ type: "finish" }
			)
		)
		expect(folded.message.items).toEqual([
			{ kind: "text", id: "text-1", text: "ac" },
			{ kind: "text", id: "text-2", text: "b" }
		])
	})

	it("a multi-byte character split anywhere is decoded whole", () => {
		const bytes = encoder.encode(
			chunkWire({ type: "text-delta", id: "text-1", delta: "café 🛡️ Ωmega" }, { type: "finish" })
		)
		for (let at = 0; at <= bytes.length; at++) {
			expect(fold(splitAt(bytes, at)).message.items, `split at ${at}`).toEqual([
				{ kind: "text", id: "text-1", text: "café 🛡️ Ωmega" }
			])
		}
	})

	it("tool-input-start then tool-input-available: the name, then the arguments", () => {
		const message = newAssistantMessage("reply")
		applyV2Chunk(message, { type: "tool-input-start", toolCallId: "c1", toolName: "lookup" })
		expect(message.items).toEqual([{ kind: "tool", toolCallId: "c1", name: "lookup", state: "input-streaming" }])
		applyV2Chunk(message, { type: "tool-input-available", toolCallId: "c1", toolName: "lookup", input: { a: 1 } })
		expect(message.items).toEqual([
			{ kind: "tool", toolCallId: "c1", name: "lookup", state: "input-available", input: { a: 1 } }
		])
	})

	it("tool-input-error fails the row with talon-analyst's fixed text", () => {
		const folded = whole(
			chunkWire(
				{ type: "tool-input-start", toolCallId: "c1", toolName: "lookup" },
				{
					type: "tool-input-error",
					toolCallId: "c1",
					toolName: "lookup",
					input: { truncated: true, keys: ["q"] },
					errorText: "the tool's input was invalid"
				},
				{ type: "finish" }
			)
		)
		expect(folded.message.items).toEqual([
			{
				kind: "tool",
				toolCallId: "c1",
				name: "lookup",
				state: "output-error",
				input: { truncated: true, keys: ["q"] },
				errorText: "the tool's input was invalid"
			}
		])
	})

	it("tool-output-error fails the row with its fixed text", () => {
		const folded = whole(
			chunkWire(
				{ type: "tool-input-available", toolCallId: "c1", toolName: "lookup", input: {} },
				{ type: "tool-output-error", toolCallId: "c1", errorText: "the tool failed" },
				{ type: "finish" }
			)
		)
		expect(folded.message.items[0]).toEqual({
			kind: "tool",
			toolCallId: "c1",
			name: "lookup",
			state: "output-error",
			input: {},
			errorText: "the tool failed"
		})
	})

	it("tool-output-denied marks the row denied, dropping the card it answered", () => {
		const message = newAssistantMessage("reply")
		applyV2Chunk(message, { type: "tool-input-available", toolCallId: "c1", toolName: "release_host", input: {} })
		applyV2Chunk(message, { type: "tool-approval-request", approvalId: "a1", toolCallId: "c1" })
		applyV2Chunk(message, { type: "tool-output-denied", toolCallId: "c1" })
		expect(message.items[0]).toEqual({
			kind: "tool",
			toolCallId: "c1",
			name: "release_host",
			state: "output-denied",
			input: {}
		})
	})

	it("a resumed call's answer, without an input, takes its name from the earlier turn", () => {
		const message = newAssistantMessage("reply")
		applyV2Chunk(
			message,
			{ type: "tool-output-available", toolCallId: "call_q", output: { status: "done", spilled: false } },
			{ toolName: id => (id === "call_q" ? "set_alert_status" : null) }
		)
		applyV2Chunk(message, { type: "tool-output-denied", toolCallId: "call_r" })
		expect(message.items).toEqual([
			{
				kind: "tool",
				toolCallId: "call_q",
				name: "set_alert_status",
				state: "output-available",
				output: { status: "done", spilled: false }
			},
			{ kind: "tool", toolCallId: "call_r", name: null, state: "output-denied" }
		])
	})

	it("data-usage keeps numbers and the cost as its decimal string", () => {
		const chunk = toV2Chunk({
			type: "data-usage",
			data: {
				input_tokens: 3,
				output_tokens: "7",
				requests: 1,
				tool_calls: 0,
				context_tokens: 9,
				cost_usd: "0.000123"
			}
		})
		expect(chunk).toEqual({
			type: "data-usage",
			data: {
				input_tokens: 3,
				output_tokens: null,
				requests: 1,
				tool_calls: 0,
				context_tokens: 9,
				cost_usd: "0.000123"
			}
		})
		expect(toV2Chunk({ type: "data-usage", data: { cost_usd: 0.1 } })).toMatchObject({ data: { cost_usd: null } })
	})

	it("an error chunk without text gets the fixed text", () => {
		expect(toV2Chunk({ type: "error" })).toEqual({ type: "error", errorText: TALON_V2_FAILED })
		expect(toV2Chunk({ type: "error", errorText: 7 })).toEqual({ type: "error", errorText: TALON_V2_FAILED })
	})

	it("ignores unknown chunk types, malformed JSON, comments and chunks missing their fields", () => {
		const folded = whole(
			chunkWire(
				{ type: "text-delta", id: "text-1", delta: "kept" },
				{ type: "reasoning-delta", id: "r1", delta: "secret thinking" },
				{ type: "tool-input-delta", toolCallId: "c1", inputTextDelta: '{"a"' },
				{ type: "message-metadata", messageMetadata: { x: 1 } },
				{ type: "data-compaction", data: { summary: "x" } },
				{ type: "data-other", data: { a: 1 } },
				{ type: "file", url: "https://example.invalid/x.png", mediaType: "image/png" },
				{ type: "abort" },
				{ type: "source-url", sourceId: "s", url: "https://example.invalid" },
				{ type: "text-delta", id: "text-1" },
				{ type: "text-delta", delta: "no id" },
				{ type: "tool-input-available", toolCallId: 5, toolName: "x" },
				{ type: "tool-approval-request", toolCallId: "c9" },
				{ notype: true },
				["not", "an", "object"],
				"{not json",
				{ type: "finish" }
			)
		)
		expect(folded.message.items).toEqual([{ kind: "text", id: "text-1", text: "kept" }])
		expect(folded.message.status).toBe("completed")
	})

	it("event fields other than data are skipped", () => {
		const folded = whole(
			'event: message\nid: 4\nretry: 100\ndata: {"type":"text-delta","id":"text-1","delta":"x"}\n\ndata: {"type":"finish"}\n\n'
		)
		expect(folded.message.items).toEqual([{ kind: "text", id: "text-1", text: "x" }])
		expect(folded.finished).toBe(true)
	})
})
