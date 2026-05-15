import type {
	BulkProvisionGraylogAlertRequest,
	BulkProvisionGraylogAlertResponse,
	ExecuteGraylogQueryRequest,
	ExecuteSearchRequest,
	ExecuteSearchResponse,
	GraylogProvisioningStatusResponse,
	GraylogQueryResponse,
	MitreCoverageQuery,
	MitreCoverageResponse,
	PlatformFilter,
	ProvisionGraylogAlertRequest,
	ProvisionGraylogAlertResponse,
	RefreshResponse,
	RuleDetailResponse,
	RuleListQuery,
	RuleListResponse,
	RulesByIdsRequest,
	RulesByIdsResponse,
	RuleStatsResponse
} from "@/types/copilotSearches.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export default {
	/**
	 * List all detection rules with optional filtering
	 */
	getRules(query?: RuleListQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & RuleListResponse>(`/copilot_searches`, {
			params: {
				platform: query?.platform,
				status: query?.status,
				severity: query?.severity,
				mitre_id: query?.mitre_id,
				search: query?.search,
				has_graylog: query?.has_graylog,
				skip: query?.skip || 0,
				limit: query?.limit || 100
			},
			signal
		})
	},

	/**
	 * List all Linux detection rules
	 */
	getLinuxRules(query?: Omit<RuleListQuery, "platform">, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & RuleListResponse>(`/copilot_searches/linux`, {
			params: {
				status: query?.status,
				severity: query?.severity,
				mitre_id: query?.mitre_id,
				search: query?.search,
				has_graylog: query?.has_graylog,
				skip: query?.skip || 0,
				limit: query?.limit || 100
			},
			signal
		})
	},

	/**
	 * List all Windows detection rules
	 */
	getWindowsRules(query?: Omit<RuleListQuery, "platform">, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & RuleListResponse>(`/copilot_searches/windows`, {
			params: {
				status: query?.status,
				severity: query?.severity,
				mitre_id: query?.mitre_id,
				search: query?.search,
				has_graylog: query?.has_graylog,
				skip: query?.skip || 0,
				limit: query?.limit || 100
			},
			signal
		})
	},

	/**
	 * List all PowerShell detection rules
	 */
	getPowershellRules(query?: Omit<RuleListQuery, "platform">, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & RuleListResponse>(`/copilot_searches/powershell`, {
			params: {
				status: query?.status,
				severity: query?.severity,
				mitre_id: query?.mitre_id,
				search: query?.search,
				has_graylog: query?.has_graylog,
				skip: query?.skip || 0,
				limit: query?.limit || 100
			},
			signal
		})
	},

	/**
	 * List all detection rules that have CVE tags
	 */
	getCveRules(query?: Omit<RuleListQuery, "platform">, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & RuleListResponse>(`/copilot_searches/cve`, {
			params: {
				status: query?.status,
				severity: query?.severity,
				mitre_id: query?.mitre_id,
				search: query?.search,
				has_graylog: query?.has_graylog,
				skip: query?.skip || 0,
				limit: query?.limit || 100
			},
			signal
		})
	},

	/**
	 * Get statistics about loaded detection rules
	 */
	getStats(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & RuleStatsResponse>(`/copilot_searches/stats`, {
			signal
		})
	},

	/**
	 * Get full details of a specific rule by its ID
	 */
	getRuleById(ruleId: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & RuleDetailResponse>(`/copilot_searches/id/${ruleId}`, {
			signal
		})
	},

	/**
	 * Get full details of a specific rule by its name
	 */
	getRuleByName(ruleName: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & RuleDetailResponse>(
			`/copilot_searches/name/${encodeURIComponent(ruleName)}`,
			{
				signal
			}
		)
	},

	/**
	 * Get all rules that detect a specific MITRE ATT&CK technique
	 */
	getRulesByMitre(techniqueId: string, platform?: PlatformFilter, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & RuleListResponse>(`/copilot_searches/mitre/${techniqueId}`, {
			params: {
				platform
			},
			signal
		})
	},

	/**
	 * Manually refresh the rules cache from GitHub
	 */
	refreshCache() {
		return HttpClient.post<FlaskBaseResponse & RefreshResponse>(`/copilot_searches/refresh`)
	},

	/**
	 * Execute a detection rule search against the Wazuh indexer
	 */
	executeSearch(request: ExecuteSearchRequest) {
		return HttpClient.post<FlaskBaseResponse & ExecuteSearchResponse>(`/copilot_searches/execute`, request)
	},

	/**
	 * Generate a Graylog query from a rule with parameter substitution
	 */
	generateGraylogQuery(request: ExecuteGraylogQueryRequest) {
		return HttpClient.post<FlaskBaseResponse & GraylogQueryResponse>(`/copilot_searches/graylog`, request)
	},

	/**
	 * Provision a Graylog event definition from a CoPilot Search rule
	 */
	provisionGraylogAlert(request: ProvisionGraylogAlertRequest) {
		return HttpClient.post<FlaskBaseResponse & ProvisionGraylogAlertResponse>(
			`/copilot_searches/provision/graylog`,
			request
		)
	},

	/**
	 * Provision multiple CoPilot Search rules as Graylog event definitions in a single call.
	 * Per-rule failures are reported in `results` rather than aborting the batch.
	 */
	bulkProvisionGraylogAlerts(request: BulkProvisionGraylogAlertRequest) {
		return HttpClient.post<FlaskBaseResponse & BulkProvisionGraylogAlertResponse>(
			`/copilot_searches/provision/graylog/bulk`,
			request
		)
	},

	/**
	 * For each rule ID, check whether a matching Graylog event definition already exists.
	 * Used to mark rules as "in Graylog" without forcing a re-provision.
	 */
	checkGraylogProvisioningStatus(ids: string[]) {
		return HttpClient.post<FlaskBaseResponse & GraylogProvisioningStatusResponse>(
			`/copilot_searches/provision/graylog/check`,
			{ ids }
		)
	},

	/**
	 * Fetch many rule summaries by ID in one round-trip
	 */
	getRulesByIds(ids: string[], signal?: AbortSignal) {
		const body: RulesByIdsRequest = { ids }
		return HttpClient.post<FlaskBaseResponse & RulesByIdsResponse>(`/copilot_searches/by-ids`, body, {
			signal
		})
	},

	/**
	 * MITRE ATT&CK matrix annotated with per-technique CoPilot Search rule coverage.
	 * Optional filters narrow which rules contribute to coverage (e.g. Windows-only).
	 */
	getMitreCoverage(query?: MitreCoverageQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & MitreCoverageResponse>(`/copilot_searches/mitre/coverage`, {
			params: {
				platform: query?.platform,
				severity: query?.severity,
				status: query?.status,
				has_graylog: query?.has_graylog,
				search: query?.search
			},
			signal
		})
	},

	/**
	 * Force re-fetch of the MITRE ATT&CK STIX bundle
	 */
	refreshMitreMatrix() {
		return HttpClient.post<FlaskBaseResponse & { tactics: number; techniques: number }>(
			`/copilot_searches/mitre/refresh`
		)
	}
}
