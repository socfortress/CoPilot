<template>
	<n-card class="cluster-health" segmented>
		<template #header>
			<div class="flex align-center justify-between">
				<span>Nodes Allocation</span>
				<span class="text-secondary-color font-mono">{{ indicesAllocation.length }}</span>
			</div>
		</template>
		<n-spin :show="loading">
			<div class="info">
				<template v-if="indicesAllocation.length">
					<n-scrollbar style="max-height: 500px" trigger="none">
						<div
							v-for="node of indicesAllocation"
							:key="node.id"
							class="item"
							:class="[`percent-${getStatusPercent(node.disk_percent)}`, `node-${node.node}`]"
						>
							<div class="group">
								<div class="box">
									<div class="value">{{ node.node }}</div>
									<div class="label">node</div>
								</div>
							</div>
							<div class="group">
								<div class="box">
									<div class="value">{{ node.disk_total || "-" }}</div>
									<div class="label">disk_total</div>
								</div>
								<div class="box">
									<div class="value">{{ node.disk_used || "-" }}</div>
									<div class="label">disk_used</div>
								</div>
								<div class="box">
									<div class="value">{{ node.disk_available || "-" }}</div>
									<div class="label">disk_available</div>
								</div>
							</div>
							<div class="group disk-percent" v-if="node.disk_percent">
								<div class="box w-full">
									<n-progress
										type="line"
										indicator-placement="inside"
										border-radius="0"
										:height="24"
										:percentage="node.disk_percent_value"
										:status="getStatusPercent(node.disk_percent_value)"
									/>
								</div>
							</div>
						</div>
					</n-scrollbar>
				</template>
			</div>
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import { type IndexAllocation } from "@/types/indices.d"
import Api from "@/api"
import { nanoid } from "nanoid"
import { useMessage, NSpin, NScrollbar, NProgress, NCard } from "naive-ui"

const message = useMessage()
const indicesAllocation = ref<IndexAllocation[]>([])
const loading = ref(true)

function getStatusPercent(percent: string | number | undefined | null) {
	if (parseFloat(percent?.toString() || "") > 90) return "error"
	if (parseFloat(percent?.toString() || "") > 80) return "warning"
	return "success"
}

function getIndicesAllocation() {
	loading.value = true
	Api.indices
		.getAllocation()
		.then(res => {
			if (res.data.success) {
				indicesAllocation.value = (res.data?.node_allocation || []).map(obj => {
					obj.id = nanoid()
					obj.disk_percent_value = parseFloat(obj.disk_percent || "")
					return obj
				})
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
	getIndicesAllocation()
})
</script>

<style lang="scss" scoped>
.cluster-health {
	.info {
		min-height: 50px;
		margin-left: -5px;
		margin-right: -5px;

		.item {
			border: 2px solid transparent;
			display: flex;
			border-radius: var(--border-radius);
			flex-direction: column;
			overflow: hidden;

			.group {
				@apply py-3 px-4;
				@apply gap-6;
				display: flex;
				justify-content: space-between;
				flex-grow: 1;
				flex-wrap: wrap;
				overflow: hidden;

				.box {
					overflow: hidden;

					.value {
						font-weight: bold;
						margin-bottom: 2px;
					}
					.label {
						@apply text-xs;
						font-family: var(--font-family-mono);
						opacity: 0.8;
					}
				}

				&.disk-percent {
					padding: 0;
				}
			}

			&.percent-success {
				border-color: var(--success-color);
			}

			&.percent-warning {
				border-color: var(--warning-color);
			}

			&.percent-error {
				border-color: var(--error-color);
			}

			&.node-UNASSIGNED {
				border-color: var(--info-color);
			}

			&:not(:last-child) {
				@apply mb-4;
			}
		}
	}
}
</style>
