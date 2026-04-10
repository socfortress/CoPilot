<template>
	<n-spin :show="loading" class="flex grow flex-col" content-class="flex grow flex-col">
		<n-tabs type="line" animated :tabs-padding="24" class="grow" pane-wrapper-class="flex grow flex-col">
			<n-tab-pane name="Summary" tab="Summary" display-directive="show:lazy" class="flex grow flex-col">
				<div class="p-7 pt-4">
					<div class="flex flex-col gap-4">
						<div v-if="report?.severity_assessment" class="flex items-center gap-2">
							<Badge type="splitted" bright :color="severityColor">
								<template #label>Severity</template>
								<template #value>{{ report.severity_assessment }}</template>
							</Badge>
						</div>
						<div v-if="report?.summary">
							<h4 class="mb-2 text-sm font-semibold opacity-70">Summary</h4>
							<p class="whitespace-pre-wrap">{{ report.summary }}</p>
						</div>
						<div v-if="report?.recommended_actions">
							<h4 class="mb-2 text-sm font-semibold opacity-70">Recommended Actions</h4>
							<p class="whitespace-pre-wrap">{{ report.recommended_actions }}</p>
						</div>
						<div v-if="!report?.summary && !report?.recommended_actions">
							<n-empty description="No summary available" />
						</div>
					</div>
				</div>
			</n-tab-pane>
			<n-tab-pane name="Report" tab="Full Report" display-directive="show:lazy">
				<div class="p-7 pt-4">
					<Markdown v-if="report?.report_markdown" :source="report.report_markdown" />
					<n-empty v-else description="No report content available" />
				</div>
			</n-tab-pane>
			<n-tab-pane name="IOCs" tab="IOCs" display-directive="show:lazy">
				<div class="p-7 pt-4">
					<AlertReportIocsList :alert-id="alert.alert_id" />
				</div>
			</n-tab-pane>
			<n-tab-pane name="Jobs" tab="Jobs" display-directive="show:lazy">
				<div class="p-7 pt-4">
					<AlertReportJobsList :alert-id="alert.alert_id" />
				</div>
			</n-tab-pane>
		</n-tabs>
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertWithReport } from "@/types/aiAnalyst.d"
import { NEmpty, NSpin, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, ref, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import Markdown from "@/components/common/Markdown.vue"

const props = defineProps<{
	alert: AlertWithReport
}>()

const { alert } = toRefs(props)

const AlertReportIocsList = defineAsyncComponent(() => import("./AlertReportIocsList.vue"))
const AlertReportJobsList = defineAsyncComponent(() => import("./AlertReportJobsList.vue"))

const loading = ref(false)
const report = computed(() => alert.value.report)

const severityColor = computed(() => {
	const severity = report.value?.severity_assessment
	if (severity === "Critical" || severity === "High") return "danger"
	if (severity === "Medium") return "warning"
	if (severity === "Low" || severity === "Informational") return "success"
	return undefined
})
</script>
