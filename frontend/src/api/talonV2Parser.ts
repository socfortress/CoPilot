/**
 * Talon v2 chat: the stream parser and the one UI model both paths fold into.
 *
 * - `createV2Parser` reads the bytes of `POST /talon/v2/chat/{id}` (the Vercel AI UI message
 *   stream, talon-analyst SPEC §8 "v2 API" "What the stream shows"; its golden files are in
 *   `__tests__/fixtures/talon-v2/`) with the v1 chat's SSE framing (`sse-framing.ts`) and hands on
 *   each known chunk, checked field by field. Unknown chunk types, malformed JSON and `: keepalive`
 *   comments are ignored; nothing after `[DONE]` is read.
 * - `applyV2Chunk` folds one chunk into an assistant message, as the AI SDK's client folds them
 *   into a `UIMessage`: text parts by id, one tool item per call id updated in place by its answer,
 *   the approval card by `approvalId`, the usage, the error (partial text kept).
 * - `fromUIMessage` maps the read-back's `UIMessage`s (`GET /talon/v2/threads/{id}/messages`,
 *   M5-5t "Reading turns back") into the same model, so a turn renders the same way either way.
 *
 * Pure: no I/O, no Vue. Every string here reaches the page as text, never as HTML; only the
 * assistant's text is rendered as Markdown (with HTML off), as in the v1 chat.
 */
import type {
	TalonV2Approval,
	TalonV2ChatMessage,
	TalonV2Chunk,
	TalonV2Item,
	TalonV2TextItem,
	TalonV2ToolItem,
	TalonV2ToolState,
	TalonV2UIMessage,
	TalonV2Usage
} from "@/types/talonV2"
import { createSseFramer, sseDataLines } from "./sse-framing"

/** talon-analyst's own fixed text for a turn that failed for a reason it doesn't name (FR-API-3a). */
export const TALON_V2_FAILED = "Talon request failed"
/** Shown when a reply stream ends without `finish` or `[DONE]`. */
export const TALON_V2_STREAM_CLOSED = "The connection to Talon closed before the reply finished."
/** A turn the client left (talon-analyst records it `cut off`), or one stopped here. */
export const TALON_V2_CUT_OFF = "This reply was cut off before it finished."

// ── the parser ───────────────────────────────────────────────────────────────

export interface V2ParserHandlers {
	onChunk: (chunk: TalonV2Chunk) => void
}

export interface V2Parser {
	/** Read the next bytes of the stream. */
	push: (value: Uint8Array) => void
	/** The stream has ended: read a final event sent without a trailing blank line. */
	end: () => void
	/** `[DONE]` was read: the stream is over, whatever follows. */
	readonly done: boolean
	/** A `finish` chunk was read: the turn ended. */
	readonly finished: boolean
}

function isString(value: unknown): value is string {
	return typeof value === "string"
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value)
}

function numberOrNull(value: unknown): number | null {
	return typeof value === "number" && Number.isFinite(value) ? value : null
}

function usageFrom(data: unknown): TalonV2Usage | null {
	if (!isRecord(data)) return null
	return {
		input_tokens: numberOrNull(data.input_tokens),
		output_tokens: numberOrNull(data.output_tokens),
		requests: numberOrNull(data.requests),
		tool_calls: numberOrNull(data.tool_calls),
		context_tokens: numberOrNull(data.context_tokens),
		cost_usd: isString(data.cost_usd) ? data.cost_usd : null
	}
}

