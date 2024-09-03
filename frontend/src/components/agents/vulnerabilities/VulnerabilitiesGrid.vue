<template>
	<div class="vulnerabilities-section">
		<div class="toolbar flex items-center gap-3 mb-8">
			<n-form-item label="Severity" label-placement="left" size="small" :show-feedback="false">
				<n-select v-model:value="severity" :options="severityOptions" class="!w-28" />
			</n-form-item>

			<n-button
				v-if="vulnerabilities.length && !loading"
				:loading="downloading"
				size="small"
				@click="vulnerabilitiesDownload(agent.agent_id)"
			>
				Download CSV
			</n-button>
		</div>
		<n-spin content-class="min-h-48" :show="loading">
			<div class="group gap-4 grid grid-auto-fill-200">
				<VulnerabilityCard :vulnerability="item" v-for="item of vulnerabilities" :key="item.id" hide-tooltip />
			</div>
			<n-empty
				description="No vulnerabilities detected"
				class="justify-center h-48"
				v-if="!loading && !vulnerabilities.length"
			/>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs, watch, computed } from "vue"
import { NButton, NSpin, NEmpty, NFormItem, NSelect, useMessage } from "naive-ui"
import Api from "@/api"
import VulnerabilityCard from "./VulnerabilityCard.vue"
import { nanoid } from "nanoid"
import axios from "axios"
import { saveAs } from "file-saver"
import type { VulnerabilitySeverityType } from "@/api/endpoints/agents"
import { type Agent, type AgentVulnerabilities } from "@/types/agents.d"

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

let abortController: AbortController | null = null
const message = useMessage()
const loading = ref(false)
const downloading = ref(false)
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

	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	Api.agents
		.agentVulnerabilities(id, severity.value, abortController.signal)
		.then(res => {
			if (res.data.success) {
				vulnerabilitiesCache.value[severity.value] = (res.data.vulnerabilities || []).map(o => {
					o.id = nanoid()
					return o
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
			loading.value = false
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				vulnerabilitiesCache.value[severity.value] = []

				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				loading.value = false
			}
		})
}

function vulnerabilitiesDownload(id: string) {
	downloading.value = true

	const fileName = `agent-${id}_${severity.value.toLowerCase()}-vulnerabilities.csv`

	Api.agents
		.agentVulnerabilitiesDownload(id, severity.value)
		.then(res => {
			if (res.data) {
				saveAs(new Blob([res.data], { type: "text/csv;charset=utf-8" }), fileName)
			} else {
				message.warning("An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			downloading.value = false
		})
}

onBeforeMount(() => {
	if (agent?.value?.agent_id) getVulnerabilities(agent.value.agent_id)
})
</script>
