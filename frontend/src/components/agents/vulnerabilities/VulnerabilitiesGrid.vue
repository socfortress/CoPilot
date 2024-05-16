<template>
	<n-spin class="vulnerabilities-section" :show="loading">
		<div class="group">
			<VulnerabilityCard :vulnerability="item" v-for="item of vulnerabilities" :key="item.id" />
		</div>
		<n-empty
			description="No vulnerabilities detected"
			class="justify-center h-48"
			v-if="!loading && !vulnerabilities.length"
		/>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs } from "vue"
import Api from "@/api"
import { type Agent, type AgentVulnerabilities } from "@/types/agents.d"
import VulnerabilityCard from "./VulnerabilityCard.vue"
import { nanoid } from "nanoid"
import { useMessage, NSpin, NEmpty } from "naive-ui"

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const vulnerabilities = ref<AgentVulnerabilities[]>([])

function getVulnerabilities(id: string) {
	loading.value = true

	Api.agents
		.agentVulnerabilities(id)
		.then(res => {
			if (res.data.success) {
				vulnerabilities.value = (res.data.vulnerabilities || []).map(o => {
					o.id = nanoid()
					return o
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
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
	if (agent?.value?.agent_id) getVulnerabilities(agent.value.agent_id)
})
</script>

<style lang="scss" scoped>
.vulnerabilities-section {
	container-type: inline-size;
	min-height: 100px;

	.group {
		@apply gap-4;
		width: 100%;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
		grid-auto-flow: row dense;
	}

	@container (max-width: 500px) {
		.group {
			grid-template-columns: repeat(auto-fit, 100%);
		}
	}
}
</style>
