<template>
	<n-spin :show="loading">
		<div class="flex min-h-28 flex-col gap-2">
			<AgentCard
				v-for="agent in list"
				:key="agent.agent_id"
				:agent
				embedded
				show-actions
				class="item-appear item-appear-bottom item-appear-005"
				@delete="getAgents()"
				@click="gotoAgent(agent.agent_id)"
			/>
			<n-empty v-if="!list.length" description="No Agents found" class="h-48 justify-center" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents.d"
import type { Customer } from "@/types/customers.d"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import AgentCard from "@/components/agents/AgentCard.vue"
import { useGoto } from "@/composables/useGoto"

const props = defineProps<{
	customer: Customer
}>()
const { customer } = toRefs(props)

const loading = ref(false)
const { gotoAgent } = useGoto()
const message = useMessage()
const list = ref<Agent[] | []>([])

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
