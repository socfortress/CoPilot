import type { VulnerabilitySearchQuery, VulnerabilitySearchResponse } from "@/types/vulnerabilities.d"
import { HttpClient } from "../httpClient"

export default {
	/**
	 * Search vulnerabilities directly from Wazuh indexer with filtering and pagination
	 */
	searchVulnerabilities(query?: VulnerabilitySearchQuery, signal?: AbortSignal) {
		return HttpClient.get<VulnerabilitySearchResponse>(`/vulnerabilities/search`, {
			params: {
				customer_code: query?.customer_code,
				agent_name: query?.agent_name,
				severity: query?.severity,
				cve_id: query?.cve_id,
				package_name: query?.package_name,
				page: query?.page || 1,
				page_size: query?.page_size || 50,
				include_epss: query?.include_epss !== false
			},
			signal
		})
	}
}
