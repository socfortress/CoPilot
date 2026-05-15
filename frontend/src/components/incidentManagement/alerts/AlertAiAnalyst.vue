<template>
	<n-spin :show="loading" class="min-h-[200px]">
		<div v-if="reports.length" class="flex flex-col gap-4">
			<div v-if="reports.length > 1" class="flex flex-col gap-2">
				<n-select v-model:value="selectedIndex" :options="reportOptions" size="small" />
				<div class="flex items-center justify-between gap-2">
					<div>
						<div v-if="report" class="flex flex-wrap items-center gap-2">
							<n-tag v-if="report.severity_assessment" :type="severityType" size="small" round>
								{{ report.severity_assessment }}
							</n-tag>
							<n-tag size="small" round>
								{{ formatDate(report.created_at, dFormats.datetime) }}
							</n-tag>
						</div>
					</div>

					<span class="text-secondary shrink-0 text-xs">
						{{ reports.length }} report{{ reports.length > 1 ? "s" : "" }}
					</span>
				</div>
			</div>

			<div v-if="report" class="flex flex-col gap-4">
				<CardEntity v-if="report.summary" embedded size="small">
					<div class="text-secondary mb-1 text-sm font-semibold uppercase">Summary</div>
					<div class="text-sm">
						{{ report.summary }}
					</div>
				</CardEntity>

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
		</div>

		<div v-else-if="!loading" class="text-secondary flex flex-col items-center justify-center py-12 text-center">
			<Icon name="carbon:bot" :size="40" class="mb-3 opacity-50" />
			<p class="text-sm">No AI Analyst report available for this alert</p>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { TalonJobData } from "@/types/talon.d"
import { NSelect, NSpin, NTabPane, NTabs, NTag } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	alertId: number
}>()

const dFormats = useSettingsStore().dateFormat

const loading = ref(false)
const job = ref<TalonJobData | null>(null)
const selectedIndex = ref(0)

const reports = computed(() => {
	const r = job.value?.reports || []
	// Most recent first
	return [...r].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
})

const reportOptions = computed(() =>
	reports.value.map((r, i) => {
		const chunks = []

		chunks.push(dayjs(r.created_at).fromNow())

		if (r.severity_assessment) {
			chunks.push(r.severity_assessment)
		}

		if (r.job_id) {
			chunks.push(`#${r.job_id}`)
		}

		return {
			label: chunks.join(" — "),
			value: i
		}
	})
)

const report = computed(() => reports.value[selectedIndex.value] || null)

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
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	fetchJob()
})
</script>
