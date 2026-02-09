<template>
    <n-drawer v-model:show="showDrawer" :width="800" placement="right">
        <n-drawer-content v-if="config" closable>
            <template #header>
                <div class="flex items-center gap-3">
                    <n-icon size="24">
                        <Icon :name="GithubIcon" />
                    </n-icon>
                    <span>{{ config.organization }}</span>
                    <n-tag v-if="!config.enabled" type="warning" size="small">Disabled</n-tag>
                </div>
            </template>

            <n-tabs v-model:value="activeTab" type="line" animated>
                <n-tab-pane name="overview" tab="Overview">
                    <div class="space-y-4">
                        <n-descriptions :column="2" label-placement="top" bordered>
                            <n-descriptions-item label="Customer">
                                {{ config.customer_code }}
                            </n-descriptions-item>
                            <n-descriptions-item label="Organization">
                                {{ config.organization }}
                            </n-descriptions-item>
                            <n-descriptions-item label="Token Type">
                                {{ config.token_type === "pat" ? "Personal Access Token" : "GitHub App" }}
                            </n-descriptions-item>
                            <n-descriptions-item label="Enabled">
                                <n-tag :type="config.enabled ? 'success' : 'warning'" size="small">
                                    {{ config.enabled ? "Yes" : "No" }}
                                </n-tag>
                            </n-descriptions-item>
                            <n-descriptions-item label="Last Audit">
                                {{ config.last_audit_at ? formatDate(config.last_audit_at) : "Never" }}
                            </n-descriptions-item>
                            <n-descriptions-item label="Last Score">
                                <template v-if="config.last_audit_score !== null">
                                    {{ config.last_audit_score?.toFixed(1) }}%
                                    <GitHubAuditGradeBadge :grade="config.last_audit_grade || 'F'" />
                                </template>
                                <template v-else>N/A</template>
                            </n-descriptions-item>
                            <n-descriptions-item label="Scheduled Audits">
                                <n-tag :type="config.auto_audit_enabled ? 'success' : 'default'" size="small">
                                    {{ config.auto_audit_enabled ? "Enabled" : "Disabled" }}
                                </n-tag>
                                <span v-if="config.auto_audit_enabled" class="ml-2 text-sm">
                                    {{ config.audit_schedule_cron }}
                                </span>
                            </n-descriptions-item>
                            <n-descriptions-item label="Audit Scope">
                                <n-space>
                                    <n-tag v-if="config.include_repos" size="small">Repos</n-tag>
                                    <n-tag v-if="config.include_workflows" size="small">Workflows</n-tag>
                                    <n-tag v-if="config.include_members" size="small">Members</n-tag>
                                </n-space>
                            </n-descriptions-item>
                        </n-descriptions>

                        <div class="flex gap-3">
                            <n-button type="primary" :loading="running" @click="runAudit">
                                <template #icon>
                                    <n-icon><Icon :name="PlayIcon" /></n-icon>
                                </template>
                                Run Audit Now
                            </n-button>
                            <n-button @click="handleEdit">
                                <template #icon>
                                    <n-icon><Icon :name="EditIcon" /></n-icon>
                                </template>
                                Edit Configuration
                            </n-button>
                            <n-popconfirm @positive-click="deleteConfig">
                                <template #trigger>
                                    <n-button type="error" ghost>
                                        <template #icon>
                                            <n-icon><Icon :name="DeleteIcon" /></n-icon>
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
                        <div v-if="reports.length === 0 && !loadingReports" class="text-center py-8">
                            <n-empty description="No reports yet">
                                <template #extra>
                                    <n-button type="primary" @click="runAudit">Run your first audit</n-button>
                                </template>
                            </n-empty>
                        </div>

                        <div v-else class="space-y-3">
                            <GitHubAuditReportCard
                                v-for="report in reports"
                                :key="report.id"
                                :report="report"
                                @click="openReportDetail"
                            />

                            <n-pagination
                                v-if="totalReports > pageSize"
                                v-model:page="currentPage"
                                :page-size="pageSize"
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
                        <div v-if="exclusions.length === 0 && !loadingExclusions" class="text-center py-8">
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
                                    <td>{{ exclusion.expires_at ? formatDate(exclusion.expires_at) : "Never" }}</td>
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

            <GitHubAuditReportDetail
                v-if="showReportDetail"
                v-model:show="showReportDetail"
                :report="selectedReport"
            />
        </n-drawer-content>
    </n-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue"
