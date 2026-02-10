import type { FlaskBaseResponse } from "@/types/flask.d"
import type { ClusterHealth, IndexAllocation, IndexShard, IndexStats } from "@/types/indices.d"
import { HttpClient } from "../../httpClient"

export default {
	getAllocation() {
		return HttpClient.get<FlaskBaseResponse & { node_allocation: IndexAllocation[] }>("/wazuh_indexer/allocation")
	},
	getIndices() {
		return HttpClient.get<FlaskBaseResponse & { indices_stats: IndexStats[] }>("/wazuh_indexer/indices")
	},
	getShards() {
		return HttpClient.get<FlaskBaseResponse & { shards: IndexShard[] }>("/wazuh_indexer/shards")
	},
	getClusterHealth() {
		return HttpClient.get<FlaskBaseResponse & { cluster_health: ClusterHealth }>("/wazuh_indexer/health")
	},
	getIndicesSizePerCustomer() {
    return HttpClient.get<{
        customer_sizes: {
            customer: string
            total_size_bytes: number
            total_size_human: string
            index_count: number
            indices: string[]
        }[]
        message: string
        success: boolean
    }>(`/wazuh_indexer/indices/size-per-customer`)
}
}
