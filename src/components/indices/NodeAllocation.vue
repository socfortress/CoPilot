<template>
	<div class="cluster-health">
		<h4 class="title mb-5">
			Nodes Allocation
			<small class="opacity-50">({{ indicesAllocation.length }})</small>
		</h4>
		<n-spin :show="loading">
			<div class="info">
				<template v-if="indicesAllocation.length">
					<n-scrollbar style=" max-height;500px">
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
							<div class="group" v-if="node.disk_percent">
								<div class="box w-full">
									<n-progress
										type="line"
										indicator-placement="inside"
										:stroke-width="26"
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
	</div>
</template>

<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import { type IndexAllocation } from "@/types/indices.d"
import Api from "@/api"
import { nanoid } from "nanoid"
import { useMessage, NSpin, NScrollbar, NProgress } from "naive-ui"

const message = useMessage()
const indicesAllocation = ref<IndexAllocation[]>([])
const loading = ref(true)

// TODO: decide with Taylor
function getStatusPercent(percent: string | number | undefined | null) {
	if (parseFloat(percent?.toString() || "") < 20) return "error"
	if (parseFloat(percent?.toString() || "") < 40) return "warning"
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
			if (err.response.status === 401) {
				message.error(
					err.response?.data?.message ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response.status === 404) {
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
	@apply py-5 px-6;

	.info {
		min-height: 50px;
		margin-left: -5px;
		margin-right: -5px;

		.item {
			@apply py-3 px-4 gap-6;

			border: 2px solid transparent;
			margin: 5px;

			display: flex;
			flex-direction: column;

			.group {
				@apply gap-6;
				display: flex;
				justify-content: space-between;
				flex-grow: 1;
				flex-wrap: wrap;

				.box {
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

					:deep() {
						// TODO: check
						/*
						.el-progress-bar__outer {
							border-radius: 4px;

							.el-progress-bar__inner {
								border-radius: 0;
							}
						}
						*/
					}

					&.w-full {
						width: 100%;
					}
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
				margin-bottom: var(--size-3);
			}
		}
	}
}
</style>
