<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total:
							<code>{{ total }}</code>
						</div>
						<div class="box">
							Passed:
							<code class="text-success-color">{{ totalPassed }}</code>
						</div>
						<div class="box">
							Not applicable:
							<code class="text-warning-color">{{ totalNA }}</code>
						</div>
						<div class="box">
							Failed:
							<code class="text-error-color">{{ totalFailed }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot="pageSlot"
				:show-size-picker="showSizePicker"
				:page-sizes="pageSizes"
				:item-count="itemsFiltered.length"
				:simple="simpleMode"
			/>
			<n-popover overlap placement="right" class="!px-0">
				<template #trigger>
					<div class="bg-color border-radius">
						<n-button size="small">
							<template #icon>
								<Icon :name="FilterIcon"></Icon>
							</template>
						</n-button>
					</div>
				</template>
				<div class="py-1">
					<div class="px-3">
						<div class="text-secondary-color text-sm mb-1">Result:</div>
						<n-select
							size="small"
							v-model:value="resultFilter"
							:options="resultOptions"
							clearable
							placeholder="All"
							class="!w-40"
						/>
					</div>
				</div>
			</n-popover>
		</div>
		<div class="list my-3">
			<template v-if="itemsPaginated.length">
				<ScaResultItem v-for="item of itemsPaginated" :key="item.id" :data="item" embedded class="mb-2" />
			</template>
			<template v-else>
				<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
			</template>
		</div>
		<div class="footer flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="itemsFiltered.length"
				:page-slot="6"
				:simple="simpleMode"
				v-if="itemsPaginated.length > 3"
			/>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NPagination, NPopover, NButton, NSelect, NEmpty } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useResizeObserver } from "@vueuse/core"
import ScaResultItem from "./ScaResultItem.vue"
import type { Agent, AgentSca, ScaPolicyResult } from "@/types/agents.d"
import { watch } from "vue"

const { sca, agent } = defineProps<{ sca: AgentSca; agent: Agent }>()

const FilterIcon = "carbon:filter-edit"
const InfoIcon = "carbon:information"

const message = useMessage()
const loading = ref(false)
const resultsList = ref<ScaPolicyResult[]>([])
const total = computed(() => resultsList.value.length)
const totalFailed = computed(() => resultsList.value.filter(o => o.result === "failed").length)
const totalNA = computed(() => resultsList.value.filter(o => o.result === "not applicable").length)
const totalPassed = computed(() => resultsList.value.filter(o => o.result === "passed").length)
const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)
const resultFilter = ref<null | string>(null)
const resultOptions = [
	{ label: "Passed", value: "passed" },
	{ label: "Not applicable", value: "not applicable" },
	{ label: "Failed", value: "failed" }
]

const itemsFiltered = computed(() =>
	resultsList.value.filter(o => {
		if (!resultFilter.value) {
			return true
		}
		return resultFilter.value === o.result
	})
)

const itemsPaginated = computed(() => {
	const from = (currentPage.value - 1) * pageSize.value
	const to = currentPage.value * pageSize.value

	return itemsFiltered.value.slice(from, to)
})

watch(resultFilter, () => {
	currentPage.value = 1
})

function getSCAResults(agentId: string, policyId: string) {
	loading.value = true

	Api.agents
		.getSCAResults(agentId, policyId)
		.then(res => {
			if (res.data.success) {
				resultsList.value = res.data.sca_policy_results || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 650 ? 5 : 8
	simpleMode.value = width < 450
})

onBeforeMount(() => {
	if (agent?.agent_id && sca?.policy_id) getSCAResults(agent.agent_id, sca.policy_id)
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
	min-height: 200px;
}
</style>
