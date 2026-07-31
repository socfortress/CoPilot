<template>
	<n-spin :show="loading" class="min-h-50">
		<n-alert v-if="error" title="Error" type="error" :description="error" />

		<n-empty
			v-else-if="!loading && !analysis?.has_analysis"
			:description="emptyDescription"
			class="min-h-50 justify-center"
		/>

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
			</div>

			<n-alert
				v-if="investigationPending"
				type="info"
				:show-icon="false"
				title="Investigation in progress"
				description="The AI analyst is still working on this alert. Findings will appear here once the investigation completes."
			/>

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
	</n-spin>
</template>

<script setup lang="ts">
import type { TagProps } from "naive-ui"
import type { AiAlertAnalysis } from "@/types/aiReports"
import type { ApiError } from "@/types/common"
import axios from "axios"
import { NAlert, NCollapse, NCollapseItem, NEmpty, NSpin } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Chip from "@/components/common/Chip.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

// Read-only by design: the portal never exposes Talon chat, review submission,
// palace lessons or replay — those stay in the SOC frontend.
const props = defineProps<{
	alertId: number
}>()

const dFormats = useSettingsStore().dateFormat

const loading = ref(false)
const error = ref<string | null>(null)
const analysis = ref<AiAlertAnalysis | null>(null)

let abortController: AbortController | null = null

const report = computed(() => analysis.value?.report ?? null)
const investigation = computed(() => analysis.value?.investigation ?? null)
// `enabled: false` only reaches here if the switch was flipped off while this
// alert was open — the tab itself is already gated on availability.
const emptyDescription = computed(() =>
	analysis.value && !analysis.value.enabled
		? "AI analyst findings are not enabled for this customer"
		: "No AI analysis has been performed for this alert"
)
const investigationPending = computed(
	() => !!investigation.value && ["pending", "running"].includes(investigation.value.status) && !report.value
)

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

async function loadAnalysis() {
	abortController?.abort()

	// Keep a local handle: a superseded request must not clear the loading flag
	// or overwrite the state of the request that replaced it.
	const controller = new AbortController()
	abortController = controller

	loading.value = true
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

watch(
	() => props.alertId,
	() => {
		analysis.value = null
		loadAnalysis()
	},
	{ immediate: true }
)

onBeforeUnmount(() => {
	abortController?.abort()
})
</script>
