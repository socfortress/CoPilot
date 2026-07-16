<template>
	<n-spin :show="loading">
		<div v-if="resolvedHealthData" class="grid-auto-fit-200 grid gap-2" :class="embedded ? 'px-7 py-6' : ''">
			<CardKV v-for="(value, key) of resolvedHealthData" :key>
				<template #key>
					{{ key }}
				</template>
				<template #value>
					{{ value || "-" }}
				</template>
			</CardKV>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CustomerAgentsHealthcheckQuery } from "@/api/endpoints/customers"
import type { CustomerAgentHealth, CustomerHealthcheckSource } from "@/types/customers"
import { NSpin } from "naive-ui"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"

const props = withDefaults(
	defineProps<{
		healthData?: CustomerAgentHealth | null
		customerCode?: string | null
		source?: CustomerHealthcheckSource | null
		agentId?: string | null
		embedded?: boolean
	}>(),
	{ embedded: true }
)

const emit = defineEmits<{
	(e: "loaded", value: CustomerAgentHealth): void
}>()

function findAgentInResponse(
	data: {
		healthy_wazuh_agents?: CustomerAgentHealth[]
		unhealthy_wazuh_agents?: CustomerAgentHealth[]
		healthy_velociraptor_agents?: CustomerAgentHealth[]
		unhealthy_velociraptor_agents?: CustomerAgentHealth[]
	},
	source: CustomerHealthcheckSource,
	agentId: string
): CustomerAgentHealth | null {
	if (source === "wazuh") {
		return (
			[...(data.healthy_wazuh_agents || []), ...(data.unhealthy_wazuh_agents || [])].find(
				agent => agent.agent_id === agentId
			) ?? null
		)
	}

	return (
		[...(data.healthy_velociraptor_agents || []), ...(data.unhealthy_velociraptor_agents || [])].find(
			agent => agent.agent_id === agentId
		) ?? null
	)
}

// the backend has no by-id endpoint: we fetch the whole healthcheck agent list and pick the agent client-side
function loadHealthData(customerCode: string, source: CustomerHealthcheckSource, agentId: string, signal: AbortSignal) {
	const query: CustomerAgentsHealthcheckQuery | undefined = undefined
	const apiCall =
		source === "wazuh"
			? Api.customers.getCustomerAgentsHealthcheckWazuh(customerCode, query, signal)
			: Api.customers.getCustomerAgentsHealthcheckVelociraptor(customerCode, query, signal)

	return apiCall.then(res => {
		if (!res.data.success) {
			return { entity: null, message: res.data?.message }
		}

		return { entity: findAgentInResponse(res.data, source, agentId) }
	})
}

const { loading, entity: resolvedHealthData } = useEntityDetails<CustomerAgentHealth, string>({
	entity: () => props.healthData,
	id: () =>
		props.customerCode && props.source && props.agentId
			? `${props.customerCode}|${props.source}|${props.agentId}`
			: null,
	fetch: (_id, signal) =>
		loadHealthData(
			props.customerCode as string,
			props.source as CustomerHealthcheckSource,
			props.agentId as string,
			signal
		),
	notFoundMessage: "Health check agent not found.",
	errorMessage: "Failed to load health check agent.",
	onLoaded: value => emit("loaded", value)
})

defineExpose({ loading, resolvedHealthData })
</script>