/** A chunk the UI knows, its fields checked; null for anything else (ignored). */
export function toV2Chunk(raw: unknown): TalonV2Chunk | null {
	if (!isRecord(raw) || !isString(raw.type)) return null
	const r = raw
	switch (r.type) {
		case "start":
		case "start-step":
		case "finish-step":
			return { type: r.type }
		case "text-start":
		case "text-end":
			return isString(r.id) ? { type: r.type, id: r.id } : null
		case "text-delta":
			return isString(r.id) && isString(r.delta) ? { type: r.type, id: r.id, delta: r.delta } : null
		case "tool-input-start":
			return isString(r.toolCallId) && isString(r.toolName)
				? { type: r.type, toolCallId: r.toolCallId, toolName: r.toolName }
				: null
		case "tool-input-available":
			return isString(r.toolCallId) && isString(r.toolName)
				? { type: r.type, toolCallId: r.toolCallId, toolName: r.toolName, input: r.input }
				: null
		case "tool-input-error":
			return isString(r.toolCallId) && isString(r.toolName)
				? {
						type: r.type,
						toolCallId: r.toolCallId,
						toolName: r.toolName,
						input: r.input,
						errorText: isString(r.errorText) ? r.errorText : TALON_V2_FAILED
					}
				: null
		case "tool-output-available":
			return isString(r.toolCallId) ? { type: r.type, toolCallId: r.toolCallId, output: r.output } : null
		case "tool-output-error":
			return isString(r.toolCallId)
				? {
						type: r.type,
						toolCallId: r.toolCallId,
						errorText: isString(r.errorText) ? r.errorText : TALON_V2_FAILED
					}
				: null
		case "tool-output-denied":
			return isString(r.toolCallId) ? { type: r.type, toolCallId: r.toolCallId } : null
		case "tool-approval-request":
			return isString(r.approvalId) && isString(r.toolCallId)
				? { type: r.type, approvalId: r.approvalId, toolCallId: r.toolCallId }
				: null
		case "data-usage": {
			const data = usageFrom(r.data)
			return data ? { type: r.type, data } : null
		}
		case "error":
			return { type: r.type, errorText: isString(r.errorText) && r.errorText ? r.errorText : TALON_V2_FAILED }
		case "finish":
			return isString(r.finishReason) ? { type: r.type, finishReason: r.finishReason } : { type: r.type }
		default:
			return null
	}
}

export function createV2Parser(handlers: V2ParserHandlers): V2Parser {
	const framer = createSseFramer()
	let done = false
	let finished = false

	const handleEvent = (event: string) => {
		for (const data of sseDataLines(event)) {
			if (done) return
			if (data.trim() === "[DONE]") {
				done = true
				return
			}
			let raw: unknown
			try {
				raw = JSON.parse(data)
			} catch {
				continue // not JSON: ignored
			}
			const chunk = toV2Chunk(raw)
			if (!chunk) continue
			if (chunk.type === "finish") finished = true
			handlers.onChunk(chunk)
		}
	}

	return {
		push(value) {
			if (done) return
			for (const event of framer.push(value)) handleEvent(event)
		},
		end() {
			if (done) return
			for (const event of framer.end()) handleEvent(event)
		},
		get done() {
			return done
		},
		get finished() {
			return finished
		}
	}
}

// ── the UI model ─────────────────────────────────────────────────────────────

export function newAssistantMessage(id: string, createdAt: string | null = null): TalonV2ChatMessage {
	return { id, role: "assistant", items: [], createdAt, status: "streaming" }
}

export function newUserMessage(id: string, text: string, createdAt: string | null = null): TalonV2ChatMessage {
	return { id, role: "user", items: [{ kind: "text", id: `${id}-text`, text }], createdAt, status: "completed" }
}

export interface ApplyContext {
	/** The name of a call this message never saw start (a resumed action call's answer). */
	toolName?: (toolCallId: string) => string | null
}

function findText(message: TalonV2ChatMessage, id: string): TalonV2TextItem | undefined {
	return message.items.find((item): item is TalonV2TextItem => item.kind === "text" && item.id === id)
}

function findTool(message: TalonV2ChatMessage, toolCallId: string): TalonV2ToolItem | undefined {
	return message.items.find((item): item is TalonV2ToolItem => item.kind === "tool" && item.toolCallId === toolCallId)
}

function text(message: TalonV2ChatMessage, id: string): TalonV2TextItem {
	let item = findText(message, id)
	if (!item) {
		item = { kind: "text", id, text: "" }
		message.items.push(item)
	}
	return item
}

