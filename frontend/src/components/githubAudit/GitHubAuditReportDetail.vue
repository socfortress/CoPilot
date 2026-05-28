<template>
	<div class="flex flex-col gap-6">
		<!-- Summary Section -->
		<n-card title="Summary" size="small">
			<n-grid :cols="4" :x-gap="16" :y-gap="16">
				<n-gi>
					<n-statistic label="Score">
						<template #default>
							<span :class="scoreClass">{{ report.score.toFixed(1) }}%</span>
						</template>
						<template #suffix>
							<GitHubAuditGradeBadge :grade="report.grade" />
						</template>
					</n-statistic>
				</n-gi>
				<n-gi>
					<n-statistic label="Repos Audited" :value="report.total_repos_audited" />
				</n-gi>
				<n-gi>
					<n-statistic label="Checks Passed">
						<template #default>{{ report.passed_checks }} / {{ report.total_checks }}</template>
					</n-statistic>
				</n-gi>
				<n-gi>
					<n-statistic label="Duration">
						<template #default>{{ report.audit_duration_seconds?.toFixed(1) || "N/A" }}s</template>
					</n-statistic>
				</n-gi>
			</n-grid>
		</n-card>

		<!-- Findings Summary -->
		<n-card title="Findings by Severity" size="small">
			<n-grid :cols="4" :x-gap="16">
				<n-gi>
					<div class="finding-stat critical">
						<div class="number">{{ report.critical_findings }}</div>
						<div class="label">Critical</div>
					</div>
				</n-gi>
				<n-gi>
					<div class="finding-stat high">
						<div class="number">{{ report.high_findings }}</div>
						<div class="label">High</div>
					</div>
				</n-gi>
				<n-gi>
					<div class="finding-stat medium">
						<div class="number">{{ report.medium_findings }}</div>
						<div class="label">Medium</div>
					</div>
				</n-gi>
				<n-gi>
					<div class="finding-stat low">
						<div class="number">{{ report.low_findings }}</div>
						<div class="label">Low</div>
					</div>
				</n-gi>
			</n-grid>
		</n-card>

		<!-- Top Findings -->
		<n-card v-if="report.top_findings && report.top_findings.length > 0" title="Top Findings" size="small">
			<n-table :bordered="false" :single-line="false" size="small">
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
		</n-card>

		<!-- Organization Results -->
		<n-card v-if="report.full_report?.organization_results" title="Organization Settings" size="small">
			<n-table :bordered="false" :single-line="false" size="small">
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

					<n-table :bordered="false" :single-line="false" size="small">
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
// TODO-FE: refactor
import type { GitHubAuditReport } from "@/types/githubAudit.d"
import {
	NAlert,
	NButton,
	NCard,
	NCollapse,
	NCollapseItem,
	NGi,
	NGrid,
	NPopconfirm,
	NSpace,
	NStatistic,
	NTable,
	NTag,
	useMessage
} from "naive-ui"
import { computed } from "vue"
import Api from "@/api"
import { AuditStatus, SeverityLevel } from "@/types/githubAudit.d"
import GitHubAuditGradeBadge from "./GitHubAuditGradeBadge.vue"

const props = defineProps<{
	report: GitHubAuditReport
}>()

const emit = defineEmits<{
	(e: "close"): void
	(e: "deleted"): void
}>()

const message = useMessage()

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

<style scoped>
.finding-stat {
	text-align: center;
	padding: 16px;
	border-radius: 8px;
}

.finding-stat .number {
	font-size: 2rem;
	font-weight: bold;
}

.finding-stat .label {
	font-size: 0.875rem;
	color: var(--text-color-3);
}

.finding-stat.critical {
	background: rgba(208, 48, 80, 0.1);
}

.finding-stat.critical .number {
	color: #d03050;
}

.finding-stat.high {
	background: rgba(240, 160, 32, 0.1);
}

.finding-stat.high .number {
	color: #f0a020;
}

.finding-stat.medium {
	background: rgba(32, 128, 240, 0.1);
}

.finding-stat.medium .number {
	color: #2080f0;
}

.finding-stat.low {
	background: rgba(24, 160, 88, 0.1);
}

.finding-stat.low .number {
	color: #18a058;
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
