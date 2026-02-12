<template>
	<n-card class="github-audit-report-card" hoverable size="small" @click="$emit('click', report)">
		<div class="flex items-center justify-between">
			<div class="flex-1">
				<div class="mb-1 flex items-center gap-2">
					<span class="font-medium">{{ report.report_name }}</span>
					<n-tag :type="statusType" size="small">{{ report.status }}</n-tag>
				</div>
				<div class="text-secondary text-xs">
					{{ formatDate(report.audit_started_at, dFormats.datetime) }}
					<span v-if="report.audit_duration_seconds">• {{ report.audit_duration_seconds.toFixed(1) }}s</span>
				</div>
			</div>

			<div class="flex items-center gap-4">
				<div class="text-center">
					<div class="text-2xl font-bold" :class="scoreClass">{{ report.score.toFixed(0) }}%</div>
					<GitHubAuditGradeBadge :grade="report.grade" />
				</div>

				<div class="findings-summary text-xs">
					<div v-if="report.critical_findings" class="text-error">
						{{ report.critical_findings }} Critical
					</div>
					<div v-if="report.high_findings" class="text-warning">{{ report.high_findings }} High</div>
					<div class="text-secondary">{{ report.passed_checks }}/{{ report.total_checks }} Passed</div>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
// TODO: refactor
import type { GitHubAuditReportSummary } from "@/types/githubAudit.d"
import { NCard, NTag } from "naive-ui"
import { computed } from "vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import GitHubAuditGradeBadge from "./GitHubAuditGradeBadge.vue"

const props = defineProps<{
	report: GitHubAuditReportSummary
}>()

defineEmits<{
	(e: "click", report: GitHubAuditReportSummary): void
}>()

const dFormats = useSettingsStore().dateFormat

const statusType = computed(() => {
	switch (props.report.status) {
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

const scoreClass = computed(() => {
	if (props.report.score >= 80) return "text-success"
	if (props.report.score >= 60) return "text-warning"
	return "text-error"
})
</script>

<style scoped>
.github-audit-report-card {
	cursor: pointer;
	transition: all 0.2s ease;
}

.github-audit-report-card:hover {
	transform: translateY(-1px);
}

.text-secondary {
	color: var(--text-color-3);
}

.text-success {
	color: var(--success-color);
}

.text-warning {
	color: var(--warning-color);
}

.text-error {
	color: var(--error-color);
}
</style>
