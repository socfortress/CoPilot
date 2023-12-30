<template>
	<n-spin :show="loading">
		<CardStatsDouble
			title="Agents"
			firstLabel="Total"
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
import { type Agent } from "@/types/agents.d"
import { isAgentOnline } from "@/components/agents/utils"
import CardStatsDouble from "@/components/common/CardStatsDouble.vue"
import CardStatsIcon from "@/components/common/CardStatsIcon.vue"
import Api from "@/api"
import { useMessage, NSpin } from "naive-ui"

const AgentsIcon = "carbon:network-3"
const message = useMessage()
const loading = ref(false)
const agents = ref<Agent[]>([])

const total = computed<number>(() => {
	return agents.value.length || 0
})

const onlineTotal = computed(() => {
	return agents.value.filter(({ online }) => online).length || 0
})

function getData() {
	loading.value = true

	Api.agents
		.getAgents()
		.then(res => {
			if (res.data.success) {
				agents.value = (res.data.agents || []).map(o => {
					o.online = isAgentOnline(o.wazuh_last_seen)
					return o
				})
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
