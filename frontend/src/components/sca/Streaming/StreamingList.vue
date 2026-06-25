<template>
	<div class="flex flex-col gap-4">
		<StreamingStatisticsSummary v-if="streamComplete && stats" :stats />

		<StreamingProgressHeader
			:is-connecting
			:is-streaming
			:stream-complete
			:stream-error
			:progress
			:status-message
			:results-count="results.length"
			@start="startStream"
			@stop="stopStream"
		/>

		<StreamingFilters @submit="applyFilters" />

		<StreamingResultsList
			:is-connecting
			:is-streaming
			:stream-complete
			:has-results="filteredResults.length > 0"
			:data="paginatedResults"
			:pagination
			@start="startStream"
		/>

		<n-alert v-if="streamError" type="error" class="mt-4" closable @close="streamError = null">
			<template #header>Stream Error</template>
			{{ streamError }}
		</n-alert>
	</div>
</template>

<script setup lang="ts">
import type { ScaStreamingFilters, ScaStreamingListFilter } from "./types.d"
import type { ApiError } from "@/types/common.ts"
import type { AgentScaOverviewItem, ScaStreamComplete, ScaStreamProgress } from "@/types/sca"
import { NAlert, useMessage } from "naive-ui"
import { computed, onBeforeUnmount, reactive, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils/index.ts"
import StreamingFilters from "./StreamingFilters.vue"
import StreamingProgressHeader from "./StreamingProgressHeader.vue"
import StreamingResultsList from "./StreamingResultsList.vue"
import StreamingStatisticsSummary from "./StreamingStatisticsSummary.vue"
import { scaStreamingListToFilters } from "./utils"

const message = useMessage()

const isConnecting = ref(false)
const isStreaming = ref(false)
const streamComplete = ref(false)
const streamError = ref<string | null>(null)
const results = ref<AgentScaOverviewItem[]>([])
const stats = ref<ScaStreamComplete | null>(null)
const abortController = ref<AbortController | null>(null)

const progress = reactive<ScaStreamProgress>({
	processed: 0,
	total: 0,
	successful: 0,
	failed: 0,
	results_so_far: 0,
	percent_complete: 0
})

const filters = reactive<ScaStreamingFilters>({
	customer_code: undefined,
	agent_name: undefined,
	policy_name: undefined,
	min_score: undefined,
	max_score: undefined
})

const statusMessage = computed(() => {
	if (isConnecting.value) return "Connecting..."
	if (isStreaming.value) return `Collecting SCA data... ${progress.processed}/${progress.total} agents`
	if (streamComplete.value) return stats.value?.message || "Collection complete"
	return "Ready to load SCA data"
})

const filteredResults = computed(() => {
	return results.value.filter(item => {
		if (filters.policy_name && !item.policy_name.toLowerCase().includes(filters.policy_name.toLowerCase())) {
			return false
		}
		return true
	})
})

const pagination = reactive({
	page: 1,
	pageSize: 25,
	showSizePicker: true,
	pageSizes: [10, 25, 50, 100],
	itemCount: computed(() => filteredResults.value.length),
	onChange: (page: number) => {
		pagination.page = page
	},
	onUpdatePageSize: (pageSize: number) => {
		pagination.pageSize = pageSize
		pagination.page = 1
	}
})

const paginatedResults = computed(() => {
	const start = (pagination.page - 1) * pagination.pageSize
	const end = start + pagination.pageSize
	return filteredResults.value.slice(start, end)
})

async function startStream() {
	results.value = []
	stats.value = null
	streamError.value = null
	streamComplete.value = false
	isConnecting.value = true

	Object.assign(progress, {
		processed: 0,
		total: 0,
		successful: 0,
		failed: 0,
		results_so_far: 0,
		percent_complete: 0
	})

	if (abortController.value) {
		abortController.value.abort()
	}

	abortController.value = new AbortController()

	const query: ScaStreamingFilters = {}
	if (filters.customer_code) query.customer_code = filters.customer_code
	if (filters.agent_name) query.agent_name = filters.agent_name
	if (filters.policy_name) query.policy_name = filters.policy_name
	if (filters.min_score !== undefined) query.min_score = filters.min_score
	if (filters.max_score !== undefined) query.max_score = filters.max_score

	try {
		await Api.sca.streamScaOverview(
			query,
			{
				onStart(data) {
					isConnecting.value = false
					isStreaming.value = true
					progress.total = data.total_agents
					message.info(data.message)
				},
				onAgentResult(data) {
					for (const policy of data.policies) {
						results.value.push({
							agent_id: data.agent_id,
							agent_name: data.agent_name,
							customer_code: data.customer_code,
							policy_id: policy.policy_id,
							policy_name: policy.policy_name,
							description: policy.description,
							total_checks: policy.total_checks,
							pass: policy.pass_count,
							fail: policy.fail_count,
							invalid: policy.invalid_count,
							score: policy.score,
							start_scan: policy.start_scan,
							end_scan: policy.end_scan,
							references: policy.references,
							hash_file: policy.hash_file
						})
					}
				},
				onAgentEmpty(data) {
					console.warn(`Agent ${data.agent_name} has no SCA data`)
				},
				onProgress(data) {
					Object.assign(progress, data)
				},
				onComplete(data) {
					stats.value = data
					isStreaming.value = false
					streamComplete.value = true
					results.value.sort((a, b) => a.score - b.score)
					message.success(data.message)
				},
				onError(error) {
					const errorMessage =
						error instanceof Error ? error.message : error.message || error.error || "Unknown error"
					console.warn("Stream error:", error)
					if (!streamComplete.value) {
						streamError.value = errorMessage
					}
					progress.failed++
				}
			},
			abortController.value
		)
	} catch (error) {
		const errorMessage = getApiErrorMessage(error as ApiError)
		if (errorMessage !== "AbortError") {
			streamError.value = errorMessage || "Connection error"
			console.error("Stream connection error:", errorMessage)
		}
	} finally {
		isStreaming.value = false
		isConnecting.value = false
	}
}

function stopStream() {
	if (abortController.value) {
		abortController.value.abort()
		abortController.value = null
	}
	isStreaming.value = false
	isConnecting.value = false
	message.warning("Stream stopped by user")
}

function applyFilters(newFilters: ScaStreamingListFilter[]) {
	const nextFilters = scaStreamingListToFilters(newFilters)
	filters.customer_code = nextFilters.customer_code
	filters.agent_name = nextFilters.agent_name
	filters.policy_name = nextFilters.policy_name
	filters.min_score = nextFilters.min_score
	filters.max_score = nextFilters.max_score
	pagination.page = 1
}

onBeforeUnmount(() => {
	if (abortController.value) {
		abortController.value.abort()
	}
})
</script>
