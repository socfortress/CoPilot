import type { FlaskBaseResponse } from "@/types/flask"
import type { ClusterHealth, CustomerIndicesSize, IndexAllocation, IndexShard, IndexStats } from "@/types/indices"
import { HttpClient } from "../../http-client"
import { searchLimitParams } from "../../params"

export interface IndicesQuery {
	customerCodes?: string[]
	/** Server-side substring match on index name (used by the search palette). */
	search?: string
	/** Cap the number of returned indices. */
	limit?: number
}

function indicesParams(query?: IndicesQuery) {
	const params: Record<string, number | string | string[]> = {
		...(query?.customerCodes?.length ? { customer_codes: query.customerCodes } : {}),
		...searchLimitParams(query ?? {})
	}

	if (!Object.keys(params).length) return undefined

	return {
		params,
		paramsSerializer: {
			indexes: null
		}
	}
}

export default {
	getAllocation() {
		return HttpClient.get<FlaskBaseResponse & { node_allocation: IndexAllocation[] }>("/wazuh_indexer/allocation")
	},
	getIndices(query?: IndicesQuery, signal?: AbortSignal) {
		const config = indicesParams(query)
		const requestConfig = signal && config ? { ...config, signal } : signal ? { signal } : config

		return HttpClient.get<FlaskBaseResponse & { indices_stats: IndexStats[] }>(
			"/wazuh_indexer/indices",
			requestConfig
		)
	},
	getShards() {
		return HttpClient.get<FlaskBaseResponse & { shards: IndexShard[] }>("/wazuh_indexer/shards")
	},
	getClusterHealth() {
		return HttpClient.get<FlaskBaseResponse & { cluster_health: ClusterHealth }>("/wazuh_indexer/health")
	},
	getIndicesSizePerCustomer(query?: IndicesQuery, signal?: AbortSignal) {
		const config = indicesParams(query)
		const requestConfig = signal && config ? { ...config, signal } : signal ? { signal } : config

		return HttpClient.get<FlaskBaseResponse & { customer_sizes: CustomerIndicesSize[] }>(
			`/wazuh_indexer/indices/size-per-customer`,
			requestConfig
		)
	}
}
