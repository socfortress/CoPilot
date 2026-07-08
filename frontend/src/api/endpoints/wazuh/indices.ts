import type { FlaskBaseResponse } from "@/types/flask"
import type { ClusterHealth, CustomerIndicesSize, IndexAllocation, IndexShard, IndexStats } from "@/types/indices"
import { HttpClient } from "../../http-client"

export interface IndicesQuery {
	customerCodes?: string[]
}

function indicesParams(query?: IndicesQuery) {
	if (!query?.customerCodes?.length) return undefined

	return {
		params: {
			customer_codes: query.customerCodes
		},
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
		const requestConfig =
			signal && config ? { ...config, signal } : signal ? { signal } : config

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
		const requestConfig =
			signal && config ? { ...config, signal } : signal ? { signal } : config

		return HttpClient.get<FlaskBaseResponse & { customer_sizes: CustomerIndicesSize[] }>(
			`/wazuh_indexer/indices/size-per-customer`,
			requestConfig
		)
	}
}
