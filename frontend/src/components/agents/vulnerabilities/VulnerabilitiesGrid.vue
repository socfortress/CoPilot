<template>
	<n-spin class="vulnerabilities-section" content-class="min-h-48" :show="loading">
		<div class="toolbar">
			<n-form-item label="Severity" label-placement="left" size="small">
				<n-select v-model:value="severity" :options="severityOptions" class="max-w-48" />
			</n-form-item>
		</div>
		<div class="group">
			<VulnerabilityCard :vulnerability="item" v-for="item of vulnerabilities" :key="item.id" hide-tooltip />
		</div>
		<n-empty
			description="No vulnerabilities detected"
			class="justify-center h-48"
			v-if="!loading && !vulnerabilities.length"
		/>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs, watch, computed } from "vue"
import Api from "@/api"
import { type Agent, type AgentVulnerabilities } from "@/types/agents.d"
import VulnerabilityCard from "./VulnerabilityCard.vue"
import { nanoid } from "nanoid"
import { useMessage, NSpin, NEmpty, NFormItem, NSelect } from "naive-ui"
import type { VulnerabilitySeverityType } from "@/api/agents"

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const severity = ref<VulnerabilitySeverityType>("Critical")
const vulnerabilitiesCache = ref<{ [key in VulnerabilitySeverityType | string]: AgentVulnerabilities[] }>({})
const vulnerabilities = computed<AgentVulnerabilities[]>(() => vulnerabilitiesCache.value[severity.value] || [])

const severityOptions: { label: string; value: VulnerabilitySeverityType }[] = [
	{ label: "Critical", value: "Critical" },
	{ label: "High", value: "High" },
	{ label: "Medium", value: "Medium" },
	{ label: "Low", value: "Low" }
]

watch(severity, () => {
	if (agent?.value?.agent_id) getVulnerabilities(agent.value.agent_id)
})

function getVulnerabilities(id: string) {
	if (severity.value in vulnerabilitiesCache.value) {
		return
	}

	loading.value = true

	Api.agents
		.agentVulnerabilities(id, severity.value)
		.then(res => {
			if (res.data.success) {
				vulnerabilitiesCache.value[severity.value] = (res.data.vulnerabilities || []).map(o => {
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
