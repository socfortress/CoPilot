import type { FlaskBaseResponse } from "@/types/flask.d"
import type { TalonInvestigateRequest, TalonJobData, TalonTemplate } from "@/types/talon.d"
import { useAuthStore } from "@/stores/auth"
import { HttpClient } from "../httpClient"

export default {
	investigate(payload: TalonInvestigateRequest) {
		return HttpClient.post<FlaskBaseResponse & { data?: Record<string, unknown> }>(`/talon/investigate`, payload)
	},
	getStatus() {
		return HttpClient.get<FlaskBaseResponse & { data?: Record<string, unknown> }>(`/talon/status`)
	},
	getJob(alertId: number) {
		return HttpClient.get<FlaskBaseResponse & { data?: TalonJobData }>(`/talon/jobs/${alertId}`)
	},
	/**
	 * List the prompt templates available in NanoClaw's CoPilot group.
	 * Used by the replay picker in the review UI — metadata only, no bodies.
	 */
	getTemplates() {
		return HttpClient.get<FlaskBaseResponse & { templates: TalonTemplate[] }>(`/talon/templates`)
	},
	/**
	 * Stream a message to Talon via SSE.
	 *
	 * NanoClaw sends events in the format:
	 *   data: {"type":"text","content":"...the markdown..."}\n\n
	 *   data: {"type":"done"}\n\n
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
				onError(`Request failed with status ${response.status}`)
				return
			}

			const reader = response.body?.getReader()
			if (!reader) {
				onError("No response body")
				return
			}

			const decoder = new TextDecoder()
			let buffer = ""

			while (true) {
				const { done, value } = await reader.read()
				if (done) break

				buffer += decoder.decode(value, { stream: true })

				// SSE events are separated by \n\n
				const events = buffer.split("\n\n")
				// Last element is incomplete — keep in buffer
				buffer = events.pop() || ""

				for (const event of events) {
					for (const line of event.split("\n")) {
						if (!line.startsWith("data: ")) continue
						const data = line.slice(6)
						try {
							const parsed = JSON.parse(data)
							if (parsed.type === "done") {
								onDone()
								return
							}
							if (parsed.type === "text" && parsed.content) {
								onChunk(parsed.content)
							}
							if (parsed.error) {
								onError(parsed.error)
								return
							}
						} catch {
							// Not JSON — ignore
						}
					}
				}
			}

			onDone()
		} catch (err: unknown) {
			if (err instanceof DOMException && err.name === "AbortError") return
			onError(err instanceof Error ? err.message : "An error occurred")
		}
	}
}
