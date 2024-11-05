<template>
	<n-card class="cluster-health" segmented>
		<template #header>
			<div class="align-center flex justify-between">
				<span>Overall Health</span>
				<IndexIcon v-if="cluster" :health="cluster.status" color />
			</div>
		</template>
		<n-spin :show="loading">
			<div v-if="cluster" class="min-h-14">
				<n-scrollbar style="max-height: 500px" trigger="none">
					<div class="card-wrap">
						<div v-for="prop of propsOrder" :key="prop" class="box">
							<template v-if="prop === 'status'">
								<div class="value align-center flex gap-2 uppercase">
									<IndexIcon :health="cluster.status" color />
									{{ cluster.status }}
								</div>
							</template>
							<template v-else>
								<div class="value">
									{{ cluster[prop] }}
								</div>
							</template>
							<div class="label">
								{{ sanitizeLabel(prop) }}
							</div>
						</div>
					</div>
				</n-scrollbar>
			</div>
			<template v-else>
				<n-empty v-if="!loading" description="No cluster found" class="h-48 justify-center" />
			</template>
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import type { ClusterHealth } from "@/types/indices.d"
import Api from "@/api"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import { NCard, NEmpty, NScrollbar, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"

const message = useMessage()
const cluster = ref<ClusterHealth | null>(null)
const loading = ref(true)

const propsOrder = ref<Array<keyof ClusterHealth>>([
	"cluster_name",
	"status",
	"active_primary_shards",
	"active_shards",
	"active_shards_percent_as_number",
	"delayed_unassigned_shards",
	"discovered_cluster_manager",
	"discovered_master",
	"initializing_shards",
	"number_of_data_nodes",
	"number_of_in_flight_fetch",
	"number_of_nodes",
	"number_of_pending_tasks",
	"relocating_shards",
	"task_max_waiting_in_queue_millis",
	"timed_out",
	"unassigned_shards"
])

function sanitizeLabel(label: string) {
	return label.replace(/_/g, " ")
}

function getClusterHealth() {
	loading.value = true
	Api.indices
		.getClusterHealth()
		.then(res => {
			if (res.data.success) {
				cluster.value = res.data.cluster_health
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(
					err.response?.data?.message ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(err.response?.data?.message || "No alerts were found.")
			} else {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getClusterHealth()
})
</script>

<style lang="scss" scoped>
.cluster-health {
	.card-wrap {
		@apply gap-6 gap-x-6 px-4 py-3;
		column-width: 12rem;
		column-count: auto;

		.box {
			overflow: hidden;
			@apply mb-6;
			.value {
				font-weight: bold;
				margin-bottom: 2px;
				white-space: nowrap;
			}
			.label {
				@apply text-xs;
				font-family: var(--font-family-mono);
				opacity: 0.8;
			}
		}
	}
}
</style>
