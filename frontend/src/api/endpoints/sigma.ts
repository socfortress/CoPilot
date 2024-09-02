import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"
import type { SigmaQuery, SigmaRuleLevels, SigmaTimeInterval } from "@/types/sigma.d"

export default {
	/** client-side pagination (1k+ items) */
	getAvailable() {
		return HttpClient.get<FlaskBaseResponse & { sigma_queries: SigmaQuery[] }>(`/sigma/queries/available`)
	},
	/** client-side pagination (1k+ items) */
	getActive() {
		return HttpClient.get<FlaskBaseResponse & { sigma_queries: SigmaQuery[] }>(`/sigma/queries/active`)
	},
	/** client-side pagination (1k+ items) */
	getInactive() {
		return HttpClient.get<FlaskBaseResponse & { sigma_queries: SigmaQuery[] }>(`/sigma/queries/inactive`)
	},
	downloadRules() {
		return HttpClient.post<FlaskBaseResponse>(`/sigma/download`, {
			url: "https://github.com/SigmaHQ/sigma/releases/download/r2024-07-17/sigma_all_rules.zip",
			folder: "windows"
		})
	},
	/** It may take several minutes */
	uploadRules(ruleLevels: SigmaRuleLevels[]) {
		return HttpClient.post<FlaskBaseResponse>(`/sigma/bulk-upload-to-db`, {
			rule_levels: ruleLevels
		})
	},
	uploadRulesFile(file: File) {
		const form = new FormData()
		form.append("file", new Blob([file], { type: file.type }), file.name)

		return HttpClient.post<FlaskBaseResponse>(`/sigma/upload`, form)
	},
	/** It may take several minutes */
	activateAllQueries() {
		return HttpClient.post<FlaskBaseResponse & { enabled_queries: string[] }>(`/sigma/activate-all-queries`)
	},
	/** It may take several minutes */
	deactivateAllQueries() {
		return HttpClient.post<FlaskBaseResponse & { disabled_queries: string[] }>(`/sigma/deactivate-all-queries`)
	},
	/** returns the updated query  */
	setQueryActive(ruleName: string, active: boolean) {
		return HttpClient.put<FlaskBaseResponse & { sigma_queries: SigmaQuery[] }>(`/sigma/queries/set-active`, {
			rule_name: ruleName,
			active
		})
	},
	/** returns the updated query  */
	setQueryTimeInterval(ruleName: string, timeInterval: SigmaTimeInterval) {
		return HttpClient.put<FlaskBaseResponse & { sigma_queries: SigmaQuery[] }>(`/sigma/queries/set-time-interval`, {
			rule_name: ruleName,
			time_interval: timeInterval
		})
	},
	deleteRule(ruleName: string) {
		return HttpClient.delete<FlaskBaseResponse & { deleted_queries: string[] }>(`/sigma/queries/delete`, {
			params: {
				rule_name: ruleName
			}
		})
	},
	deleteAllRules() {
		return HttpClient.delete<FlaskBaseResponse & { deleted_queries: string[] }>(`/sigma/queries/delete-all`)
	}
}
