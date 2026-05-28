<template>
	<CardEntity clickable hoverable :loading @click="$emit('click', report)">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div class="min-w-0">
				<div class="mb-1 flex items-center gap-2">
					<span class="text-default truncate font-mono text-sm font-medium">
						{{ report.report_name }}
					</span>
					<span class="shrink-0 font-mono text-[10px] tracking-wider uppercase" :class="statusTextClass">
						{{ report.status }}
					</span>
				</div>
				<p class="text-secondary font-mono text-xs tabular-nums">
					{{ formatDate(report.audit_started_at, dFormats.datetime) }}
					<template v-if="report.audit_duration_seconds != null">
						<span class="text-tertiary mx-1.5">·</span>
						{{ report.audit_duration_seconds.toFixed(1) }}s
					</template>
				</p>
			</div>

			<div class="flex shrink-0 items-end gap-4 text-right">
				<div>
					<p class="text-secondary mb-0.5 text-[10px] tracking-wider uppercase">Score</p>
					<p class="font-mono text-2xl leading-none font-bold tabular-nums" :class="scoreClass">
						{{ report.score.toFixed(0) }}%
					</p>
				</div>
				<div>
					<p class="text-secondary mb-0.5 text-[10px] tracking-wider uppercase">Grade</p>
					<GitHubAuditGradeLabel :grade="report.grade" class="text-2xl" />
				</div>
			</div>
		</div>

		<template #footer>
			<dl class="flex flex-wrap items-baseline gap-x-4 gap-y-1">
				<Badge v-if="report.critical_findings" color="danger" type="splitted" size="small">
					<template #label>Critical</template>
					<template #value>{{ report.critical_findings }}</template>
				</Badge>
				<Badge v-if="report.high_findings" color="warning" type="splitted" size="small">
					<template #label>High</template>
					<template #value>{{ report.high_findings }}</template>
				</Badge>
				<Badge type="splitted" size="small">
					<template #label>Passed</template>
					<template #value>{{ report.passed_checks }}/{{ report.total_checks }}</template>
				</Badge>
			</dl>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { GitHubAuditReportSummary } from "@/types/githubAudit.d"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import GitHubAuditGradeLabel from "./GitHubAuditGradeLabel.vue"

const props = defineProps<{
	report: GitHubAuditReportSummary
	loading?: boolean
}>()

defineEmits<{
	(e: "click", report: GitHubAuditReportSummary): void
}>()

const dFormats = useSettingsStore().dateFormat

const statusTextClass = computed(() => {
	switch (props.report.status) {
		case "completed":
			return "text-success"
		case "running":
			return "text-info"
		case "failed":
			return "text-error"
		default:
			return "text-tertiary"
	}
})

const scoreClass = computed(() => {
	if (props.report.score >= 80) return "text-success"
	if (props.report.score >= 60) return "text-warning"
	return "text-error"
})
</script>