function tool(
	message: TalonV2ChatMessage,
	toolCallId: string,
	name: string | null,
	context?: ApplyContext
): TalonV2ToolItem {
	let item = findTool(message, toolCallId)
	if (!item) {
		item = {
			kind: "tool",
			toolCallId,
			name: name ?? context?.toolName?.(toolCallId) ?? null,
			state: "input-streaming"
		}
		message.items.push(item)
	} else if (name) {
		item.name = name
	}
	return item
}

/** A tool item's new state: what an earlier state held (an output, an error, a card) goes. */
function setState(item: TalonV2ToolItem, state: TalonV2ToolState, fields: Partial<TalonV2ToolItem> = {}) {
	delete item.output
	delete item.errorText
	delete item.approval
	item.state = state
	Object.assign(item, fields)
}

/** Fold one stream chunk into `message`, the assistant message the stream is building. */
export function applyV2Chunk(message: TalonV2ChatMessage, chunk: TalonV2Chunk, context?: ApplyContext): void {
	switch (chunk.type) {
		case "text-start":
			text(message, chunk.id)
			break
		case "text-delta":
			text(message, chunk.id).text += chunk.delta
			break
		case "tool-input-start": {
			const item = tool(message, chunk.toolCallId, chunk.toolName, context)
			if (item.state !== "input-available") setState(item, "input-streaming")
			break
		}
		case "tool-input-available":
			setState(tool(message, chunk.toolCallId, chunk.toolName, context), "input-available", {
				input: chunk.input
			})
			break
		case "tool-input-error":
			setState(tool(message, chunk.toolCallId, chunk.toolName, context), "output-error", {
				input: chunk.input,
				errorText: chunk.errorText
			})
			break
		case "tool-output-available":
			setState(tool(message, chunk.toolCallId, null, context), "output-available", { output: chunk.output })
			break
		case "tool-output-error":
			setState(tool(message, chunk.toolCallId, null, context), "output-error", { errorText: chunk.errorText })
			break
		case "tool-output-denied":
			setState(tool(message, chunk.toolCallId, null, context), "output-denied")
			break
		case "tool-approval-request":
			setState(tool(message, chunk.toolCallId, null, context), "approval-requested", {
				approval: { id: chunk.approvalId, status: "pending" }
			})
			break
		case "data-usage":
			message.usage = chunk.data
			break
		case "error":
			message.status = "failed"
			message.errorText = chunk.errorText
			break
		case "finish":
			if (message.status === "streaming") message.status = "completed"
			break
		default:
			// start, start-step, text-end, finish-step: nothing to show
			break
	}
}

/** How a stream ended, from the reader's side. */
export type V2StreamEnding = "finished" | "closed" | "aborted"

/** Close `message` once its stream is over. An `error` chunk already decided a failed turn. */
export function endAssistantMessage(message: TalonV2ChatMessage, ending: V2StreamEnding): void {
	if (message.status !== "streaming") return
	if (ending === "finished") {
		message.status = "completed"
	} else if (ending === "aborted") {
		message.status = "cut_off"
	} else {
		message.status = "failed"
		message.errorText = TALON_V2_STREAM_CLOSED
	}
}

// ── the read-back ────────────────────────────────────────────────────────────

const TOOL_STATES = new Set<TalonV2ToolState>([
	"input-streaming",
	"input-available",
	"output-available",
	"output-error",
	"output-denied",
	"approval-requested",
	"approval-responded"
])

function approvalFrom(value: unknown): TalonV2Approval | undefined {
	if (!isRecord(value) || !isString(value.id) || !isString(value.status)) return undefined
	return typeof value.approved === "boolean"
		? { id: value.id, status: value.status, approved: value.approved }
		: { id: value.id, status: value.status }
}

