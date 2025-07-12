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
	}
}
