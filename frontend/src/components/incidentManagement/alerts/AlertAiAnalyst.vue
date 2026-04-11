<template>
	<n-spin :show="loading" class="min-h-[200px]">
		<div v-if="report" class="flex flex-col gap-4">
			<div class="flex flex-wrap items-center gap-3">
				<n-tag v-if="report.severity_assessment" :type="severityType" size="small" round>
					{{ report.severity_assessment }}
				</n-tag>
				<span class="text-tertiary text-xs">
					{{ formatDate(report.created_at, dFormats.datetime) }}
				</span>
			</div>

			<div v-if="report.summary" class="bg-secondary rounded-lg p-4">
				<div class="text-secondary mb-1 text-xs font-semibold uppercase">Summary</div>
				<p class="text-default text-sm leading-relaxed">{{ report.summary }}</p>
			</div>

			<n-tabs type="line" animated :tabs-padding="0">
				<n-tab-pane name="report" tab="Full Report" display-directive="show:lazy">
					<div class="**:text-default pt-2 **:text-sm [&_*:last-child]:mb-0!">
						<Markdown :source="report.report_markdown || 'No report content'" breaks />
					</div>
				</n-tab-pane>
				<n-tab-pane name="actions" tab="Recommended Actions" display-directive="show:lazy">
					<div class="**:text-default pt-2 **:text-sm [&_*:last-child]:mb-0!">
						<Markdown :source="report.recommended_actions || 'No recommended actions'" breaks />
					</div>
				</n-tab-pane>
			</n-tabs>
		</div>

		<div v-else-if="!loading" class="text-secondary flex flex-col items-center justify-center py-12 text-center">
			<Icon name="carbon:bot" :size="40" class="mb-3 opacity-50" />
			<p class="text-sm">No AI Analyst report available for this alert</p>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { TalonJobData } from "@/types/talon.d"
import { NSpin, NTabPane, NTabs, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	alertId: number
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const loading = ref(false)
const job = ref<TalonJobData | null>(null)

const report = computed(() => job.value?.reports?.[0] || null)

const severityType = computed(() => {
	const s = report.value?.severity_assessment?.toLowerCase()
	if (s === "critical" || s === "high") return "error"
	if (s === "medium") return "warning"
	return "info"
})

function fetchJob() {
	loading.value = true

	Api.talon
		.getJob(props.alertId)
		.then(res => {
			if (res.data.success && res.data.data) {
				job.value = res.data.data
			}
		})
		.catch(() => {
			// No job found — not an error, just no report
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	fetchJob()
})
</script>
