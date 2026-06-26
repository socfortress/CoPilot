<template>
	<div class="@container flex flex-col gap-6">
		<!-- Summary Section -->
		<n-card title="Summary" size="small">
			<div class="grid gap-4 @sm:grid-cols-2 @xl:grid-cols-4">
				<n-statistic label="Score">
					<template #default>
						<span :class="scoreClass">{{ report.score.toFixed(1) }}%</span>
					</template>
					<template #suffix>
						<GitHubAuditGradeBadge :grade="report.grade" class="relative -top-0.5" />
					</template>
				</n-statistic>

				<n-statistic label="Repos Audited" :value="report.total_repos_audited" />

				<n-statistic label="Checks Passed">
					<template #default>{{ report.passed_checks }} / {{ report.total_checks }}</template>
				</n-statistic>

				<n-statistic label="Duration">
					<template #default>{{ report.audit_duration_seconds?.toFixed(1) || "N/A" }}s</template>
				</n-statistic>
			</div>
		</n-card>

		<!-- Findings Summary -->
		<n-card title="Findings by Severity" size="small">
			<div class="border-border divide-border grid grid-cols-4 divide-x rounded-md border">
				<div
					v-for="stat in severityStats"
					:key="stat.key"
					class="flex flex-col items-center gap-1 px-3 py-4"
					:class="stat.bgClass"
				>
					<p class="text-secondary text-3xs tracking-wider uppercase">{{ stat.label }}</p>
					<p class="font-mono text-2xl leading-none font-bold tabular-nums" :class="stat.numberClass">
						{{ report[stat.key] }}
					</p>
				</div>
			</div>
		</n-card>

		<!-- Top Findings -->
		<n-card v-if="report.top_findings && report.top_findings.length > 0" title="Top Findings" size="small">
			<div class="scrollbar-styled overflow-x-auto">
				<n-table :single-line="false" size="small" class="min-w-150">
					<thead>
						<tr>
							<th>Severity</th>
							<th>Check</th>
							<th>Resource</th>
							<th>Description</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(finding, index) in report.top_findings" :key="index">
							<td>
								<n-tag :type="getSeverityType(finding.severity)" size="small">
									{{ finding.severity }}
								</n-tag>
							</td>
							<td>{{ finding.check_name }}</td>
							<td>{{ finding.resource_name || "N/A" }}</td>
							<td>{{ finding.description }}</td>
						</tr>
					</tbody>
				</n-table>
			</div>
		</n-card>

		<!-- Organization Results -->
		<n-card v-if="report.full_report?.organization_results" title="Organization Settings" size="small">
			<div class="scrollbar-styled overflow-x-auto">
				<n-table :single-line="false" size="small" class="min-w-150">
					<thead>
						<tr>
							<th>Status</th>
							<th>Check</th>
							<th>Description</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="check in report.full_report.organization_results.checks" :key="check.check_id">
							<td>
								<n-tag :type="getStatusType(check.status)" size="small">
									{{ check.status }}
								</n-tag>
							</td>
							<td>{{ check.check_name }}</td>
							<td>{{ check.description }}</td>
						</tr>
					</tbody>
				</n-table>
			</div>
		</n-card>

		<!-- Repository Results -->
		<n-card v-if="report.full_report?.repository_results?.length" title="Repository Results" size="small">
			<n-collapse>
				<n-collapse-item
					v-for="repo in report.full_report.repository_results"
					:key="repo.repo_name"
					:title="repo.repo_name"
				>
					<template #header-extra>
						<n-space>
							<n-tag type="success" size="small">{{ repo.passed_count }} passed</n-tag>
							<n-tag v-if="repo.failed_count > 0" type="error" size="small">
								{{ repo.failed_count }} failed
							</n-tag>
						</n-space>
					</template>

					<div class="scrollbar-styled overflow-x-auto">
						<n-table :single-line="false" size="small" class="min-w-150">
							<thead>
								<tr>
									<th>Status</th>
									<th>Check</th>
									<th>Description</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="check in repo.checks" :key="check.check_id">
									<td>
										<n-tag :type="getStatusType(check.status)" size="small">
											{{ check.status }}
										</n-tag>
									</td>
									<td>{{ check.check_name }}</td>
									<td>{{ check.description }}</td>
								</tr>
							</tbody>
						</n-table>
					</div>
				</n-collapse-item>
			</n-collapse>
		</n-card>

		<!-- Error Message -->
		<n-alert v-if="report.error_message" title="Error" type="error">
			{{ report.error_message }}
		</n-alert>

		<div class="border-border flex justify-between gap-3 border-t pt-4">
			<n-popconfirm @positive-click="deleteReport">
				<template #trigger>
					<n-button type="error" ghost>Delete Report</n-button>
				</template>
				Are you sure you want to delete this report?
			</n-popconfirm>
			<n-button @click="emit('close')">Close</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { GitHubAuditReport } from "@/types/github-audit"
import {
	NAlert,
	NButton,
	NCard,
	NCollapse,
	NCollapseItem,
	NPopconfirm,
	NSpace,
	NStatistic,
	NTable,
	NTag,
	useMessage
} from "naive-ui"
import { computed } from "vue"
import Api from "@/api"
import { AuditStatus, SeverityLevel } from "@/types/github-audit"
import GitHubAuditGradeBadge from "./GitHubAuditGradeBadge.vue"

const props = defineProps<{
	report: GitHubAuditReport
}>()

const emit = defineEmits<{
	(e: "close"): void
	(e: "deleted"): void
}>()

const message = useMessage()

const severityStats = [
	{ key: "critical_findings" as const, label: "Critical", numberClass: "text-error", bgClass: "bg-error/5" },
	{ key: "high_findings" as const, label: "High", numberClass: "text-warning", bgClass: "bg-warning/5" },
	{ key: "medium_findings" as const, label: "Medium", numberClass: "text-info", bgClass: "bg-info/5" },
	{ key: "low_findings" as const, label: "Low", numberClass: "text-success", bgClass: "bg-success/5" }
]

const scoreClass = computed(() => {
	const score = props.report.score ?? 0
	if (score >= 80) return "text-success"
	if (score >= 60) return "text-warning"
	return "text-error"
})

function getStatusType(status: AuditStatus | string) {
	switch (status) {
		case AuditStatus.PASS:
		case "pass":
			return "success"
		case AuditStatus.FAIL:
		case "fail":
			return "error"
		case AuditStatus.WARNING:
		case "warning":
			return "warning"
		default:
			return "default"
	}
}

function getSeverityType(severity: SeverityLevel | string) {
	switch (severity) {
		case SeverityLevel.CRITICAL:
		case "critical":
			return "error"
		case SeverityLevel.HIGH:
		case "high":
			return "warning"
		case SeverityLevel.MEDIUM:
		case "medium":
			return "info"
		default:
			return "default"
	}
}

async function deleteReport() {
	try {
		await Api.githubAudit.deleteReport(props.report.id)
		message.success("Report deleted")
		emit("deleted")
		emit("close")
	} catch {
		message.error("Failed to delete report")
	}
}
</script>
