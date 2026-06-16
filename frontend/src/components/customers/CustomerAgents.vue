<template>
	<n-spin :show="loading">
		<div class="flex min-h-28 flex-col gap-2 p-px">
			<div v-if="sortedList.length" class="mb-2 flex justify-end">
				<n-button type="primary" @click="exportToCSV">
					<template #icon>
						<Icon :name="DownloadIcon" />
					</template>
					Export
				</n-button>
			</div>
			<AgentCard
				v-for="agent in sortedList"
				:key="agent.agent_id"
				:agent
				embedded
				show-actions
				class="item-appear item-appear-bottom item-appear-005"
			>
				<template #actions-left>
					<n-tooltip to="body">
						<span class="text-sm">Open in new tab</span>
						<template #trigger>
							<n-button text size="small" type="primary" @click.stop="openAgentInNewTab(agent.agent_id)">
								<template #icon>
									<Icon name="carbon:launch" />
								</template>
								Open
							</n-button>
						</template>
					</n-tooltip>
				</template>
			</AgentCard>
			<n-empty v-if="!sortedList.length" description="No Agents found" class="h-48 justify-center" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
// TODO-FE: refactor
import type { Agent } from "@/types/agents.d"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers.d"
import { saveAs } from "file-saver"
import _sortBy from "lodash/sortBy"
import { NButton, NEmpty, NSpin, NTooltip, useMessage } from "naive-ui"
import Papa from "papaparse"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import AgentCard from "@/components/agents/AgentCard.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	customer: Customer
}>()
const { customer } = toRefs(props)

const DownloadIcon = "carbon:download"

const loading = ref(false)
const router = useRouter()
const message = useMessage()
const list = ref<Agent[] | []>([])

const sortedList = computed(() => _sortBy(list.value, "critical_asset").reverse())

function exportToCSV() {
	if (!sortedList.value.length) {
		message.warning("No agents to export")
		return
	}

	const csv = Papa.unparse(sortedList.value, {
		header: true
	})

	const filename = `agents_${customer.value.customer_code}_${new Date().toISOString().split("T")[0]}.csv`
	const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
	saveAs(blob, filename)

	message.success("Export completed successfully")
}

function openAgentInNewTab(agentId: string) {
	const route = router.resolve({ name: "Agent", params: { id: agentId } })
	window.open(route.href, "_blank")
}

function getAgents() {
	loading.value = true

	Api.customers
		.getCustomerAgents(customer.value.customer_code)
		.then(res => {
			if (res.data.success) {
				list.value = res.data.agents || []
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getAgents()
})
</script>
