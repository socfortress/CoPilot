import type {
	TalonChatAvailability,
	TalonChatChunk,
	TalonChatMessagesPage,
	TalonChatRating,
	TalonChatThread,
	TalonChatThreadCreate,
	TalonChatThreadPage,
	TalonChatThreadStatusFilter,
	TalonDraftSubmit,
	TalonSocDraft
} from "@/types/talonChat"
import { useAuthStore } from "@/stores/auth"
import { API_ROOT, HttpClient, isAccountDisabled } from "../httpClient"
import { codeFrom, createTalonChatParser } from "../talonChatStream"

/**
 * "Ask Talon" (talon-analyst D97, FR-CHAT-9): the portal's chat with Talon, through CoPilot's
 * `/customer_portal/talon_chat/…` routes (talon-analyst SPEC §5.3 "Portal chat: CoPilot's side").
 *
 * CoPilot checks the user's access to the customer and the customer's switch on every request and
 * builds the portal identity itself; nothing here names a role, a user or a language. Every refusal
 * is `{detail, code}`: the page localizes by `code` and never reads `detail`.
 */

const BASE = "/customer_portal/talon_chat"

/** How a chat request ended. Exactly one is reported per request. */
export type TalonChatStreamResult =
	| { kind: "finished" }
	/** The stream ended without `finish` or `[DONE]`. */
	| { kind: "closed" }
	| { kind: "aborted" }
	/** Refused before the stream: the status (null: no answer at all) and the refusal's code. */
	| { kind: "refused"; status: number | null; code: string | null }

export interface TalonChatStreamHandlers {
	onChunk: (chunk: TalonChatChunk) => void
	onEnd: (result: TalonChatStreamResult) => void
}

function id(value: string) {
	return encodeURIComponent(value)
}

export default {
	/**
	 * Whether "Ask Talon" is on: for one customer, or any of the caller's (the menu). Also whether
	 * the user may submit a SOC draft and run an AI analysis for that customer.
	 */
	getAvailability(customerCode?: string) {
		return HttpClient.get<TalonChatAvailability>(`${BASE}/availability`, {
			params: customerCode ? { customer_code: customerCode } : undefined,
			// Cached as a shared promise (useTalonChatAvailability): one cancelled by a navigation
			// would never settle and keep the menu entry hidden for the session.
			keepOnNavigation: true
		})
	},
	listThreads(query: { status?: TalonChatThreadStatusFilter; limit?: number; cursor?: string | null }, signal?: AbortSignal) {
		const params: Record<string, string | number> = {}
		if (query.status) params.status = query.status
		if (query.limit) params.limit = query.limit
		if (query.cursor) params.cursor = query.cursor
		return HttpClient.get<TalonChatThreadPage>(`${BASE}/threads`, { params, signal })
	},
	createThread(payload: TalonChatThreadCreate) {
		const body: Record<string, unknown> = { customer_code: payload.customer_code }
		if (payload.title) body.title = payload.title
		if (payload.alert_id) body.alert_id = payload.alert_id
		return HttpClient.post<TalonChatThread>(`${BASE}/threads`, body)
	},
	/** Close a conversation (archive; one without a turn is deleted). */
	archiveThread(threadId: string) {
		return HttpClient.delete<TalonChatThread>(`${BASE}/threads/${id(threadId)}`)
	},
	/** A page of the thread's earlier turns, newest page first; `before` is the previous page's `next`. */
	getMessages(threadId: string, query: { limit?: number; before?: string | null } = {}, signal?: AbortSignal) {
		const params: Record<string, string | number> = {}
		if (query.limit) params.limit = query.limit
		if (query.before) params.before = query.before
		return HttpClient.get<TalonChatMessagesPage>(`${BASE}/threads/${id(threadId)}/messages`, { params, signal })
	},
	/** Thumbs up or down on a completed turn; `null` takes the rating back. */
	sendFeedback(threadId: string, runId: string, rating: TalonChatRating | null) {
		return HttpClient.post<void>(`${BASE}/threads/${id(threadId)}/feedback`, { run_id: runId, rating })
	},
	/** A SOC request draft, read by its id: never from the stream's text. */
	getDraft(draftId: string, signal?: AbortSignal) {
		return HttpClient.get<TalonSocDraft>(`${BASE}/drafts/${id(draftId)}`, { signal })
	},
	/** File the draft with the SOC as the user (claim, file, outcome: CoPilot's). */
	submitDraft(draftId: string, payload: TalonDraftSubmit) {
		return HttpClient.post<{ request_id: number | string }>(`${BASE}/drafts/${id(draftId)}/submit`, payload)
	},
	discardDraft(draftId: string) {
		return HttpClient.post<TalonSocDraft>(`${BASE}/drafts/${id(draftId)}/discard`)
	},
	/**
	 * Send one message to a thread and read the answer as it streams (`createTalonChatParser`).
	 * CoPilot builds the AI SDK's `SubmitMessage` from `{message}`, as the SOC chat's proxy does:
	 * the browser never sends one.
	 *
	 * `onEnd` is called once: `finished` after `finish` or `[DONE]`, `closed` when the stream just
	 * stops, `aborted` when `signal` aborts, `refused` when CoPilot or talon-analyst refused the
	 * request before the stream started.
	 */
	async streamChat(threadId: string, message: string, handlers: TalonChatStreamHandlers, signal?: AbortSignal) {
		const store = useAuthStore()
		let ended = false
		const end = (result: TalonChatStreamResult) => {
			if (ended) return
			ended = true
			handlers.onEnd(result)
		}
		const aborted = () => !!signal?.aborted

		let response: Response
		try {
			response = await fetch(`${API_ROOT}${BASE}/chat/${id(threadId)}`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					...(store.userToken ? { Authorization: `Bearer ${store.userToken}` } : {})
				},
				body: JSON.stringify({ message }),
				signal
			})
		} catch {
			end(aborted() ? { kind: "aborted" } : { kind: "refused", status: null, code: null })
			return
		}

		if (!response.ok) {
			// As the HTTP client does for every other request: an ended session signs out.
			if (response.status === 401 && !window.location.pathname.includes("login")) {
				window.location.href = isAccountDisabled(response.headers) ? "/logout?reason=disabled" : "/logout"
			}
			let code: string | null = null
			try {
				const body: unknown = await response.json()
				code = typeof body === "object" && body !== null ? codeFrom((body as { code?: unknown }).code) : null
			} catch {
				// not JSON: no code
			}
			end(aborted() ? { kind: "aborted" } : { kind: "refused", status: response.status, code })
			return
		}

		const reader = response.body?.getReader()
		if (!reader) {
			end({ kind: "closed" })
			return
		}

		const parser = createTalonChatParser(chunk => handlers.onChunk(chunk))
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
		else end({ kind: "closed" })
	}
}
