<template>
	<n-select
		to="body"
		:value="selectedCritical"
		:options="criticalOptions"
		:loading
		size="small"
		class="min-w-36"
		:consistent-menu-width="false"
		@update:value="handleCriticalChange"
	/>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import { NSelect, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

export interface AgentCriticalUpdateSuccessPayload {
	agentId: string | number
	critical: boolean
}

export interface AgentCriticalUpdateErrorPayload {
	agentId: string | number
	critical: boolean
	message: string
}

const props = defineProps<{
	agentId: string | number
	critical: boolean
}>()

const emit = defineEmits<{
	success: [AgentCriticalUpdateSuccessPayload]
	error: [AgentCriticalUpdateErrorPayload]
}>()

const message = useMessage()

const criticalOptions = [
	{ label: "Critical", value: "CRITICAL" },
	{ label: "Not Critical", value: "NOT_CRITICAL" }
]

const selectedCritical = ref<string>(props.critical ? "CRITICAL" : "NOT_CRITICAL")
const loading = ref(false)

watch(
	() => props.critical,
	newCritical => {
		selectedCritical.value = newCritical ? "CRITICAL" : "NOT_CRITICAL"
	}
)

async function handleCriticalChange(value: string) {
	if (loading.value || value === selectedCritical.value) return

	const previousCritical = selectedCritical.value
	selectedCritical.value = value
	loading.value = true

	try {
		if (selectedCritical.value === "CRITICAL") {
			await Api.agents.markAgentAsCritical(props.agentId.toString())
		} else {
			await Api.agents.markAgentAsNotCritical(props.agentId.toString())
		}
		message.success(
			`Agent criticality updated to ${selectedCritical.value === "CRITICAL" ? "Critical" : "Not Critical"}`
		)
		emit("success", {
			agentId: props.agentId,
			critical: selectedCritical.value === "CRITICAL"
		})
	} catch (err) {
		selectedCritical.value = previousCritical
		message.error(getApiErrorMessage(err as ApiError))
		emit("error", {
			agentId: props.agentId,
			critical: previousCritical === "CRITICAL",
			message: getApiErrorMessage(err as ApiError)
		})
	} finally {
		loading.value = false
	}
}
</script>
