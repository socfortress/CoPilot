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
import type { ApiError } from "@/types/common"
import type { CustomerAgentHealth, CustomerHealthcheckSource } from "@/types/customers"
import axios from "axios"
import { NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import { getApiErrorMessage } from "@/utils"

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

const message = useMessage()
const loading = ref(false)
const fetchedHealthData = ref<CustomerAgentHealth | null>(null)

let abortController: AbortController | null = null

const resolvedHealthData = computed(() => props.healthData ?? fetchedHealthData.value)

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

function loadHealthData(customerCode: string, source: CustomerHealthcheckSource, agentId: string) {
	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	const query: CustomerAgentsHealthcheckQuery | undefined = undefined
	const apiCall =
		source === "wazuh"
			? Api.customers.getCustomerAgentsHealthcheckWazuh(customerCode, query, abortController.signal)
			: Api.customers.getCustomerAgentsHealthcheckVelociraptor(customerCode, query, abortController.signal)

	apiCall
		.then(res => {
			loading.value = false

			if (!res.data.success) {
				message.warning(res.data?.message || "Health check agent not found.")
				return
			}

			const agent = findAgentInResponse(res.data, source, agentId)
			if (agent) {
				fetchedHealthData.value = agent
				emit("loaded", agent)
			} else {
				message.warning("Health check agent not found.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to load health check agent.")
				loading.value = false
			}
		})
}

watch(
	() => [props.healthData, props.customerCode, props.source, props.agentId] as const,
	([healthData, customerCode, source, agentId]) => {
		if (healthData) {
			abortController?.abort()
			fetchedHealthData.value = null
			loading.value = false
			return
		}

		if (customerCode && source && agentId) {
			loadHealthData(customerCode, source, agentId)
			return
		}

		abortController?.abort()
		fetchedHealthData.value = null
		loading.value = false
	},
	{ immediate: true }
)

defineExpose({ loading, resolvedHealthData })
</script>
