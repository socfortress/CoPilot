import type { TalonHealthReport } from "@/types/talonHealth"
import { HttpClient } from "../http-client"

/**
 * The Talon health dashboard (the AI Analyst page's Overview tab): `GET /api/talon/health`, whatever
 * the "Talon v2" setting says. One answer combines CoPilot's own checks with talon-analyst's health,
 * history and metrics, each section with its own `error`. CoPilot caches Talon's side for 30 s.
 */
export default {
	/** `hours`: the history and metrics window, 1 to 168 (the page uses 24 and 168). */
	getHealth(hours: number, signal?: AbortSignal) {
		return HttpClient.get<TalonHealthReport>(`/talon/health`, { params: { hours }, signal })
	}
}
