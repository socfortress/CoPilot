<template>
	<n-tabs v-model:value="activeTab" type="segment" animated>
		<n-tab-pane name="overview" tab="Overview">
			<div class="flex flex-col gap-6 py-4">
				<GitHubAuditConfigSummary :config />

				<dl class="border-border bg-secondary flex flex-col gap-2 rounded-md border p-4">
					<div class="flex items-baseline justify-between gap-3">
						<dt class="text-secondary shrink-0 text-[10px] tracking-wider uppercase">Enabled</dt>
						<dd class="font-mono text-xs" :class="config.enabled ? 'text-success' : 'text-warning'">
							{{ config.enabled ? "Active" : "Disabled" }}
						</dd>
					</div>
					<div class="flex items-baseline justify-between gap-3">
						<dt class="text-secondary shrink-0 text-[10px] tracking-wider uppercase">Scheduled</dt>
						<dd
							class="font-mono text-xs"
							:class="config.auto_audit_enabled ? 'text-success' : 'text-tertiary'"
						>
							{{ config.auto_audit_enabled ? "Enabled" : "Disabled" }}
						</dd>
					</div>
					<div v-if="config.auto_audit_enabled" class="flex items-baseline justify-between gap-3">
						<dt class="text-secondary shrink-0 text-[10px] tracking-wider uppercase">Cron</dt>
						<dd class="text-default min-w-0 truncate text-right font-mono text-xs tabular-nums">
							{{ config.audit_schedule_cron || "—" }}
						</dd>
					</div>
				</dl>

				<div class="flex flex-col gap-2">
					<p class="text-secondary text-[10px] font-medium tracking-widest uppercase">Audit scope</p>
					<GitHubAuditScopeFlags :config size="large" class="bg-secondary" />
				</div>

				<div class="border-border flex flex-wrap justify-between gap-3 border-t pt-6">
					<div class="flex flex-wrap gap-3">
						<n-button @click="handleEdit">
							<template #icon>
								<Icon :name="EditIcon" />
							</template>
							Edit Configuration
						</n-button>
						<n-button quaternary :loading="running" @click="runAudit">
							<template #icon>
								<Icon :name="PlayIcon" />
							</template>
							Run Audit Now
						</n-button>
					</div>
					<n-popconfirm @positive-click="deleteConfig">
						<template #trigger>
							<n-button type="error" ghost>
								<template #icon>
									<Icon :name="DeleteIcon" />
								</template>
								Delete
							</n-button>
						</template>
						Are you sure you want to delete this configuration?
					</n-popconfirm>
				</div>
			</div>
		</n-tab-pane>

		<n-tab-pane name="reports" tab="Reports">
			<n-spin :show="loadingReports">
				<div v-if="reports.length === 0 && !loadingReports" class="py-8 text-center">
					<n-empty description="No reports yet">
						<template #extra>
							<n-button type="primary" @click="runAudit">Run your first audit</n-button>
						</template>
					</n-empty>
				</div>

				<div v-else class="flex flex-col gap-3">
					<GitHubAuditReportCard
						v-for="report in reports"
						:key="report.id"
						:report
						@click="openReportDetail"
					/>

					<n-pagination
						v-if="totalReports > pageSize"
						v-model:page="currentPage"
						:page-size
						:item-count="totalReports"
						@update:page="loadReports"
					/>
				</div>
			</n-spin>
		</n-tab-pane>

		<n-tab-pane name="exclusions" tab="Exclusions">
			<div class="mb-4">
				<n-button type="primary" size="small" @click="showExclusionForm = true">
					<template #icon>
						<n-icon><Icon :name="AddIcon" /></n-icon>
					</template>
					Add Exclusion
				</n-button>
			</div>

			<n-spin :show="loadingExclusions">
				<div v-if="exclusions.length === 0 && !loadingExclusions" class="py-8 text-center">
					<n-empty description="No exclusions configured" />
				</div>

				<n-table v-else :bordered="false" :single-line="false">
					<thead>
						<tr>
							<th>Check</th>
							<th>Resource</th>
							<th>Reason</th>
							<th>Expires</th>
							<th>Actions</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="exclusion in exclusions" :key="exclusion.id">
							<td>{{ exclusion.check_id }}</td>
							<td>{{ exclusion.resource_name || "All" }}</td>
							<td>{{ exclusion.reason }}</td>
							<td>
								{{
									exclusion.expires_at ? formatDate(exclusion.expires_at, dFormats.datetime) : "Never"
								}}
							</td>
							<td>
								<n-button text type="error" @click="deleteExclusion(exclusion.id)">
									<n-icon><Icon :name="DeleteIcon" /></n-icon>
								</n-button>
							</td>
						</tr>
					</tbody>
				</n-table>
			</n-spin>
		</n-tab-pane>
	</n-tabs>

	<GitHubAuditExclusionForm
		v-if="showExclusionForm"
		v-model:show="showExclusionForm"
		:config-id="config.id"
		@saved="loadExclusions"
	/>

	<GitHubAuditReportDetail v-if="showReportDetail" v-model:show="showReportDetail" :report="selectedReport" />
