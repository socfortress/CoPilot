import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { SocAlert, SocAlertCaseResponse } from "@/types/soc/alert.d"
import type { SocCase, SocCaseExt } from "@/types/soc/case.d"
import type { SocAlertAsset, SocCaseAsset, SocCaseAssetsState } from "@/types/soc/asset.d"
import type { SocNewNote, SocNote } from "@/types/soc/note.d"
import type { SocUser } from "@/types/soc/user.d"

export interface CasesFilter {
	olderThan: number
	unit: TimeUnit
}

export interface AlertsFilter {
	pageSize: number
	page: number
	sort: "desc" | "asc"
	alertTitle: string
}

type TimeUnit = "hours" | "days" | "weeks"

export default {
	getAlerts(filters?: Partial<AlertsFilter>, signal?: AbortSignal) {
		return HttpClient.post<FlaskBaseResponse & { alerts: SocAlert[] }>(
			`/soc/alerts`,
			{
				per_page: filters?.pageSize || 1000,
				page: filters?.page || 1,
				sort: filters?.sort || "desc",
				alert_title: filters?.alertTitle || ""
			},
			signal ? { signal } : {}
		)
	},
	getAlert(alertId: string) {
		return HttpClient.get<FlaskBaseResponse & { alert: SocAlert }>(`/soc/alerts/${alertId}`)
	},
	getAlertsBookmark(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { bookmarked_alerts: SocAlert[] }>(
			`/soc/alerts/bookmark`,
			signal ? { signal } : {}
		)
	},
	getAlertsByUser(userId: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { alerts: SocAlert[] }>(
			`/soc/alerts/alerts_by_user/${userId}`,
			signal ? { signal } : {}
		)
	},
	getAssetsByAlert(alertId: string) {
		return HttpClient.get<FlaskBaseResponse & { assets: SocAlertAsset[] }>(`/soc/alerts/assets/${alertId}`)
	},
	addAlertBookmark(alertId: string) {
		return HttpClient.post<FlaskBaseResponse & { alert: SocAlert }>(`/soc/alerts/bookmark/${alertId}`)
	},
	removeAlertBookmark(alertId: string) {
		return HttpClient.delete<FlaskBaseResponse & { alert: SocAlert }>(`/soc/alerts/bookmark/${alertId}`)
	},
	deleteAlert(alertId: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/soc/alerts/${alertId}`)
	},
	deleteMultipleAlerts(alertIds: string[]) {
		return HttpClient.post<FlaskBaseResponse>(`/soc/alerts/delete_multiple`, {
			alert_ids: alertIds
		})
	},
	/** Delete all alerts (up to 1000 per time) */
	purgeAlerts() {
		return HttpClient.delete<FlaskBaseResponse>(`/soc/alerts/purge`)
	},
	createCase(alertId: string) {
		return HttpClient.post<FlaskBaseResponse & { case: SocAlertCaseResponse }>(`/soc/alerts/create_case/${alertId}`)
	},
	getCases(payload?: string | CasesFilter) {
		let apiMethod: "get" | "post" = "get"
		let url = `/soc/cases`

		if (payload) {
			if (typeof payload === "string") {
				url = `/soc/cases/${payload}`
			} else {
				apiMethod = "post"
				url = `/soc/cases/older_than`
			}
		}

		return HttpClient[apiMethod]<
			FlaskBaseResponse & { cases?: SocCase[]; case?: SocCaseExt; cases_breached?: SocCase[] }
		>(
			url,
			{},
			apiMethod === "post" && typeof payload !== "string"
				? {
						params: {
							older_than: payload?.olderThan || 1,
							time_unit: payload?.unit || "days"
						}
						/*eslint no-mixed-spaces-and-tabs: "off"*/
				  }
				: undefined
		)
	},
	getCasesOlder(payload: CasesFilter) {
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
		return HttpClient.get<FlaskBaseResponse & { assets: SocCaseAsset[]; state: SocCaseAssetsState }>(
			`/soc/assets/${caseId}`
		)
	},
	getNotesByCase(caseId: string | number, payload: { searchTerm?: string }, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { notes: SocNote[] }>(`/soc/notes/${caseId}`, {
			params: {
				search_term: payload.searchTerm || "%"
			},
			signal
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
	},
	removeUserAlertAssign(alertId: string, userId: string) {
		return HttpClient.delete<FlaskBaseResponse & { alert: SocAlert }>(`/soc/users/assign/${alertId}/${userId}`)
	},
	closeCase(caseId: string) {
		return HttpClient.put<FlaskBaseResponse & { case: SocAlertCaseResponse }>(`/soc/cases/close/${caseId}`)
	},
	reopenCase(caseId: string) {
		return HttpClient.put<FlaskBaseResponse & { case: SocAlertCaseResponse }>(`/soc/cases/open/${caseId}`)
	},
	deleteCase(caseId: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/soc/cases/purge/${caseId}`)
	},
	purgeAllCases() {
		return HttpClient.delete<FlaskBaseResponse>(`/soc/cases/purge`)
	}
}