import {
    NButton,
    NDescriptions,
    NDescriptionsItem,
    NDrawer,
    NDrawerContent,
    NEmpty,
    NIcon,
    NPagination,
    NPopconfirm,
    NSpace,
    NSpin,
    NTable,
    NTabPane,
    NTabs,
    NTag,
    useMessage
} from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import GitHubAuditGradeBadge from "./GitHubAuditGradeBadge.vue"
import GitHubAuditReportCard from "./GitHubAuditReportCard.vue"
import GitHubAuditReportDetail from "./GitHubAuditReportDetail.vue"
import GitHubAuditExclusionForm from "./GitHubAuditExclusionForm.vue"
import Api from "@/api"
import type { GitHubAuditCheckExclusion, GitHubAuditConfig, GitHubAuditReport, GitHubAuditReportSummary } from "@/types/githubAudit.d"
import { formatDate } from "@/utils"

const GithubIcon = "mdi:github"
const PlayIcon = "ion:play"
const EditIcon = "ion:create-outline"
const DeleteIcon = "ion:trash-outline"
const AddIcon = "ion:add"

const props = defineProps<{
    show: boolean
    config: GitHubAuditConfig | null
}>()

const emit = defineEmits<{
    (e: "update:show", value: boolean): void
    (e: "updated"): void
    (e: "edit", config: GitHubAuditConfig): void
}>()

const message = useMessage()
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

const showDrawer = computed({
    get: () => props.show,
    set: (value) => emit("update:show", value)
})

watch(
    () => props.show,
    (show) => {
        if (show && props.config) {
            activeTab.value = "overview"
            loadReports()
            loadExclusions()
        }
    }
)

async function loadReports() {
    if (!props.config || loadingReports.value) return

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
        message.error("Failed to load reports")
    } finally {
        loadingReports.value = false
    }
}

async function loadExclusions() {
    if (!props.config || loadingExclusions.value) return

    loadingExclusions.value = true
    try {
        const response = await Api.githubAudit.getExclusions(props.config.id)
        exclusions.value = response.data.exclusions || []
    } catch (error: any) {
        message.error("Failed to load exclusions")
    } finally {
        loadingExclusions.value = false
    }
}

async function runAudit() {
    if (!props.config) return

    running.value = true
    try {
        await Api.githubAudit.runAuditFromConfig(props.config.id)
        message.success("Audit completed successfully")
        loadReports()
        emit("updated")
    } catch (error: any) {
        message.error(error.response?.data?.detail || "Failed to run audit")
    } finally {
        running.value = false
    }
}

async function deleteConfig() {
    if (!props.config) return

    try {
        await Api.githubAudit.deleteConfig(props.config.id)
        message.success("Configuration deleted")
        showDrawer.value = false
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
    } catch (error: any) {
        message.error("Failed to delete exclusion")
    }
}

function handleEdit() {
    if (props.config) {
        showDrawer.value = false
        emit("edit", props.config)
    }
}

async function openReportDetail(report: GitHubAuditReportSummary) {
    try {
        const response = await Api.githubAudit.getReport(report.id)
        if (response.data.report) {
            selectedReport.value = response.data.report
            showReportDetail.value = true
        }
    } catch (error: any) {
        message.error("Failed to load report details")
    }
}
</script>

<style scoped>
.space-y-4 > * + * {
    margin-top: 1rem;
}

.space-y-3 > * + * {
    margin-top: 0.75rem;
}
</style>
