<template>
	<n-spin :show="loading">
		<div class="flex min-h-28 flex-col gap-2">
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
				@delete="getAgents()"
				@click="openAgentInNewTab(agent.agent_id)"
			/>
			<n-empty v-if="!sortedList.length" description="No Agents found" class="h-48 justify-center" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
// TODO: refactor
import type { Agent } from "@/types/agents.d"
import type { Customer } from "@/types/customers.d"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import AgentCard from "@/components/agents/AgentCard.vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	customer: Customer
}>()
const { customer } = toRefs(props)

const DownloadIcon = "carbon:download"

const loading = ref(false)
const router = useRouter()
const message = useMessage()
const list = ref<Agent[] | []>([])

const sortedList = computed(() => {
	return [...list.value].sort((a, b) => {
		return a.hostname.toLowerCase().localeCompare(b.hostname.toLowerCase())
	})
})

function exportToCSV() {
	if (!sortedList.value.length) {
		message.warning("No agents to export")
		return
	}

	// CSV headers
	const headers = [
		"customer_code",
		"agent_id",
		"hostname",
		"ip_address",
		"os",
		"wazuh_last_seen",
		"velociraptor_last_seen"
	]

	// Create CSV content
	const csvContent = [
		headers.join(","),
		...sortedList.value.map(agent => {
			return [
				agent.customer_code || "",
				agent.agent_id,
				`"${agent.hostname.replace(/"/g, '""')}"`, // Escape quotes in hostname
				agent.ip_address,
				`"${agent.os.replace(/"/g, '""')}"`, // Escape quotes in OS
				agent.wazuh_last_seen,
				agent.velociraptor_last_seen || ""
			].join(",")
		})
	].join("\n")

	// Create blob and download
	const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
	const link = document.createElement("a")
	const url = URL.createObjectURL(blob)

	const filename = `agents_${customer.value.customer_code}_${new Date().toISOString().split("T")[0]}.csv`

	link.setAttribute("href", url)
	link.setAttribute("download", filename)
	link.style.visibility = "hidden"
	document.body.appendChild(link)
	link.click()
	document.body.removeChild(link)

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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getAgents()
})
</script>
