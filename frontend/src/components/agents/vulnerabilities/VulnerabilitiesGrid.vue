<template>
	<div class="vulnerabilities-section">
		<div class="toolbar mb-8 flex items-center gap-3">
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
			<div class="grid-auto-fill-200 group grid gap-4">
				<VulnerabilityCard v-for="item of vulnerabilities" :key="item.id" :vulnerability="item" hide-tooltip />
			</div>
			<n-empty
				v-if="!loading && !vulnerabilities.length"
				description="No vulnerabilities detected"
				class="h-48 justify-center"
			/>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { VulnerabilitySeverityType } from "@/api/endpoints/agents"
import type { Agent, AgentVulnerabilities } from "@/types/agents.d"
import Api from "@/api"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import axios from "axios"
import { saveAs } from "file-saver"
import { NButton, NEmpty, NFormItem, NSelect, NSpin, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import VulnerabilityCard from "./VulnerabilityCard.vue"

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

let abortController: AbortController | null = null
const message = useMessage()
const loading = ref(false)
const dFormats = useSettingsStore().dateFormat
const downloading = ref(false)
const severity = ref<VulnerabilitySeverityType>("Critical")
const vulnerabilitiesCache = ref<{ [key in VulnerabilitySeverityType | string]: AgentVulnerabilities[] }>({})
const vulnerabilities = computed<AgentVulnerabilities[]>(() => vulnerabilitiesCache.value[severity.value] || [])

const severityOptions: { label: string; value: VulnerabilitySeverityType }[] = [
	{ label: "All", value: "All" },
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

	const fileName = `vulnerabilities_agent:${id}_severity:${severity.value.toLowerCase()}_${formatDate(
		new Date(),
		dFormats.datetimesec
	)}.csv`

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
