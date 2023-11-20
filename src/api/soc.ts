import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { SocAlert } from "@/types/soc/alert.d"
import type { SocCase, SocCaseExt } from "@/types/soc/case.d"
import type { SocAsset, SocAssetsState } from "@/types/soc/asset.d"
import type { SocNewNote, SocNote } from "@/types/soc/note.d"
import type { SocUser } from "@/types/soc/user.d"

type TimeUnit = "hours" | "days" | "weeks"

export default {
	getAlerts() {
		return HttpClient.get<FlaskBaseResponse & { alerts: SocAlert[] }>(`/soc/alerts`)
	},
	getAlertsBookmark() {
		return HttpClient.get<FlaskBaseResponse & { bookmarked_alerts: SocAlert[] }>(`/soc/alerts/bookmark`)
	},
	addAlertBookmark(alertId: string) {
		return HttpClient.post<FlaskBaseResponse & { alert: SocAlert }>(`/soc/alerts/bookmark/${alertId}`)
	},
	removeAlertBookmark(alertId: string) {
		return HttpClient.delete<FlaskBaseResponse & { alert: SocAlert }>(`/soc/alerts/bookmark/${alertId}`)
	},
	getCases(caseId?: string) {
		return HttpClient.get<FlaskBaseResponse & { cases?: SocCase[]; case?: SocCaseExt }>(
			`/soc/cases${caseId ? "/" + caseId : ""}`
		)
	},
	getCasesOlder(payload: { olderThan: number; unit: TimeUnit }) {
		return HttpClient.post<FlaskBaseResponse & { cases_breached: SocCase[] }>(
			`/soc/cases/older_than`,
			{},
			{
				params: {
					older_than: payload.olderThan || 1,
					time_unit: payload.unit || "days"
				}
			}
		)
	},
	getAssetsByCase(caseId: string) {
		return HttpClient.get<FlaskBaseResponse & { assets: SocAsset[]; state: SocAssetsState }>(
			`/soc/assets/${caseId}`
		)
	},
	getNotesByCase(caseId: string | number, payload?: { searchTerm?: string }) {
		return HttpClient.get<FlaskBaseResponse & { notes: SocNote[] }>(`/soc/notes/${caseId}`, {
			params: {
				search_term: payload?.searchTerm || "%"
			}
		})
	},
	createCaseNote(caseId: string | number, payload?: { title?: string; content?: string }) {
		return HttpClient.post<FlaskBaseResponse & { note: SocNewNote }>(`/soc/notes/${caseId}`, {
			note_title: payload?.title || "",
			note_content: payload?.content || ""
		})
	},
	getUsers() {
		return HttpClient.get<FlaskBaseResponse & { users: SocUser[] }>(`/soc/users`)
	},
	assignUserToAlert(alertId: string, userId: string) {
		return HttpClient.post<FlaskBaseResponse & { alert: SocAlert }>(`/soc/users/assign/${alertId}/${userId}`)
	}
}
