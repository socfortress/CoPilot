import { fetchEventSource } from "@microsoft/fetch-event-source"
import { useAuthStore } from "@/stores/auth"
import { HttpClient } from "./httpClient"

/** Converte Record<string, string | number> in query string, escludendo undefined/null */
function paramsToQueryString(params?: Record<string, string | number | undefined>): string {
	if (!params || Object.keys(params).length === 0) {
		return ""
	}
	const search = new URLSearchParams()
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined && value !== null) {
			search.append(key, String(value))
		}
	}
	const qs = search.toString()
	return qs ? `?${qs}` : ""
}

export interface SSEClientOptions {
	/** Path dell'endpoint (es. "/sca/overview/stream") */
	path: string
	/** HTTP method (default: "GET") */
	method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
	/** Base URL (default: HttpClient.baseURL ovvero "/api") */
	baseURL?: string
	/** Parametri convertiti automaticamente in query string */
	params?: Record<string, string | number | undefined>
	/** Handler per tipo di evento. Chiave = nome evento SSE (es. "start", "agent_result") + onOpen, onMessage, onError */
	handlers: Record<string, (data: unknown) => void> & {
		onOpen?: (response: Response) => void | Promise<void>
		onMessage?: (event: { event?: string; data: string }) => void
		onError?: (error: unknown) => void
	}
	/** AbortController per cancellare lo stream */
	signal?: AbortSignal
}

export async function createSSEStream(options: SSEClientOptions): Promise<void> {
	const { path, params, handlers, signal } = options
	const method = options.method ?? "GET"
	const baseURL = options.baseURL ?? HttpClient.defaults.baseURL ?? "/api"
	const authStore = useAuthStore()

	const base = (baseURL ?? "").replace(/\/$/, "")
	const cleanPath = path.startsWith("/") ? path : `/${path}`
	const queryString = paramsToQueryString(params)
	const url = `${base}${cleanPath}${queryString}`

	const headers: Record<string, string> = {}
	if (authStore.userToken) {
		headers.Authorization = `Bearer ${authStore.userToken}`
	}

	await fetchEventSource(url, {
		method,
		headers,
		signal,
		onopen(response) {
			if (!response.ok) {
				throw new Error(`Failed to connect: ${response.status} ${response.statusText}`)
			}
			handlers.onOpen?.(response)
			return Promise.resolve()
		},
		onmessage(event) {
			handlers.onMessage?.({ event: event.event, data: event.data ?? "" })

			if (!event.data) {
				return
			}

			try {
				const data = JSON.parse(event.data)
				const eventName = event.event || "message"
				const lifecycleKeys = ["onOpen", "onMessage", "onError"] // nomi handler lifecycle, non eventi SSE
				if (!lifecycleKeys.includes(eventName)) {
					const handler = handlers[eventName]
					if (handler) {
						handler(data)
					}
				}
			} catch (e) {
				console.error("Failed to parse SSE data:", e)
			}
		},
		onerror(err) {
			handlers.onError?.(err)
			throw err
		}
	})
}
