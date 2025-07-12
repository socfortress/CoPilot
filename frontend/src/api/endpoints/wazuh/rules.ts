import type { AlertSourceContent, WazuhRuleExclude } from "@/types/alerts.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import type { WazuhFileDetails, WazuhFileItem } from "@/types/wazuh/rules.d"
import { HttpClient } from "../../httpClient"

// Interface for rules query parameters
export interface RulesQueryParams {
	/** Show results in human-readable format */
	pretty?: boolean
	/** Disable timeout response */
	wait_for_complete?: boolean
	/** First element to return in the collection */
	offset?: number
	/** Maximum number of elements to return */
	limit?: number
	/** Sort the collection by a field or fields */
	sort?: string | null
	/** Look for elements containing the specified string */
	search?: string | null
	/** Filter by relative directory name */
	relative_dirname?: string | null
	/** Filter by filename of rule files */
	filename?: string[] | null
	/** Filter by list status (enabled, disabled, all) */
	status?: string | null
	/** Query to filter results by */
	q?: string | null
	/** Select which fields to return */
	select?: string[] | null
	/** Look for distinct values */
	distinct?: boolean
}

export default {
	wazuhManagerRuleExclude(source: AlertSourceContent) {
		return HttpClient.post<FlaskBaseResponse & WazuhRuleExclude>(`/wazuh_manager/rule/exclude`, {
			integration: "wazuh-rule-exclusion",
			prompt: source
		})
	},
	getRulesFileList(query: RulesQueryParams, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { results: WazuhFileItem[]; total_items: number }>(
			`/wazuh_manager/rules/files`,
			{
				params: query,
				signal
			}
		)
	},
	getRulesFile(filename: string) {
		return HttpClient.get<FlaskBaseResponse & WazuhFileDetails>(`/wazuh_manager/rules/files/${filename}`, {
			params: { raw: true, pretty: false, wait_for_complete: false }
		})
	},
	updateRulesFile(filename: string, rules: File) {
		const form = new FormData()
		form.append("file", new Blob([rules], { type: rules.type }), rules.name)

		return HttpClient.put<FlaskBaseResponse & WazuhFileDetails>(`/wazuh_manager/rules/files/${filename}`, form)
	},
	restartManager() {
		return HttpClient.post<FlaskBaseResponse>(`/wazuh_manager/management/restart`)
	}
}
