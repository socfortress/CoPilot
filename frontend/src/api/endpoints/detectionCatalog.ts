// API client for the Detection Catalog — a discovery surface over CoPilot Searches.
// Backend routes live under the existing copilot_searches router because the
// catalog reads from the same in-memory rules cache; the URLs are namespaced
// under /catalog/* so they don't conflict with the rules-grid endpoints.

import type {
	CatalogComplianceFrameworksResponse,
	CatalogComplianceResponse,
	CatalogCoverageGapsResponse,
	CatalogLogTestRequest,
	CatalogLogTestResponse,
	CatalogStatsResponse,
	CatalogStoryDetailResponse,
	CatalogStoryListResponse,
	CatalogWazuhRuleDetailResponse,
	CatalogWazuhRulesResponse
} from "@/types/detectionCatalog.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export default {
	/** Top-level metrics for the catalog overview pane. */
	getStats() {
		return HttpClient.get<FlaskBaseResponse & CatalogStatsResponse>(
			`/copilot_searches/catalog/stats`
		)
	},

	/** List every analytic story with per-story aggregated summary fields. */
	listStories() {
		return HttpClient.get<FlaskBaseResponse & CatalogStoryListResponse>(
			`/copilot_searches/catalog/stories`
		)
	},

	/**
	 * Detail payload for one analytic story (description, why-it-matters narrative,
	 * detections table, data sources, references). The backend uses ``{story_name:path}``
	 * so spaces and other characters are tolerated — we encodeURIComponent here too.
	 */
	getStory(storyName: string) {
		return HttpClient.get<FlaskBaseResponse & CatalogStoryDetailResponse>(
			`/copilot_searches/catalog/stories/${encodeURIComponent(storyName)}`
		)
	},

	/**
	 * List the full Wazuh ruleset for the Wazuh Rules tab. Returns the whole
	 * corpus (~3–5k rules) in a single shot — pagination/filtering happens
	 * client-side. When the Wazuh Manager is unreachable, ``available=false``
	 * and ``unavailable_reason`` carries the human-readable cause.
	 *
	 * Pass ``customerCode`` to scope the firing-stats columns (Hits 30d /
	 * Hits 7d / Last fired) to a single customer's alerts. The rule list
	 * itself is unchanged — every rule is still returned — but rules without
	 * any hits for that customer get zeros.
	 */
	listWazuhRules(customerCode?: string) {
		return HttpClient.get<FlaskBaseResponse & CatalogWazuhRulesResponse>(
			`/copilot_searches/catalog/wazuh-rules`,
			{ params: customerCode ? { customer_code: customerCode } : {} }
		)
	},

	/** Full meta payload for one Wazuh rule (header, compliance, if-then details, …). */
	getWazuhRule(ruleId: number) {
		return HttpClient.get<FlaskBaseResponse & CatalogWazuhRuleDetailResponse>(
			`/copilot_searches/catalog/wazuh-rules/${ruleId}`
		)
	},

	/**
	 * MITRE techniques NOT covered by any rule across either corpus —
	 * the "where are our blind spots?" view. Sub-techniques are collapsed
	 * into their parents server-side (a hit on T1059.001 covers T1059).
	 */
	listCoverageGaps() {
		return HttpClient.get<FlaskBaseResponse & CatalogCoverageGapsResponse>(
			`/copilot_searches/catalog/coverage-gaps`
		)
	},

	/**
	 * Run a raw log line through Wazuh's logtest engine. Returns the matched
	 * rule (if any) + the full alert envelope. Stateless — no Wazuh session
	 * is created. Wrapped by the backend with mitre_matrix tactic-name
	 * enrichment so the result matches the rest of the catalog.
	 */
	runLogTest(payload: CatalogLogTestRequest) {
		return HttpClient.post<FlaskBaseResponse & CatalogLogTestResponse>(
			`/copilot_searches/catalog/wazuh-rules/test`,
			payload
		)
	},

	/** List the compliance frameworks the Compliance tab can pivot by. */
	listComplianceFrameworks() {
		return HttpClient.get<FlaskBaseResponse & CatalogComplianceFrameworksResponse>(
			`/copilot_searches/catalog/compliance/frameworks`
		)
	},

	/**
	 * Wazuh rules grouped by control IDs for the given framework. Each group
	 * carries rule count + total firing hits — the "what coverage do we have
	 * for PCI 10.2.4?" answer in one round-trip.
	 */
	getCompliancePivot(framework: string) {
		return HttpClient.get<FlaskBaseResponse & CatalogComplianceResponse>(
			`/copilot_searches/catalog/compliance/${encodeURIComponent(framework)}`
		)
	}
}
