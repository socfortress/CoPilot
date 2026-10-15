import type { FlaskBaseResponse } from "@/types/flask"
import type { TalonInvestigateRequest, TalonJobData, TalonTemplate } from "@/types/talon"
import { useAuthStore } from "@/stores/auth"
import { HttpClient } from "../http-client"

/** Shown when a Talon reply stream ends without `done` or `error`. */
export const TALON_STREAM_CLOSED = "The connection to Talon closed before the reply finished."

export default {
	investigate(payload: TalonInvestigateRequest) {
		return HttpClient.post<FlaskBaseResponse & { data?: Record<string, unknown> }>(`/talon/investigate`, payload)
	},
	getStatus(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { data?: Record<string, unknown> }>(`/talon/status`, { signal })
	},
	/**
	 * Start a fresh Talon conversation for the signed-in user.
	 *
	 * Talon holds the conversation, not CoPilot — the chat sends only the current
	 * message and the agent resumes its own stored session. Emptying the local
	 * message list alone leaves the agent remembering every prior turn.
	 *
	 * Scoped server-side to the caller's own lane; the user is read from the JWT.
	 */
	resetSession() {
		return HttpClient.post<FlaskBaseResponse & { lanes_cleared?: number }>(`/talon/session/reset`)
	},
	/**
	 * Size of the signed-in user's Talon conversation. Resolved server-side, so
	 * this never reports another analyst's activity.
	 */
	getSessionContext(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { input_tokens?: number | null; updated_at?: string | null }>(
			`/talon/session/context`,
			{ signal }
		)
	},
	getJob(alertId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { data?: TalonJobData }>(`/talon/jobs/${alertId}`, { signal })
	},
	/**
	 * List the prompt templates available in NanoClaw's CoPilot group.
	 * Used by the replay picker in the review UI — metadata only, no bodies.
	 */
	getTemplates(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { templates: TalonTemplate[] }>(`/talon/templates`, { signal })
	},
	/**
	 * Stream a message to Talon via SSE.
	 *
	 * Talon sends events in the format:
	 *   data: {"type":"text","content":"...the markdown..."}\n\n   (repeated)
	 *   data: {"type":"done"}\n\n
	 * or, on failure, possibly after some text has already streamed:
	 *   data: {"error":"Talon request failed: ..."}\n\n
	 * `: keepalive` comment lines may arrive while a reply is being worked on.
	 *
	 * Exactly one of `onDone` / `onError` is called, unless the caller aborts. A
	 * stream that ends without `done` or `error` was cut off, so it is reported as
	 * an error rather than as a finished reply.
	 */
	async streamMessage(
		message: string,
		onChunk: (text: string) => void,
		onDone: () => void,
		onError: (error: string) => void,
		signal?: AbortSignal
	) {
		const store = useAuthStore()
		const baseUrl = "/api"

		// Set before the callback runs, so a callback that throws can't end the reply a second time.
		let settled = false
		const finish = () => {
			settled = true
			onDone()
		}
		const fail = (error: string) => {
			settled = true
			onError(error)
		}

		try {
			const response = await fetch(`${baseUrl}/talon/message`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					...(store.userToken ? { Authorization: `Bearer ${store.userToken}` } : {})
				},
				body: JSON.stringify({ message, sender: "copilot" }),
				signal
			})

			if (!response.ok) {
				fail(`Request failed with status ${response.status}`)
				return
			}

			const reader = response.body?.getReader()
			if (!reader) {
				fail("No response body")
				return
			}

			/** Handle one SSE event; true once it ended the reply. */
			const handleEvent = (event: string): boolean => {
				for (const line of event.split("\n")) {
					// Only `data:` lines carry events: `: keepalive` comments are skipped here.
					if (!line.startsWith("data:")) continue
					let parsed: { type?: string; content?: string; error?: unknown }
					try {
						parsed = JSON.parse(line.slice(5))
					} catch {
						continue // Not JSON — ignore
					}
					if (parsed?.error) {
						fail(String(parsed.error))
						return true
					}
					if (parsed?.type === "done") {
						finish()
						return true
					}
					if (parsed?.type === "text" && parsed.content) {
						onChunk(parsed.content)
					}
				}
				return false
			}

			const decoder = new TextDecoder()
			let buffer = ""

			try {
				while (true) {
					let read: ReadableStreamReadResult<Uint8Array>
					try {
						read = await reader.read()
					} catch {
						// The connection failed mid-reply; an abort is the caller's own doing.
						if (!signal?.aborted) fail(TALON_STREAM_CLOSED)
						return
					}
					const { done, value } = read
					if (done) break

					// SSE allows CRLF line endings; normalised after joining, so a pair split across reads still matches.
					buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, "\n")

					// SSE events are separated by \n\n
					const events = buffer.split("\n\n")
					// Last element is incomplete — keep in buffer
					buffer = events.pop() || ""

					for (const event of events) {
						if (handleEvent(event)) return
					}
				}

				// A final event the server closed without a trailing blank line.
				buffer += decoder.decode()
				if (buffer && handleEvent(buffer)) return

				// No `done` and no `error`: the connection dropped mid-reply (proxy timeout,
				// backend restart). Not a finished reply, so don't present it as one.
				if (!signal?.aborted) fail(TALON_STREAM_CLOSED)
			} finally {
				// Release the connection however the reply ended, including after `done` / `error`.
				reader.cancel().catch(() => {})
			}
		} catch (err) {
			if (settled) return
			if (err instanceof DOMException && err.name === "AbortError") return
			fail(err instanceof Error ? err.message : "An error occurred")
		}
	}
}
