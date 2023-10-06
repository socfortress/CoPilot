import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { ClusterHealth, Index, IndexAllocation, IndexShard } from "@/types/indices.d"

export default {
	getAllocation() {
		return HttpClient.get<FlaskBaseResponse & { node_allocation: IndexAllocation[] }>("/wazuh_indexer/allocation")
	},
	getIndices() {
		return HttpClient.get<FlaskBaseResponse & { indices: Index[] }>("/wazuh_indexer/indices")
	},
	getShards() {
		return HttpClient.get<FlaskBaseResponse & { shards: IndexShard[] }>("/wazuh_indexer/shards")
	},
	getClusterHealth() {
		return HttpClient.get<FlaskBaseResponse & { cluster_health: ClusterHealth }>("/wazuh_indexer/health")
	}
}
