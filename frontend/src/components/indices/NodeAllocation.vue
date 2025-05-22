<template>
	<n-card class="cluster-health" segmented>
		<template #header>
			<div class="align-center flex justify-between">
				<span>Nodes Allocation</span>
				<span v-if="indicesAllocation.length" class="text-secondary font-mono">
					{{ indicesAllocation.length }}
				</span>
			</div>
		</template>
		<n-spin :show="loading">
			<div class="info min-h-14">
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
									<div class="value">
										{{ node.node }}
									</div>
									<div class="label">node</div>
								</div>
							</div>
							<div class="group">
								<div class="box">
									<div class="value">
										{{ node.disk_total || "-" }}
									</div>
									<div class="label">disk_total</div>
								</div>
								<div class="box">
									<div class="value">
										{{ node.disk_used || "-" }}
									</div>
									<div class="label">disk_used</div>
								</div>
								<div class="box">
									<div class="value">
										{{ node.disk_available || "-" }}
									</div>
									<div class="label">disk_available</div>
								</div>
							</div>
							<div v-if="node.disk_percent" class="disk-percent group">
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
				<template v-else>
					<n-empty v-if="!loading" description="No allocations found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
	</n-card>
</template>

<script setup lang="ts">
import type { IndexAllocation } from "@/types/indices.d"
import { NCard, NEmpty, NProgress, NScrollbar, NSpin, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"

const message = useMessage()
const indicesAllocation = ref<IndexAllocation[]>([])
const loading = ref(true)

function getStatusPercent(percent: string | number | undefined | null) {
	if (Number.parseFloat(percent?.toString() || "") > 90) return "error"
	if (Number.parseFloat(percent?.toString() || "") > 80) return "warning"
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
					obj.disk_percent_value = Number.parseFloat(obj.disk_percent || "")
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
		margin-left: -5px;
		margin-right: -5px;

		.item {
			border: 2px solid transparent;
			display: flex;
			border-radius: var(--border-radius);
			flex-direction: column;
			overflow: hidden;

			.group {
				padding-inline: calc(var(--spacing) * 4);
				padding-block: calc(var(--spacing) * 3);
				gap: calc(var(--spacing) * 6);
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
						font-size: var(--text-xs);
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
				margin-bottom: calc(var(--spacing) * 4);
			}
		}
	}
}
</style>
