<template>
	<n-spin :show="loading">
		<CardStatsDouble
			title="Agents"
			firstLabel="Total"
			hovered
			class="cursor-pointer"
			@click="gotoAgent()"
			:value="total"
			secondLabel="Online"
			:subValue="onlineTotal"
			:secondStatus="onlineTotal ? 'success' : undefined"
		>
			<template #icon>
				<CardStatsIcon :iconName="AgentsIcon" boxed :boxSize="30"></CardStatsIcon>
			</template>
		</CardStatsDouble>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref } from "vue"
import { AgentStatus, type Agent } from "@/types/agents.d"
import CardStatsDouble from "@/components/common/CardStatsDouble.vue"
import CardStatsIcon from "@/components/common/CardStatsIcon.vue"
import Api from "@/api"
import { useMessage, NSpin } from "naive-ui"
import { useGoto } from "@/composables/useGoto"

const AgentsIcon = "carbon:network-3"
const { gotoAgent } = useGoto()
const message = useMessage()
const loading = ref(false)
const agents = ref<Agent[]>([])

const total = computed<number>(() => {
	return agents.value.length || 0
})

const onlineTotal = computed(() => {
	return agents.value.filter(({ wazuh_agent_status }) => wazuh_agent_status === AgentStatus.Active).length || 0
})

function getData() {
	loading.value = true

	Api.agents
		.getAgents()
		.then(res => {
			if (res.data.success) {
				agents.value = res.data.agents || []
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
	getData()
})
</script>

<style lang="scss" scoped>
.n-spin-container {
	:deep() {
		.n-spin-content {
			height: 100%;
		}
	}
}
</style>
