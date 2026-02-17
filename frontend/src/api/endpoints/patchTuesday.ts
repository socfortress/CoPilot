import type {
	AvailableCyclesResponse,
	PatchTuesdayPriorityQuery,
	PatchTuesdayQuery,
	PatchTuesdayResponse,
	PatchTuesdaySearchQuery,
	PatchTuesdaySummaryQuery,
	PatchTuesdaySummaryResponse
} from "@/types/patchTuesday.d"
import { HttpClient } from "../httpClient"

const BASE_PATH = "/patch-tuesday"

// TODO: refactor
export default {
	/**
	 * Get full Patch Tuesday data for a specific cycle
	 * Includes all CVE x product records with EPSS and KEV enrichment
	 */
	getPatchTuesday(query?: PatchTuesdayQuery, signal?: AbortSignal) {
		return HttpClient.get<PatchTuesdayResponse>(BASE_PATH, {
			params: {
				cycle: query?.cycle,
				include_epss: query?.include_epss !== false,
				include_kev: query?.include_kev !== false
			},
			signal
		})
	},

	/**
	 * Get Patch Tuesday summary with top prioritized items
	 * Lighter endpoint suitable for dashboards
	 */
	getSummary(query?: PatchTuesdaySummaryQuery, signal?: AbortSignal) {
		return HttpClient.get<PatchTuesdaySummaryResponse>(`${BASE_PATH}/summary`, {
			params: {
				cycle: query?.cycle,
				include_epss: query?.include_epss !== false,
				include_kev: query?.include_kev !== false,
				top_n: query?.top_n || 25
			},
			signal
		})
	},

	/**
	 * Get available Patch Tuesday cycles
	 * Returns list of recent cycles and next Patch Tuesday date
	 */
	getCycles(signal?: AbortSignal) {
		return HttpClient.get<AvailableCyclesResponse>(`${BASE_PATH}/cycles`, { signal })
	},

	/**
	 * Search for specific CVEs in Patch Tuesday data
	 */
	searchCVEs(query: PatchTuesdaySearchQuery, signal?: AbortSignal) {
		return HttpClient.get<PatchTuesdayResponse>(`${BASE_PATH}/search`, {
			params: {
				cve_ids: query.cve_ids,
				cycle: query.cycle
			},
			signal
		})
	},

	/**
	 * Get vulnerabilities filtered by priority level (P0, P1, P2, P3)
	 */
	getByPriority(query: PatchTuesdayPriorityQuery, signal?: AbortSignal) {
		return HttpClient.get<PatchTuesdayResponse>(`${BASE_PATH}/priority/${query.priority_level}`, {
			params: {
				cycle: query.cycle,
				include_epss: query.include_epss !== false,
				include_kev: query.include_kev !== false
			},
			signal
		})
	},

	/**
	 * Get only CISA KEV (Known Exploited Vulnerabilities) items
	 * These are actively exploited and should be prioritized immediately
	 */
	getKEVItems(cycle?: string, signal?: AbortSignal) {
		return HttpClient.get<PatchTuesdayResponse>(`${BASE_PATH}/kev`, {
			params: { cycle },
			signal
		})
	}
}
