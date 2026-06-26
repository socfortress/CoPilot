<template>
	<n-card segmented content-class="pr-1!">
		<template #header>
			<div class="flex items-center justify-between">
				<span>Overall Health</span>
				<IndexIcon v-if="cluster" :health="cluster.status" color />
			</div>
		</template>
		<n-spin :show="loading" class="min-h-14">
			<n-scrollbar v-if="cluster" class="max-h-125" trigger="none" content-class="pr-5!">
				<div class="columns-[12rem] gap-6">
					<div
						v-for="prop of propsOrder"
						:key="prop"
						class="mb-6 flex break-inside-avoid flex-col gap-1 overflow-hidden"
					>
						<div class="text-secondary font-mono text-xs uppercase">
							{{ sanitizeLabel(prop) }}
						</div>
						<template v-if="prop === 'status'">
							<div class="flex items-center gap-2 font-bold whitespace-nowrap uppercase">
								<IndexIcon :health="cluster.status" color />
								{{ cluster.status }}
							</div>
						</template>
						<template v-else>
							<div class="font-bold whitespace-nowrap">
								{{ cluster[prop] }}
							</div>
						</template>
					</div>
				</div>
			</n-scrollbar>

			<template v-else>
				<n-empty v-if="!loading" description="No cluster found" class="h-48 justify-center" />
			</template>
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { ClusterHealth } from "@/types/indices"
import { NCard, NEmpty, NScrollbar, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import { getApiErrorMessage } from "@/utils"

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

const UNDERSCORE_REGEX = /_/g

function sanitizeLabel(label: string) {
	return label.replace(UNDERSCORE_REGEX, " ")
}

function getClusterHealth() {
	loading.value = true
	Api.wazuh.indices
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
					getApiErrorMessage(err as ApiError) ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(getApiErrorMessage(err as ApiError) || "No alerts were found.")
			} else {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
