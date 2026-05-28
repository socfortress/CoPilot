<template>
	<div
		class="border-border hover:border-primary/30 group flex cursor-pointer flex-col gap-3 rounded-md border p-4 transition-colors"
		@click="$emit('click', report)"
	>
		<div class="flex items-start justify-between gap-4">
			<div class="min-w-0 flex-1">
				<div class="mb-1 flex items-center gap-2">
					<span class="text-default truncate font-mono text-sm font-medium">
						{{ report.report_name }}
					</span>
					<span
						class="shrink-0 font-mono text-[10px] tracking-wider uppercase"
						:class="statusTextClass"
					>
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

			<div class="shrink-0 text-right">
				<p class="text-secondary mb-0.5 text-[10px] tracking-wider uppercase">Score</p>
				<p class="font-mono text-2xl leading-none font-bold tabular-nums" :class="scoreClass">
					{{ report.score.toFixed(0) }}%
				</p>
				<p class="mt-1 font-mono text-sm leading-none font-semibold" :class="gradeTextClass">
					{{ report.grade }}
				</p>
			</div>
		</div>

		<dl class="border-border flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t pt-3">
			<div v-if="report.critical_findings" class="flex items-baseline gap-1.5">
				<dt class="text-secondary text-[10px] tracking-wider uppercase">Critical</dt>
				<dd class="text-error font-mono text-xs tabular-nums">{{ report.critical_findings }}</dd>
			</div>
			<div v-if="report.high_findings" class="flex items-baseline gap-1.5">
				<dt class="text-secondary text-[10px] tracking-wider uppercase">High</dt>
				<dd class="text-warning font-mono text-xs tabular-nums">{{ report.high_findings }}</dd>
			</div>
			<div class="flex items-baseline gap-1.5">
				<dt class="text-secondary text-[10px] tracking-wider uppercase">Passed</dt>
				<dd class="text-default font-mono text-xs tabular-nums">
					{{ report.passed_checks }}/{{ report.total_checks }}
				</dd>
			</div>
		</dl>
	</div>
</template>

<script setup lang="ts">
import type { GitHubAuditReportSummary } from "@/types/githubAudit.d"
import { computed } from "vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	report: GitHubAuditReportSummary
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

const gradeTextClass = computed(() => {
	const grade = props.report.grade
	if (grade === "A" || grade === "A+") return "text-success"
	if (grade.startsWith("B")) return "text-info"
	if (grade.startsWith("C")) return "text-warning"
	if (grade === "D" || grade === "D+" || grade === "F") return "text-error"
	return "text-tertiary"
})
</script>
