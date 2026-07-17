<template>
	<n-spin :show="loading" content-class="h-full">
		<CardStatsMulti title="Agents" hovered class="h-full cursor-pointer" :values @click="routeAgent().navigate()">
			<template #icon>
				<CardStatsIcon :icon-name="AgentsIcon" boxed :box-size="30"></CardStatsIcon>
			</template>
		</CardStatsMulti>
	</n-spin>
</template>

<script setup lang="ts">
import type { ItemProps } from "@/components/common/cards/CardStatsMulti.vue"
import type { Agent } from "@/types/agents"
import type { ApiError } from "@/types/common"
import { NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import CardStatsIcon from "@/components/common/cards/CardStatsIcon.vue"
import CardStatsMulti from "@/components/common/cards/CardStatsMulti.vue"
import { useNavigation } from "@/composables/useNavigation"
import { AgentStatus } from "@/types/agents"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	customerCodes?: string[]
}>()

const AgentsIcon = "carbon:network-3"
const { routeAgent } = useNavigation()
const message = useMessage()
const loading = ref(false)
const agents = ref<Agent[]>([])
const total = computed<number>(() => {
	return agents.value.length || 0
})
const onlineTotal = computed(() => {
	return agents.value.filter(({ wazuh_agent_status }) => wazuh_agent_status === AgentStatus.Active).length || 0
})
const values = computed<ItemProps[]>(() => [
	{ value: total.value, label: "Total" },
	{ value: onlineTotal.value, label: "Online", status: onlineTotal.value ? "success" : undefined }
])

function getData() {
	loading.value = true

	Api.agents
		.getAgents(
			props.customerCodes && props.customerCodes.length
				? { customerCodes: props.customerCodes }
				: undefined
		)
		.then(res => {
			if (res.data.success) {
				agents.value = res.data.agents || []
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
	getData()
})

watch(
	() => (props.customerCodes || []).slice(),
	() => {
		getData()
	}
)
</script>
