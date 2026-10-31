/**
 * "Ask Talon": the stream parser and the one UI model the stream and the read-back fold into.
 *
 * - `createTalonChatParser` reads the bytes of `POST /customer_portal/talon_chat/chat/{thread_id}`:
 *   talon-analyst's portal stream (FR-API-38), the Vercel AI UI message stream with the portal's
 *   chunks only (`start`, steps, text, `data-checked`, `data-soc-draft`, `data-ai-analysis-offer`,
 *   `error` with its `code`, `finish`, `[DONE]`). Every chunk is checked field by field; anything
 *   else (a tool chunk, reasoning, usage, malformed JSON, `: keepalive`) is ignored, and nothing
 *   after `[DONE]` is read. The approach is the SOC chat's (`frontend/src/api/talonV2Parser.ts`).
 * - `applyChunk` folds one chunk into an assistant message: text by id, the newest "checked"
 *   summary, the cards (once each), the error's code.
 * - `fromUIMessage` maps the read-back (`GET …/threads/{id}/messages`, FR-API-37) into the same model.
 *
 * Pure: no I/O, no Vue, no i18n. Every string here reaches the page as text, never as HTML.
 */
import type {
	TalonChatChunk,
	TalonChatMessage,
	TalonChatRating,
	TalonChatUIMessage,
	TalonCheckedItem
} from "@/types/talonChat"
import { createSseFramer, sseDataLines } from "./sseFraming"

/** The code of a turn that failed without one we know: talon-analyst's own generic failure. */
export const FAILED_CODE = "failed"
/** The portal's own code for a stream that stopped before `finish` or `[DONE]`. */
export const STREAM_CLOSED_CODE = "stream_closed"

const CODE = /^[a-z][a-z0-9_]{0,63}$/
const DRAFT_ID = /^[\w-]{1,64}$/
const KIND = /^[a-z][a-z_]{0,31}$/
const MAX_CHECKED_ITEMS = 50

function isString(value: unknown): value is string {
	return typeof value === "string"
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value)
}

function isPositiveInteger(value: unknown): value is number {
	return typeof value === "number" && Number.isSafeInteger(value) && value > 0
}

/** A machine code from the fixed table, or null: the text beside it is never read. */
export function codeFrom(value: unknown): string | null {
	return isString(value) && CODE.test(value) ? value : null
}

function checkedFrom(data: unknown): TalonCheckedItem[] | null {
	if (!isRecord(data) || !Array.isArray(data.items)) return null
	const items: TalonCheckedItem[] = []
	for (const raw of data.items.slice(0, MAX_CHECKED_ITEMS)) {
		if (!isRecord(raw) || !isString(raw.kind) || !KIND.test(raw.kind) || !isPositiveInteger(raw.count)) continue
		const item: TalonCheckedItem = { kind: raw.kind, count: raw.count }
		if (isString(raw.type) && KIND.test(raw.type)) item.type = raw.type
		items.push(item)
	}
	return items
}

/** A chunk (or a read-back data part) the portal knows, its fields checked; null for anything else. */
export function toChunk(raw: unknown): TalonChatChunk | null {
	if (!isRecord(raw) || !isString(raw.type)) return null
	switch (raw.type) {
		case "start":
		case "start-step":
		case "finish-step":
			return { type: raw.type }
		case "text-start":
		case "text-end":
			return isString(raw.id) ? { type: raw.type, id: raw.id } : null
		case "text-delta":
			return isString(raw.id) && isString(raw.delta) ? { type: raw.type, id: raw.id, delta: raw.delta } : null
		case "data-checked": {
			const items = checkedFrom(raw.data)
			return items ? { type: raw.type, items } : null
		}
		case "data-soc-draft":
			return isRecord(raw.data) && isString(raw.data.id) && DRAFT_ID.test(raw.data.id)
				? { type: raw.type, draftId: raw.data.id }
				: null
		case "data-ai-analysis-offer":
			return isRecord(raw.data) && isPositiveInteger(raw.data.alert_id)
				? { type: raw.type, alertId: raw.data.alert_id }
				: null
		case "error":
			return { type: raw.type, code: codeFrom(raw.code) }
		case "finish":
			return { type: raw.type }
		default:
			return null
	}
}

export interface TalonChatParser {
	/** Read the next bytes of the stream. */
	push: (value: Uint8Array) => void
	/** The stream has ended: read a final event sent without a trailing blank line. */
	end: () => void
	/** `[DONE]` was read: the stream is over, whatever follows. */
	readonly done: boolean
	/** A `finish` chunk was read: the turn ended. */
	readonly finished: boolean
}

