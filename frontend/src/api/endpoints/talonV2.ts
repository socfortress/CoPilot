import type { FlaskBaseResponse } from "@/types/flask"
import type {
	TalonV2Chunk,
	TalonV2MessagesPage,
	TalonV2Thread,
	TalonV2ThreadCreate,
	TalonV2ThreadPage,
	TalonV2ThreadStatusFilter
} from "@/types/talonV2"
import { useAuthStore } from "@/stores/auth"
import { HttpClient } from "../http-client"
import { createV2Parser, TALON_V2_FAILED, TALON_V2_STREAM_CLOSED } from "../talonV2Parser"

/**
 * Talon v2 chat (talon-analyst M5): threads, a thread's earlier turns and the chat stream, through
 * CoPilot's proxy under `/api/talon/v2` (M5-5a, plus `GET /threads/{id}/messages` for M5-5t).
 *
 * Every route but `/availability` answers 404 while the "Talon v2" setting is off, so nothing here
 * is called unless `useTalonV2Availability` said it is on. A refusal keeps its status with
 * `{"detail": <fixed text>}`: 409 a decision pending, 403 a customer taken away or the alert access
 * narrowed (the UI tells them apart by status and text).
 */

/** How a chat request ended. Exactly one is reported per request. */
export type TalonV2StreamResult =
	| { kind: "finished" }
	/** The stream ended without `finish` or `[DONE]`. */
	| { kind: "closed"; errorText: string }
	| { kind: "aborted" }
	/** Refused before the stream: the status (null: no answer at all) and a short text to show. */
	| { kind: "refused"; status: number | null; detail: string }

export interface TalonV2StreamHandlers {
	onChunk: (chunk: TalonV2Chunk) => void
	onEnd: (result: TalonV2StreamResult) => void
}

const MAX_DETAIL_CHARS = 300

/** The text to show for a refused request: its own short `detail` (or CoPilot's `message`), else the fixed one. */
export function refusalDetail(body: unknown): string {
	if (typeof body === "object" && body !== null) {
		const { detail, message } = body as { detail?: unknown; message?: unknown }
		for (const candidate of [detail, message]) {
			if (typeof candidate === "string" && candidate.trim() && candidate.length <= MAX_DETAIL_CHARS) {
				return candidate.trim()
			}
		}
	}
	return TALON_V2_FAILED
}

export default {
	getAvailability(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { enabled: boolean; run_view?: boolean }>(`/talon/v2/availability`, {
			signal
		})
	},
	listThreads(
		query: { status?: TalonV2ThreadStatusFilter; limit?: number; cursor?: string | null },
		signal?: AbortSignal
	) {
		const params: Record<string, string | number> = {}
		if (query.status) params.status = query.status
		if (query.limit) params.limit = query.limit
		if (query.cursor) params.cursor = query.cursor
		return HttpClient.get<TalonV2ThreadPage>(`/talon/v2/threads`, { params, signal })
	},
	createThread(payload: TalonV2ThreadCreate) {
		return HttpClient.post<TalonV2Thread>(`/talon/v2/threads`, {
			title: payload.title ?? null,
			customer_code: payload.customer_code ?? null
		})
	},
	renameThread(threadId: string, title: string | null) {
		return HttpClient.patch<TalonV2Thread>(`/talon/v2/threads/${encodeURIComponent(threadId)}`, { title })
	},
	archiveThread(threadId: string) {
		return HttpClient.delete<TalonV2Thread>(`/talon/v2/threads/${encodeURIComponent(threadId)}`)
	},
	/** A page of the thread's earlier turns, newest page first; `before` is the previous page's `next`. */
	getMessages(threadId: string, query: { limit?: number; before?: string | null } = {}, signal?: AbortSignal) {
		const params: Record<string, string | number> = {}
		if (query.limit) params.limit = query.limit
		if (query.before) params.before = query.before
		return HttpClient.get<TalonV2MessagesPage>(`/talon/v2/threads/${encodeURIComponent(threadId)}/messages`, {
			params,
			signal
		})
	},
	/**
	 * Send one message to a thread and read the answer as it streams (`createV2Parser`).
	 *
	 * `onEnd` is called once: `finished` after `finish` or `[DONE]`, `closed` when the stream just
	 * stops, `aborted` when `signal` aborts, `refused` when CoPilot or talon-analyst refused the
	 * request before the stream started.
	 */
	async streamChat(
		threadId: string,
		body: { message: string; message_id?: string },
		handlers: TalonV2StreamHandlers,
		signal?: AbortSignal
	) {
		const store = useAuthStore()
		let ended = false
		const end = (result: TalonV2StreamResult) => {
			if (ended) return
			ended = true
			handlers.onEnd(result)
		}
		const aborted = () => !!signal?.aborted

		let response: Response
		try {
			response = await fetch(`/api/talon/v2/chat/${encodeURIComponent(threadId)}`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					...(store.userToken ? { Authorization: `Bearer ${store.userToken}` } : {})
				},
				body: JSON.stringify(body),
				signal
			})
		} catch {
			end(aborted() ? { kind: "aborted" } : { kind: "refused", status: null, detail: TALON_V2_FAILED })
			return
		}

		if (!response.ok) {
			let detail = TALON_V2_FAILED
			try {
				detail = refusalDetail(await response.json())
			} catch {
				// not JSON: the fixed text
			}
			end(aborted() ? { kind: "aborted" } : { kind: "refused", status: response.status, detail })
			return
		}

		const reader = response.body?.getReader()
		if (!reader) {
			end({ kind: "closed", errorText: TALON_V2_STREAM_CLOSED })
			return
		}

		const parser = createV2Parser({ onChunk: chunk => handlers.onChunk(chunk) })
		// The browser errors the body on abort; this makes sure a pending read ends either way.
		const cancel = () => reader.cancel().catch(() => {})
		signal?.addEventListener("abort", cancel, { once: true })
		try {
			while (!parser.done) {
				let read: ReadableStreamReadResult<Uint8Array>
				try {
					read = await reader.read()
				} catch {
					break
				}
				if (read.done) {
					if (!aborted()) parser.end()
					break
				}
				parser.push(read.value)
			}
		} finally {
			signal?.removeEventListener("abort", cancel)
			// Release the connection however the reply ended, `[DONE]` included.
			cancel()
		}

		if (aborted()) end({ kind: "aborted" })
		else if (parser.done || parser.finished) end({ kind: "finished" })
		else end({ kind: "closed", errorText: TALON_V2_STREAM_CLOSED })
	}
}
