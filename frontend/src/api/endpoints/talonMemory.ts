import type {
	TalonChatMemoryItem,
	TalonMemoryAsset,
	TalonMemoryDrawer,
	TalonMemoryPage,
	TalonMemoryQuery,
	TalonMemoryStats,
	TalonMemoryTimeline
} from "@/types/talonMemory"
import axios from "axios"
import { HttpClient } from "../http-client"
import { refusalDetail } from "./talonV2"

/**
 * The Talon Memory tab (`/api/talon/memory/...`): what talon-analyst remembers about a customer, the
 * asset timeline and the caller's own chat memory. Every route answers 404 `{"detail": "Not Found"}`
 * while the "Talon v2" setting is off, so nothing here is called unless `useTalonV2Availability`
 * said it is on. CoPilot checks the customer is one of the caller's; the chat routes take no user
 * id (the caller's own is used). A refusal is `{"detail", "code"}` (`memoryFailure` reads it).
 *
 * Every path segment is `encodeURIComponent`-ed here, and CoPilot checks it again; a search goes in
 * the query string only.
 */

export type TalonMemoryFailureCode =
	| "v2_off"
	| "unsupported"
	| "not_found"
	| "unknown_customer"
	| "forbidden"
	| "invalid"
	| "refused"
	| "unavailable"
	| "bad_answer"
	| "unknown"

export interface TalonMemoryFailure {
	status: number | null
	code: TalonMemoryFailureCode
	detail: string
}

const CODES: TalonMemoryFailureCode[] = [
	"unsupported",
	"not_found",
	"unknown_customer",
	"forbidden",
	"invalid",
	"refused",
	"unavailable",
	"bad_answer"
]

/** Why a request failed. CoPilot's own 404 while "Talon v2" is off is `{"detail": "Not Found"}` with no code. */
export function memoryFailure(err: unknown): TalonMemoryFailure {
	if (axios.isAxiosError(err) && err.response) {
		const data = err.response.data as { detail?: unknown; code?: unknown } | undefined
		const status = err.response.status
		const code = typeof data?.code === "string" && (CODES as string[]).includes(data.code) ? data.code : null
		if (status === 404 && !code && data?.detail === "Not Found") {
			return { status, code: "v2_off", detail: "Talon v2 is off in CoPilot" }
		}
		return { status, code: (code as TalonMemoryFailureCode) ?? "unknown", detail: refusalDetail(data) }
	}
	return { status: null, code: "unknown", detail: refusalDetail(null) }
}

const seg = encodeURIComponent

export default {
	getStats(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<TalonMemoryStats>(`/talon/memory/${seg(customerCode)}/stats`, { signal })
	},
	listDrawers(customerCode: string, query: TalonMemoryQuery, signal?: AbortSignal) {
		const params: Record<string, string | number> = {}
		for (const [key, value] of Object.entries(query)) {
			if (value !== null && value !== undefined && value !== "") params[key] = value as string | number
		}
		return HttpClient.get<TalonMemoryPage>(`/talon/memory/${seg(customerCode)}/drawers`, { params, signal })
	},
	getDrawer(customerCode: string, drawerId: string, signal?: AbortSignal) {
		return HttpClient.get<TalonMemoryDrawer>(`/talon/memory/${seg(customerCode)}/drawers/${seg(drawerId)}`, {
			signal
		})
	},
	/** Audited. 409: refused (only one-off review lessons and chat remember lessons); 404: unknown. */
	forgetDrawer(customerCode: string, drawerId: string) {
		return HttpClient.delete<{ success: boolean; drawer_id: string }>(
			`/talon/memory/${seg(customerCode)}/drawers/${seg(drawerId)}`
		)
	},
	listAssets(customerCode: string, query: { q?: string | null; limit?: number }, signal?: AbortSignal) {
		const params: Record<string, string | number> = {}
		if (query.q) params.q = query.q
		if (query.limit) params.limit = query.limit
		return HttpClient.get<{ success: boolean; items: TalonMemoryAsset[] }>(
			`/talon/memory/${seg(customerCode)}/assets`,
			{ params, signal }
		)
	},
	getAssetTimeline(customerCode: string, asset: string, signal?: AbortSignal) {
		return HttpClient.get<TalonMemoryTimeline>(`/talon/memory/${seg(customerCode)}/assets/${seg(asset)}/timeline`, {
			signal
		})
	},
	/** The caller's own chat memory: CoPilot uses the signed-in user's id, never one from here. */
	/** At most 50 (the backend caps it); default 20. */
	listMyChatMemory(limit?: number, signal?: AbortSignal) {
		return HttpClient.get<{ success: boolean; items: TalonChatMemoryItem[] }>(`/talon/memory/chat/mine`, {
			params: limit ? { limit } : undefined,
			signal
		})
	},
	forgetMyChatMemory(drawerId: string) {
		return HttpClient.delete<{ success: boolean; drawer_id: string }>(`/talon/memory/chat/mine/${seg(drawerId)}`)
	}
}