</template>

<script setup lang="ts">
import type {
	GitHubAuditCheckExclusion,
	GitHubAuditConfig,
	GitHubAuditReport,
	GitHubAuditReportSummary
} from "@/types/githubAudit.d"
import { NButton, NEmpty, NIcon, NPagination, NPopconfirm, NSpin, NTable, NTabPane, NTabs, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import GitHubAuditConfigSummary from "./GitHubAuditConfigSummary.vue"
import GitHubAuditExclusionForm from "./GitHubAuditExclusionForm.vue"
import GitHubAuditReportCard from "./GitHubAuditReportCard.vue"
import GitHubAuditReportDetail from "./GitHubAuditReportDetail.vue"
import GitHubAuditScopeFlags from "./GitHubAuditScopeFlags.vue"

const props = defineProps<{
	config: GitHubAuditConfig
}>()

const emit = defineEmits<{
	(e: "updated"): void
	(e: "edit", config: GitHubAuditConfig): void
	(e: "close"): void
}>()

const PlayIcon = "carbon:play"
const EditIcon = "carbon:edit"
const DeleteIcon = "ion:trash-outline"
const AddIcon = "ion:add"

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const activeTab = ref("overview")
const running = ref(false)

// Reports
const loadingReports = ref(false)
const reports = ref<GitHubAuditReportSummary[]>([])
const totalReports = ref(0)
const currentPage = ref(1)
const pageSize = 10
const showReportDetail = ref(false)
const selectedReport = ref<GitHubAuditReport | null>(null)

// Exclusions
const loadingExclusions = ref(false)
const exclusions = ref<GitHubAuditCheckExclusion[]>([])
const showExclusionForm = ref(false)

function resetAndLoad() {
	activeTab.value = "overview"
	reports.value = []
	exclusions.value = []
	currentPage.value = 1
	loadReports()
	loadExclusions()
}

watch(() => props.config.id, resetAndLoad, { immediate: true })

async function loadReports() {
	if (loadingReports.value) {
		return
	}

	loadingReports.value = true
	try {
		const response = await Api.githubAudit.getReports({
			configId: props.config.id,
			limit: pageSize,
			offset: (currentPage.value - 1) * pageSize
		})
		reports.value = response.data.reports || []
		totalReports.value = response.data.total_count || 0
	} catch (error: any) {
		console.error("Failed to load reports:", error)
		message.error("Failed to load reports")
	} finally {
		loadingReports.value = false
	}
}

async function loadExclusions() {
	if (loadingExclusions.value) return

	loadingExclusions.value = true
	try {
		const response = await Api.githubAudit.getExclusions(props.config.id)
		exclusions.value = response.data.exclusions || []
	} catch (error: any) {
		console.error("Failed to load exclusions:", error)
		message.error("Failed to load exclusions")
	} finally {
		loadingExclusions.value = false
	}
}

async function runAudit() {
	running.value = true
	try {
		await Api.githubAudit.runAuditFromConfig(props.config.id)
		message.success("Audit completed successfully")
		// Reload reports after audit completes
		await loadReports()
		emit("updated")
	} catch (error: any) {
		message.error(error.response?.data?.detail || "Failed to run audit")
	} finally {
		running.value = false
	}
}

async function deleteConfig() {
	try {
		await Api.githubAudit.deleteConfig(props.config.id)
		message.success("Configuration deleted")
		emit("close")
		emit("updated")
	} catch (error: any) {
		message.error(error.response?.data?.detail || "Failed to delete configuration")
	}
}

async function deleteExclusion(exclusionId: number) {
	try {
		await Api.githubAudit.deleteExclusion(exclusionId)
		message.success("Exclusion deleted")
		loadExclusions()
	} catch {
		message.error("Failed to delete exclusion")
	}
}

function handleEdit() {
	emit("edit", props.config)
}

async function openReportDetail(report: GitHubAuditReportSummary) {
	try {
		const response = await Api.githubAudit.getReport(report.id)
		if (response.data.report) {
			selectedReport.value = response.data.report
			showReportDetail.value = true
		}
	} catch {
		message.error("Failed to load report details")
	}
}
</script>
