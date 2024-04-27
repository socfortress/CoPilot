<template>
	<n-spin :show="loading">
		<div class="customer-agents flex flex-col gap-2">
			<AgentCard
				v-for="agent in list"
				:key="agent.agent_id"
				:agent="agent"
				bg-secondary
				show-actions
				@delete="getAgents()"
				@click="gotoAgent(agent.agent_id)"
				class="item-appear item-appear-bottom item-appear-005"
			/>
			<n-empty v-if="!list.length" description="No Agents found" class="justify-center h-48" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { onBeforeMount, ref, toRefs } from "vue"
import AgentCard from "@/components/agents/AgentCard.vue"
import Api from "@/api"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import type { Customer } from "@/types/customers.d"
import type { Agent } from "@/types/agents.d"
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

<style lang="scss" scoped>
.customer-agents {
	min-height: 100px;
}
</style>
