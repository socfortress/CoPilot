<template>
	<n-spin :show="loading" class="min-h-50">
		<n-alert v-if="error" title="Error" type="error">{{ error }}</n-alert>

		<template v-else>
			<n-alert
				v-if="requestError"
				type="warning"
				closable
				class="mb-4"
				data-testid="ai-request-error"
				@close="requestError = null"
			>
				{{ requestError }}
			</n-alert>

			<n-empty
				v-if="!loading && !analysis?.has_analysis"
				:description="emptyDescription"
				class="min-h-50 justify-center"
				data-testid="ai-report-empty"
			>
				<template v-if="analysis?.can_request" #extra>
					<AiAnalysisRequestButton
						:has-analysis="false"
						:in-progress
						:requesting
						@request="requestAnalysis"
					/>
				</template>
			</n-empty>

			<div v-else-if="analysis?.has_analysis" class="flex flex-col gap-4">
				<div class="flex flex-wrap items-center gap-2">
					<Chip
						v-if="report?.severity_assessment"
						:type="severityType"
						size="small"
						round
						:bordered="false"
						label="Severity"
						:value="report.severity_assessment"
					/>
					<Chip
						v-if="investigation"
						:type="statusType"
						size="small"
						round
						:bordered="false"
						label="Investigation"
						:value="investigation.status"
					/>
					<Chip
						v-if="investigation"
						size="small"
						round
						label="Started"
						:value="
							formatDate(investigation.started_at ?? investigation.created_at, dFormats.datetime) as string
						"
					/>
					<Chip
						v-if="investigation?.completed_at"
						size="small"
						round
						label="Completed"
						:value="formatDate(investigation.completed_at, dFormats.datetime) as string"
					/>
					<div v-if="analysis.can_request" class="ml-auto">
						<AiAnalysisRequestButton
							has-analysis
							:in-progress
							:requesting
							@request="requestAnalysis"
						/>
					</div>
				</div>

				<n-alert
					v-if="waitingForJob"
					type="info"
					:show-icon="false"
					title="AI analysis requested"
					data-testid="ai-request-pending"
				>
					The AI analyst will pick it up shortly. This page updates by itself, and the new findings replace these once it has finished.
				</n-alert>
				<n-alert
					v-else-if="investigationPending"
					type="info"
					:show-icon="false"
					title="Investigation in progress"
				>
					The AI analyst is still working on this alert. Findings will appear here once the investigation completes.
				</n-alert>

				<template v-if="report">
					<CardKV v-if="report.summary">
						<template #key>Summary</template>
						<template #default>{{ report.summary }}</template>
					</CardKV>

					<CardKV v-if="report.recommended_actions">
						<template #key>Recommended Actions</template>
						<template #default>{{ report.recommended_actions }}</template>
					</CardKV>

					<n-collapse v-if="report.report_markdown">
						<n-collapse-item title="Full Report" name="report">
							<Markdown :source="report.report_markdown" />
						</n-collapse-item>
					</n-collapse>

					<div v-if="analysis.iocs.length" class="flex flex-col gap-2">
						<div class="text-secondary text-sm">Indicators identified by the AI analyst</div>
						<CardEntity v-for="ioc of analysis.iocs" :key="ioc.id" size="small" embedded>
							<template #header-main>{{ ioc.ioc_value }}</template>
							<template #header-extra>{{ ioc.ioc_type }}</template>
							<template v-if="ioc.details" #default>{{ ioc.details }}</template>
							<template #footer-main>
								<div class="flex flex-wrap items-center gap-2">
									<Chip
										:type="verdictType(ioc.vt_verdict)"
										size="tiny"
										round
										:bordered="false"
										label="VT Verdict"
										:value="ioc.vt_verdict"
									/>
									<Chip v-if="ioc.vt_score" size="tiny" round label="VT Score" :value="ioc.vt_score" />
								</div>
							</template>
						</CardEntity>
					</div>

					<div class="text-secondary text-xs">
						Report generated {{ formatDate(report.created_at, dFormats.datetime) }}
					</div>
				</template>
			</div>
		</template>
	</n-spin>
</template>

<script setup lang="ts">
import type { TagProps } from "naive-ui"
import type { AiAlertAnalysis } from "@/types/aiReports"
import type { ApiError } from "@/types/common"
import axios from "axios"
import { NAlert, NCollapse, NCollapseItem, NEmpty, NSpin } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Chip from "@/components/common/Chip.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import AiAnalysisRequestButton from "./AiAnalysisRequestButton.vue"

// The portal never exposes Talon chat, review submission, palace lessons or replay —
// those stay in the SOC frontend. Where the customer allows it, a user can ask for an
// analysis (#1215); the tab then refreshes itself until the analysis has finished.
const props = defineProps<{
	alertId: number
}>()