function toolItemFrom(part: Record<string, unknown>): TalonV2ToolItem | null {
	if (!isString(part.type) || !part.type.startsWith("tool-") || !isString(part.toolCallId)) return null
	const state =
		isString(part.state) && TOOL_STATES.has(part.state as TalonV2ToolState) ? part.state : "input-available"
	const item: TalonV2ToolItem = {
		kind: "tool",
		toolCallId: part.toolCallId,
		name: part.type.slice("tool-".length) || null,
		state: state as TalonV2ToolState
	}
	if ("input" in part) item.input = part.input
	if ("output" in part) item.output = part.output
	if (isString(part.errorText)) item.errorText = part.errorText
	const approval = approvalFrom(part.approval)
	if (approval) item.approval = approval
	return item
}

/** One read-back `UIMessage` as the UI model; null for a role the chat doesn't show. */
export function fromUIMessage(message: TalonV2UIMessage): TalonV2ChatMessage | null {
	if (!isRecord(message) || !isString(message.id) || !Array.isArray(message.parts)) return null
	const metadata = isRecord(message.metadata) ? message.metadata : {}
	const createdAt = isString(metadata.created_at) ? metadata.created_at : null

	if (message.role === "user") {
		const texts = message.parts
			.filter(
				(part): part is { type: "text"; text: string } =>
					isRecord(part) && part.type === "text" && isString(part.text)
			)
			.map(part => part.text)
		return newUserMessage(message.id, texts.join("\n"), createdAt)
	}
	if (message.role !== "assistant") return null

	const items: TalonV2Item[] = []
	message.parts.forEach((part, index) => {
		if (!isRecord(part)) return
		if (part.type === "text") {
			if (isString(part.text)) items.push({ kind: "text", id: `${message.id}-text-${index}`, text: part.text })
			return
		}
		const item = toolItemFrom(part)
		if (item) items.push(item)
		// anything else (reasoning, files, step markers): never shown
	})

	const out: TalonV2ChatMessage = { id: message.id, role: "assistant", items, createdAt, status: "completed" }
	if (metadata.status === "failed") {
		out.status = "failed"
		out.errorText = isString(metadata.error_text) && metadata.error_text ? metadata.error_text : TALON_V2_FAILED
	} else if (metadata.status === "cut_off") {
		out.status = "cut_off"
	}
	return out
}

export function fromUIMessages(messages: TalonV2UIMessage[]): TalonV2ChatMessage[] {
	return (Array.isArray(messages) ? messages : []).map(fromUIMessage).filter((m): m is TalonV2ChatMessage => !!m)
}

// ── display helpers (text only) ──────────────────────────────────────────────

/** `{truncated, keys}`: arguments too long to show, by key name only (SPEC §8, 4,096 characters). */
export function truncatedKeys(input: unknown): string[] | null {
	if (!isRecord(input) || input.truncated !== true || !Array.isArray(input.keys)) return null
	return input.keys.filter(isString)
}

/** A call's arguments as indented JSON text, for a `<pre>`; never parsed as HTML. */
export function formatToolInput(input: unknown): string {
	if (input === undefined) return ""
	try {
		return JSON.stringify(input, null, 2) ?? String(input)
	} catch {
		return String(input)
	}
}

/** The fixed tool summary `{status, spilled, returned?, total?, truncated?}` as short words. */
export function describeToolOutput(output: unknown): string[] {
	if (!isRecord(output)) return []
	const words: string[] = []
	if (output.status === "interrupted") words.push("interrupted")
	const returned = numberOrNull(output.returned)
	const total = numberOrNull(output.total)
	if (returned !== null && total !== null) words.push(`${returned.toLocaleString()} of ${total.toLocaleString()}`)
	else if (returned !== null) words.push(`${returned.toLocaleString()} returned`)
	else if (total !== null) words.push(`${total.toLocaleString()} total`)
	if (output.truncated === true) words.push("truncated")
	if (output.spilled === true) words.push("spilled")
	return words
}

/** The context badge's label, as v1's (`context 12k`); null when there is nothing to show. */
export function contextLabel(tokens: number | null | undefined): string | null {
	if (!tokens) return null
	return `context ${tokens >= 1000 ? `${Math.round(tokens / 1000)}k` : tokens}`
}
