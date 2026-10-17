import type { TalonActionListResponse, TalonActionResponse, TalonActionScope } from "@/types/talonActions"
import { HttpClient } from "../http-client"

/**
 * Talon v2 chat action proposals (plan M5-11a; talon-analyst SPEC §5.3 M5-11): CoPilot's routes
 * under `/api/talon/actions`, behind the "Talon v2" setting (every route answers 404 while it is
 * off, so nothing here is called unless `useTalonV2Availability` said it is on).
 *
 * - `list("pending")`: what the caller may decide now, plus their own pending proposals;
 *   `list("mine")`: every proposal of theirs. Each with `can_decide` and `is_requester`.
 * - `get(id)`: one proposal, read back from talon-analyst as the caller (the card's only source).
 * - `approve`, `deny`, `withdraw`: CoPilot decides and runs it; a refusal keeps its status with
 *   CoPilot's `{success: false, message}` (a fixed text, shown as text).
 */
export default {
	list(scope: TalonActionScope, signal?: AbortSignal) {
		return HttpClient.get<TalonActionListResponse>(`/talon/actions`, { params: { scope }, signal })
	},
	get(actionId: string, signal?: AbortSignal) {
		return HttpClient.get<TalonActionResponse>(`/talon/actions/${encodeURIComponent(actionId)}`, { signal })
	},
	approve(actionId: string) {
		return HttpClient.post<TalonActionResponse>(`/talon/actions/${encodeURIComponent(actionId)}/approve`)
	},
	deny(actionId: string) {
		return HttpClient.post<TalonActionResponse>(`/talon/actions/${encodeURIComponent(actionId)}/deny`)
	},
	withdraw(actionId: string) {
		return HttpClient.post<TalonActionResponse>(`/talon/actions/${encodeURIComponent(actionId)}/withdraw`)
	}
}
