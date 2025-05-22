<template>
	<n-spin :show="loading">
		<CardStatsMulti title="Agents" hovered class="h-full cursor-pointer" :values @click="gotoAgent()">
			<template #icon>
				<CardStatsIcon :icon-name="AgentsIcon" boxed :box-size="30"></CardStatsIcon>
			</template>
		</CardStatsMulti>
	</n-spin>
</template>

<script setup lang="ts">
import type { ItemProps } from "@/components/common/cards/CardStatsMulti.vue"
import type { Agent } from "@/types/agents.d"
import { NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardStatsIcon from "@/components/common/cards/CardStatsIcon.vue"
import CardStatsMulti from "@/components/common/cards/CardStatsMulti.vue"
import { useGoto } from "@/composables/useGoto"
import { AgentStatus } from "@/types/agents.d"

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
const values = computed<ItemProps[]>(() => [
	{ value: total.value, label: "Total" },
	{ value: onlineTotal.value, label: "Online", status: onlineTotal.value ? "success" : undefined }
])

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
