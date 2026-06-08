<template>
	<n-card segmented>
		<template #header>
			<div class="flex items-center justify-between">
				<span>Nodes Allocation</span>
				<span v-if="indicesAllocation.length" class="text-secondary font-mono">
					{{ indicesAllocation.length }}
				</span>
			</div>
		</template>
		<n-spin :show="loading">
			<div class="mx-[-5px] min-h-14">
				<template v-if="indicesAllocation.length">
					<n-scrollbar class="max-h-125" trigger="none">
						<div class="flex flex-col gap-4">
							<div
								v-for="node of indicesAllocation"
								:key="node.id"
								class="flex flex-col overflow-hidden rounded-(--border-radius) border-2"
								:class="getNodeBorderClass(node)"
							>
								<div class="flex grow flex-wrap justify-between gap-6 overflow-hidden px-4 py-3">
									<div class="flex flex-col gap-1 overflow-hidden">
										<div class="text-secondary font-mono text-xs uppercase">node</div>
										<div class="font-bold">
											{{ node.node }}
										</div>
									</div>
								</div>
								<div class="flex grow flex-wrap justify-between gap-6 overflow-hidden px-4 py-3">
									<div class="flex flex-col gap-1 overflow-hidden">
										<div class="text-secondary font-mono text-xs uppercase">disk_total</div>
										<div class="font-bold">
											{{ node.disk_total || "-" }}
										</div>
									</div>
									<div class="flex flex-col gap-1 overflow-hidden">
										<div class="text-secondary font-mono text-xs uppercase">disk_used</div>
										<div class="font-bold">
											{{ node.disk_used || "-" }}
										</div>
									</div>
									<div class="flex flex-col gap-1 overflow-hidden">
										<div class="text-secondary font-mono text-xs uppercase">disk_available</div>
										<div class="font-bold">
											{{ node.disk_available || "-" }}
										</div>
									</div>
								</div>
								<div v-if="node.disk_percent" class="overflow-hidden p-0">
									<div class="w-full overflow-hidden">
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

function getNodeBorderClass(node: IndexAllocation) {
	if (node.node === "UNASSIGNED") return "border-info"
	const status = getStatusPercent(node.disk_percent)
	if (status === "error") return "border-error"
	if (status === "warning") return "border-warning"
	return "border-success"
}

function getIndicesAllocation() {
	loading.value = true
	Api.wazuh.indices
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