export function createTalonChatParser(onChunk: (chunk: TalonChatChunk) => void): TalonChatParser {
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
			const chunk = toChunk(raw)
			if (!chunk) continue
			if (chunk.type === "finish") finished = true
			onChunk(chunk)
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

function message(id: string, role: TalonChatMessage["role"], createdAt: string | null): TalonChatMessage {
	return {
		id,
		role,
		items: [],
		checked: null,
		createdAt,
		status: "completed",
		errorCode: null,
		runId: null,
		feedback: null
	}
}

export function newUserMessage(id: string, text: string, createdAt: string | null = null): TalonChatMessage {
	const out = message(id, "user", createdAt)
	out.items.push({ kind: "text", id: `${id}-text`, text })
	return out
}

export function newAssistantMessage(id: string, createdAt: string | null = null): TalonChatMessage {
	return { ...message(id, "assistant", createdAt), status: "streaming" }
}

function textItem(target: TalonChatMessage, id: string) {
	let item = target.items.find(i => i.kind === "text" && i.id === id)
	if (!item) {
		item = { kind: "text", id, text: "" }
		target.items.push(item)
	}
	return item as { kind: "text"; id: string; text: string }
}

/** Fold one chunk into `target`, the assistant message the stream (or the read-back) is building. */
export function applyChunk(target: TalonChatMessage, chunk: TalonChatChunk): void {
	switch (chunk.type) {
		case "text-start":
			textItem(target, chunk.id)
			break
		case "text-delta":
			textItem(target, chunk.id).text += chunk.delta
			break
		case "data-checked":
			// Cumulative: the newest holds the turn's totals so far.
			target.checked = chunk.items
			break
		case "data-soc-draft":
			if (!target.items.some(i => i.kind === "soc-draft" && i.draftId === chunk.draftId)) {
				target.items.push({ kind: "soc-draft", draftId: chunk.draftId })
			}
			break
		case "data-ai-analysis-offer":
			if (!target.items.some(i => i.kind === "analysis-offer" && i.alertId === chunk.alertId)) {
				target.items.push({ kind: "analysis-offer", alertId: chunk.alertId })
			}
			break
		case "error":
			target.status = "failed"
			target.errorCode = chunk.code ?? FAILED_CODE
			break
		case "finish":
			if (target.status === "streaming") target.status = "completed"
			break
		default:
			// start, steps, text-end: nothing to show
			break
	}
}

/** How a stream ended, from the reader's side. */
export type StreamEnding = "finished" | "closed" | "aborted"

/** Close `target` once its stream is over. An `error` chunk already decided a failed turn. */
export function endAssistantMessage(target: TalonChatMessage, ending: StreamEnding): void {
	if (target.status !== "streaming") return
	if (ending === "finished") {
		target.status = "completed"
	} else if (ending === "aborted") {
		target.status = "cut_off"
	} else {
		target.status = "failed"
		target.errorCode = STREAM_CLOSED_CODE
	}
}

// ── the read-back ────────────────────────────────────────────────────────────

const ASSISTANT_SUFFIX = "-assistant"

function ratingFrom(value: unknown): TalonChatRating | null {
	return value === "up" || value === "down" ? value : null
}

/** One read-back `UIMessage` as the UI model; null for a role the chat doesn't show. */
export function fromUIMessage(raw: TalonChatUIMessage): TalonChatMessage | null {
	if (!isRecord(raw) || !isString(raw.id) || !Array.isArray(raw.parts)) return null
	const metadata = isRecord(raw.metadata) ? raw.metadata : {}
	const createdAt = isString(metadata.created_at) ? metadata.created_at : null

	if (raw.role === "user") {
		const texts = raw.parts.filter(part => isRecord(part) && part.type === "text" && isString(part.text))
		return newUserMessage(raw.id, texts.map(part => (part as { text: string }).text).join("\n"), createdAt)
	}
	if (raw.role !== "assistant") return null

	const out = message(raw.id, "assistant", createdAt)
	raw.parts.forEach((part, index) => {
		if (!isRecord(part)) return
		if (part.type === "text") {
			if (isString(part.text)) out.items.push({ kind: "text", id: `${raw.id}-text-${index}`, text: part.text })
			return
		}
		// The data parts have the stream's own shape (the AI SDK's data parts): checked, the cards.
		const chunk = toChunk(part)
		if (chunk && chunk.type.startsWith("data-")) applyChunk(out, chunk)
		// anything else (a tool part, reasoning, files, step markers): never shown
	})

	if (metadata.status === "failed") {
		out.status = "failed"
		// The contract's `metadata.code` (FR-API-37); none, or one malformed, is the generic failure.
		out.errorCode = codeFrom(metadata.code) ?? FAILED_CODE
	} else if (metadata.status === "cut_off") {
		out.status = "cut_off"
	}
	if (raw.id.endsWith(ASSISTANT_SUFFIX) && raw.id.length > ASSISTANT_SUFFIX.length) {
		out.runId = raw.id.slice(0, -ASSISTANT_SUFFIX.length)
	}
	out.feedback = ratingFrom(metadata.feedback)
	return out
}

export function fromUIMessages(messages: TalonChatUIMessage[]): TalonChatMessage[] {
	return (Array.isArray(messages) ? messages : []).map(fromUIMessage).filter((m): m is TalonChatMessage => !!m)
}
