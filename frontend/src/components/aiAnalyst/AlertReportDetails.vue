<template>
	<n-spin :show="loading" class="flex grow flex-col" content-class="flex grow flex-col">
		<n-tabs
			v-if="resolvedAlert"
			v-model:value="tabActive"
			type="line"
			animated
			:tabs-padding="fullWidth ? 0 : 24"
			class="grow"
			pane-wrapper-class="flex grow flex-col"
		>
			<n-tab-pane name="summary" tab="Summary" display-directive="show:lazy" class="flex grow flex-col">
				<div :class="fullWidth ? 'p-0 pt-3' : 'p-6 pt-3'">
					<div class="flex flex-col gap-4">
						<div v-if="report?.severity_assessment" class="flex items-center gap-2">
							<Badge type="splitted" bright :color="severityColor">
								<template #label>Severity</template>
								<template #value>{{ report.severity_assessment }}</template>
							</Badge>
						</div>
						<CardKV v-if="report?.summary">
							<template #key>Summary</template>
							<template #value>{{ report.summary }}</template>
						</CardKV>
						<CardKV v-if="report?.recommended_actions">
							<template #key>Recommended Actions</template>
							<template #value>{{ report.recommended_actions }}</template>
						</CardKV>
						<div v-if="!report?.summary && !report?.recommended_actions">
							<n-empty description="No summary available" class="h-40" />
						</div>
					</div>
				</div>
			</n-tab-pane>
			<n-tab-pane name="report" tab="Full Report" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0 pt-3' : 'p-6 pt-3'">
					<Markdown v-if="report?.report_markdown" :source="report.report_markdown" breaks />
					<n-empty v-else description="No report content available" class="h-40" />
				</div>
			</n-tab-pane>
			<n-tab-pane name="iocs" tab="IOCs" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0 pt-3' : 'p-6 pt-3'">
					<AlertReportIocsList :alert-id="resolvedAlert.alert_id" />
				</div>
			</n-tab-pane>
			<n-tab-pane name="jobs" tab="Jobs" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0 pt-3' : 'p-6 pt-3'">
					<AlertReportJobsList :alert-id="resolvedAlert.alert_id" />
				</div>
			</n-tab-pane>
			<n-tab-pane v-if="report" name="review" tab="Review" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0 pt-3' : 'p-6 pt-3'">
					<AlertReportReviewPanel :report />
				</div>
			</n-tab-pane>
			<n-tab-pane v-if="report && resolvedAlert" name="compare" tab="Compare" display-directive="show:lazy">
				<div :class="fullWidth ? 'p-0 pt-3' : 'p-6 pt-3'">
					<AlertReportCompare :alert-id="resolvedAlert.alert_id" :current-report-id="report.id" />
				</div>
			</n-tab-pane>
		</n-tabs>
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertWithReport } from "@/types/ai-analyst"
import type { ApiError } from "@/types/common"
import axios from "axios"
import { NEmpty, NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Markdown from "@/components/common/Markdown.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	alert?: AlertWithReport | null
	alertId?: number | null
	reportId?: number | null
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: AlertWithReport): void
	(e: "tab-change", value: string): void
}>()

const AlertReportIocsList = defineAsyncComponent(() => import("./AlertReportIocsList.vue"))
const AlertReportJobsList = defineAsyncComponent(() => import("./AlertReportJobsList.vue"))
const AlertReportReviewPanel = defineAsyncComponent(() => import("./AlertReportReviewPanel/AlertReportReviewPanel.vue"))
const AlertReportCompare = defineAsyncComponent(() => import("./AlertReportCompare/AlertReportCompare.vue"))

const message = useMessage()
const tabActive = ref("summary")
const loading = ref(false)
const fetchedAlert = ref<AlertWithReport | null>(null)

let abortController: AbortController | null = null

const resolvedAlert = computed(() => props.alert ?? fetchedAlert.value)
const report = computed(() => resolvedAlert.value?.report)

const severityColor = computed(() => {
	const severity = report.value?.severity_assessment
	if (severity === "Critical" || severity === "High") return "danger"
	if (severity === "Medium") return "warning"
	if (severity === "Low" || severity === "Informational") return "success"
	return undefined
})

function loadAlert() {
	const { alertId, reportId } = props
	const request =
		alertId != null
			? Api.aiAnalyst.getAlertWithReportByAlertId(alertId, abortController?.signal)
			: reportId != null
				? Api.aiAnalyst.getAlertWithReportByReportId(reportId, abortController?.signal)
				: null

	if (!request) return

	loading.value = true

	request
		.then(res => {
			loading.value = false

			if (res.data.success && res.data.alert) {
				fetchedAlert.value = res.data.alert
				emit("loaded", res.data.alert)
			} else {
				message.warning(res.data?.message || "Alert not found.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to load alert.")
				loading.value = false
			}
		})
}

watch(
	() => [props.alert, props.alertId, props.reportId] as const,
	([alert, alertId, reportId]) => {
		if (alert) {
			abortController?.abort()
			fetchedAlert.value = null
			loading.value = false
			emit("loaded", alert)
			return
		}

		if (alertId != null || reportId != null) {
			abortController?.abort()
			abortController = new AbortController()
			loadAlert()
			return
		}

		abortController?.abort()
		fetchedAlert.value = null
		loading.value = false
	},
	{ immediate: true }
)

watch(
	tabActive,
	value => {
		emit("tab-change", value)
	},
	{ immediate: true }
)

defineExpose({ loading, resolvedAlert })
</script>