const POLL_MS = 15_000
// The backend treats a job pending or running for longer as dead; so does the button.
const STALE_INVESTIGATION_MS = 2 * 60 * 60_000
// How long the tab expects Talon to start a request before it stops waiting for it.
const AWAIT_JOB_FOR_MS = 15 * 60_000
// Talon's job and the request are both stamped by the server, but by different steps.
const CLOCK_SKEW_MS = 60_000

// Markdown pulls in markdown-it and the code highlighter: only load them when a report is shown.
const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const dFormats = useSettingsStore().dateFormat

const loading = ref(false)
const error = ref<string | null>(null)
const analysis = ref<AiAlertAnalysis | null>(null)

let abortController: AbortController | null = null

const report = computed(() => analysis.value?.report ?? null)
const investigation = computed(() => analysis.value?.investigation ?? null)
const investigationPending = computed(
	() => !!investigation.value && ["pending", "running"].includes(investigation.value.status) && !report.value
)

/** The backend's timestamps are UTC without an offset. */
function utcMillis(value: string): number {
	return Date.parse(/(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`)
}

const requesting = ref(false)
const requestError = ref<string | null>(null)
/** When the backend accepted the latest request (its clock), and when the tab started waiting (ours). */
const awaiting = ref<{ requestedAt: number; since: number } | null>(null)

/** A request was accepted but Talon's investigation for it has not appeared yet. */
const waitingForJob = computed(() => {
	if (!awaiting.value) return false
	const started = investigation.value ? utcMillis(investigation.value.created_at) : null
	return started === null || started < awaiting.value.requestedAt - CLOCK_SKEW_MS
})

const inProgress = computed(() => {
	if (waitingForJob.value) return true
	const job = investigation.value
	return (
		!!job &&
		["pending", "running"].includes(job.status) &&
		Date.now() - utcMillis(job.created_at) < STALE_INVESTIGATION_MS
	)
})

// `enabled: false` only reaches here if the switch was flipped off while this
// alert was open — the tab itself is already gated on availability.
const emptyDescription = computed(() => {
	if (analysis.value && !analysis.value.enabled) return "AI analyst findings are not enabled for this customer"
	if (waitingForJob.value) return "AI analysis requested: the findings appear here once the AI analyst has finished"
	return "No AI analysis has been performed for this alert"
})

const severityType = computed<TagProps["type"]>(() => {
	switch (report.value?.severity_assessment) {
		case "Critical":
		case "High":
			return "error"
		case "Medium":
			return "warning"
		case "Low":
			return "success"
		default:
			return "default"
	}
})

const statusType = computed<TagProps["type"]>(() => {
	switch (investigation.value?.status) {
		case "completed":
			return "success"
		case "running":
			return "info"
		case "failed":
			return "error"
		default:
			return "default"
	}
})

function verdictType(verdict: string): TagProps["type"] {
	switch (verdict) {
		case "malicious":
			return "error"
		case "suspicious":
			return "warning"
		case "clean":
			return "success"
		default:
			return "default"
	}
}

async function loadAnalysis(quiet = false) {
	abortController?.abort()

	// Keep a local handle: a superseded request must not clear the loading flag
	// or overwrite the state of the request that replaced it.
	const controller = new AbortController()
	abortController = controller

	// A refresh while an analysis runs keeps the tab as it is instead of a spinner.
	if (!quiet) loading.value = true
	error.value = null

	try {
		const response = await Api.aiReports.getAlertAnalysis(props.alertId, controller.signal)
		if (abortController !== controller) return
		analysis.value = response.data
	} catch (err) {
		if (axios.isCancel(err) || abortController !== controller) return
		error.value = getApiErrorMessage(err as ApiError)
	} finally {
		if (abortController === controller) {
			loading.value = false
		}
	}
}

async function requestAnalysis() {
	requesting.value = true
	requestError.value = null
	try {
		const response = await Api.aiReports.requestAnalysis(props.alertId)
		awaiting.value = { requestedAt: utcMillis(response.data.requested_at), since: Date.now() }
		await loadAnalysis(true)
	} catch (err) {
		requestError.value =
			getApiErrorMessage(err as ApiError) || "The analysis could not be requested. Please try again later."
		// Refused because one is already running: show it.
		if ((err as ApiError).response?.status === 409) await loadAnalysis(true)
	} finally {
		requesting.value = false
	}
}

let poll: ReturnType<typeof setInterval> | null = null

function stopPolling() {
	if (poll) clearInterval(poll)
	poll = null
}

function refresh() {
	if (awaiting.value && Date.now() - awaiting.value.since > AWAIT_JOB_FOR_MS) awaiting.value = null
	loadAnalysis(true)
}

// While an analysis is under way (requested here, or started by the SOC), keep the tab current.
watch(inProgress, active => {
	stopPolling()
	if (active) poll = setInterval(refresh, POLL_MS)
})

watch(
	() => props.alertId,
	() => {
		analysis.value = null
		awaiting.value = null
		requestError.value = null
		loadAnalysis()
	},
	{ immediate: true }
)

onBeforeUnmount(() => {
	stopPolling()
	abortController?.abort()
})
</script>
