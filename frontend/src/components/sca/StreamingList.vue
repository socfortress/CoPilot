<template>
    <div class="sca-streaming-list">
        <!-- Progress Header -->
        <n-card v-if="isStreaming || streamComplete" class="mb-4">
            <div class="flex flex-col gap-4">
                <!-- Progress Bar -->
                <div class="flex items-center gap-4">
                    <n-progress
                        type="line"
                        :percentage="progress.percent_complete"
                        :status="streamError ? 'error' : streamComplete ? 'success' : 'default'"
                        :show-indicator="true"
                        class="flex-grow"
                    />
                    <n-button
                        v-if="!isStreaming && !streamComplete"
                        type="primary"
                        @click="startStream"
                        :loading="isConnecting"
                    >
                        <template #icon>
                            <Icon :name="RefreshIcon" />
                        </template>
                        Load SCA Data
                    </n-button>
                    <n-button
                        v-if="isStreaming"
                        type="error"
                        @click="stopStream"
                    >
                        <template #icon>
                            <Icon :name="StopIcon" />
                        </template>
                        Stop
                    </n-button>
                    <n-button
                        v-if="streamComplete"
                        @click="startStream"
                    >
                        <template #icon>
                            <Icon :name="RefreshIcon" />
                        </template>
                        Refresh
                    </n-button>
                </div>

                <!-- Status Text -->
                <div class="flex items-center justify-between text-sm">
                    <span class="text-secondary">
                        {{ statusMessage }}
                    </span>
                    <div class="flex gap-4">
                        <span>
                            Agents:
                            <code class="text-success">{{ progress.successful }}</code>
                            /
                            <code>{{ progress.total }}</code>
                            <code v-if="progress.failed > 0" class="text-error ml-1">
                                ({{ progress.failed }} failed)
                            </code>
                        </span>
                        <span>
                            Results: <code>{{ results.length }}</code>
                        </span>
                    </div>
                </div>
            </div>
        </n-card>

        <!-- Statistics Summary (shown when complete) -->
        <n-card v-if="streamComplete && stats" class="mb-4">
            <div class="flex flex-wrap justify-between gap-4">
                <n-statistic label="Total Agents" :value="stats.total_agents" />
                <n-statistic label="Total Policies" :value="stats.total_policies" />
                <n-statistic label="Average Score">
                    <template #default>
                        <span :class="getScoreClass(stats.average_score)">
                            {{ stats.average_score }}%
                        </span>
                    </template>
                </n-statistic>
                <n-statistic label="Checks" :value="stats.total_checks" />
                <n-statistic label="Passed" :value="stats.total_passes" class="text-success" />
                <n-statistic label="Failed" :value="stats.total_fails" class="text-error" />
            </div>
        </n-card>

        <!-- Filters -->
        <n-card class="mb-4">
            <div class="flex flex-wrap gap-4">
                <n-select
                    v-model:value="filters.customer_code"
                    placeholder="All Customers"
                    :options="customerOptions"
                    clearable
                    class="w-48"
                    @update:value="onFilterChange"
                />
                <n-input
                    v-model:value="filters.agent_name"
                    placeholder="Agent Name"
                    clearable
                    class="w-48"
                    @update:value="onFilterChange"
                />
                <n-input
                    v-model:value="filters.policy_name"
                    placeholder="Policy Name"
                    clearable
                    class="w-48"
                    @update:value="onFilterChange"
                />
                <n-input-number
                    v-model:value="filters.min_score"
                    placeholder="Min Score"
                    :min="0"
                    :max="100"
                    clearable
                    class="w-32"
                    @update:value="onFilterChange"
                />
                <n-input-number
                    v-model:value="filters.max_score"
                    placeholder="Max Score"
                    :min="0"
                    :max="100"
                    clearable
                    class="w-32"
                    @update:value="onFilterChange"
                />
            </div>
        </n-card>

        <!-- Results List -->
        <div class="results-container">
            <n-spin :show="isConnecting">
                <!-- Empty State -->
                <n-empty
                    v-if="!isStreaming && !streamComplete && filteredResults.length === 0"
                    description="Click 'Load SCA Data' to start collecting results"
                    class="py-12"
                >
                    <template #extra>
                        <n-button type="primary" @click="startStream">
                            Load SCA Data
                        </n-button>
                    </template>
                </n-empty>

                <!-- Results Table -->
                <n-data-table
                    v-else
                    :columns="columns"
                    :data="paginatedResults"
                    :pagination="pagination"
                    :loading="isConnecting"
                    :row-key="(row: AgentScaOverviewItem) => `${row.agent_id}-${row.policy_id}`"
                    striped
                />
            </n-spin>
        </div>

        <!-- Error Display -->
        <n-alert v-if="streamError" type="error" class="mt-4" closable @close="streamError = null">
            <template #header>Stream Error</template>
            {{ streamError }}
        </n-alert>
    </div>
</template>

<script setup lang="ts">
import type {
    AgentScaOverviewItem,
    ScaOverviewQuery,
    ScaStreamComplete,
    ScaStreamProgress
} from "@/types/sca.d"
import type { DataTableColumns } from "naive-ui"
import {
    NAlert,
    NButton,
    NCard,
    NDataTable,
    NEmpty,
    NInput,
    NInputNumber,
    NProgress,
    NSelect,
    NSpin,
    NStatistic,
    useMessage
} from "naive-ui"
import { computed, h, onBeforeUnmount, reactive, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"

const RefreshIcon = "carbon:refresh"
const StopIcon = "carbon:stop"

const message = useMessage()

// State
const isConnecting = ref(false)
const isStreaming = ref(false)
const streamComplete = ref(false)
const streamError = ref<string | null>(null)
const results = ref<AgentScaOverviewItem[]>([])
const stats = ref<ScaStreamComplete | null>(null)
const abortController = ref<AbortController | null>(null)

const progress = reactive<ScaStreamProgress>({
    processed: 0,
    total: 0,
    successful: 0,
    failed: 0,
    results_so_far: 0,
    percent_complete: 0
})

const filters = reactive<ScaOverviewQuery>({
    customer_code: undefined,
    agent_name: undefined,
    policy_name: undefined,
    min_score: undefined,
    max_score: undefined
})

// Customer options (you'd populate this from your API)
const customerOptions = ref<{ label: string; value: string }[]>([])

// Computed
const statusMessage = computed(() => {
    if (isConnecting.value) return "Connecting..."
    if (isStreaming.value) return `Collecting SCA data... ${progress.processed}/${progress.total} agents`
    if (streamComplete.value) return stats.value?.message || "Collection complete"
    return "Ready to load SCA data"
})

const filteredResults = computed(() => {
    return results.value.filter(item => {
        if (filters.policy_name && !item.policy_name.toLowerCase().includes(filters.policy_name.toLowerCase())) {
            return false
        }
        return true
    })
})

const pagination = reactive({
    page: 1,
    pageSize: 25,
    showSizePicker: true,
    pageSizes: [10, 25, 50, 100],
    itemCount: computed(() => filteredResults.value.length),
    onChange: (page: number) => {
        pagination.page = page
    },
    onUpdatePageSize: (pageSize: number) => {
        pagination.pageSize = pageSize
        pagination.page = 1
    }
})

const paginatedResults = computed(() => {
    const start = (pagination.page - 1) * pagination.pageSize
    const end = start + pagination.pageSize
    return filteredResults.value.slice(start, end)
})

// Table columns
const columns: DataTableColumns<AgentScaOverviewItem> = [
    {
        title: "Agent",
        key: "agent_name",
        width: 150,
        ellipsis: { tooltip: true }
    },
    {
        title: "Customer",
        key: "customer_code",
        width: 120
    },
    {
        title: "Policy",
        key: "policy_name",
        ellipsis: { tooltip: true }
    },
    {
        title: "Checks",
        key: "total_checks",
        width: 80,
        align: "center"
    },
    {
        title: "Passed",
        key: "pass_count",
        width: 80,
        align: "center",
        render: (row) => h("span", { class: "text-success" }, row.pass_count)
    },
    {
        title: "Failed",
        key: "fail_count",
        width: 80,
        align: "center",
        render: (row) => h("span", { class: "text-error" }, row.fail_count)
    },
    {
        title: "Score",
        key: "score",
        width: 100,
        align: "center",
        sorter: (a, b) => a.score - b.score,
        render: (row) => h(
            Badge,
            {
                type: "splitted",
                color: row.score >= 80 ? "success" : row.score >= 60 ? "warning" : "danger"
            },
            { label: () => `${row.score}%` }
        )
    },
    {
        title: "Last Scan",
        key: "end_scan",
        width: 160,
        render: (row) => new Date(row.end_scan).toLocaleString()
    }
]

// Methods
function getScoreClass(score: number): string {
    if (score >= 80) return "text-success"
    if (score >= 60) return "text-warning"
    return "text-error"
}

async function startStream() {
    // Reset state
    results.value = []
    stats.value = null
    streamError.value = null
    streamComplete.value = false
    isConnecting.value = true

    Object.assign(progress, {
        processed: 0,
        total: 0,
        successful: 0,
        failed: 0,
        results_so_far: 0,
        percent_complete: 0
    })

    // Abort existing connection if any
    if (abortController.value) {
        abortController.value.abort()
    }

    // Create new abort controller
    abortController.value = new AbortController()

    // Build query params
    const query: ScaOverviewQuery = {}
    if (filters.customer_code) query.customer_code = filters.customer_code
    if (filters.agent_name) query.agent_name = filters.agent_name
    if (filters.policy_name) query.policy_name = filters.policy_name
    if (filters.min_score !== undefined) query.min_score = filters.min_score
    if (filters.max_score !== undefined) query.max_score = filters.max_score

    try {
        await Api.sca.streamScaOverview(
            query,
            {
                onStart(data) {
                    isConnecting.value = false
                    isStreaming.value = true
                    progress.total = data.total_agents
                    message.info(data.message)
                },
                onAgentResult(data) {
                    // Add all policies from this agent
                    for (const policy of data.policies) {
                        results.value.push({
                            agent_id: data.agent_id,
                            agent_name: data.agent_name,
                            customer_code: data.customer_code,
                            ...policy
                        })
                    }
                },
                onAgentEmpty(data) {
                    // Agent had no SCA data - could log or display if needed
                    console.debug(`Agent ${data.agent_name} has no SCA data`)
                },
                onProgress(data) {
                    Object.assign(progress, data)
                },
                onComplete(data) {
                    stats.value = data
                    isStreaming.value = false
                    streamComplete.value = true

                    // Sort results by score (lowest first)
                    results.value.sort((a, b) => a.score - b.score)

                    message.success(data.message)
                },
                onError(error) {
                    const errorMessage = error?.message || error?.error || "Unknown error"
                    console.warn("Stream error:", error)

                    // Only set error if we haven't completed successfully
                    if (!streamComplete.value) {
                        streamError.value = errorMessage
                    }
                    progress.failed++
                }
            },
            abortController.value
        )
    } catch (error: any) {
        // Don't show error for intentional abort
        if (error.name !== "AbortError") {
            streamError.value = error.message || "Connection error"
            console.error("Stream connection error:", error)
        }
    } finally {
        isStreaming.value = false
        isConnecting.value = false
    }
}

function stopStream() {
    if (abortController.value) {
        abortController.value.abort()
        abortController.value = null
    }
    isStreaming.value = false
    isConnecting.value = false
    message.warning("Stream stopped by user")
}

function onFilterChange() {
    // Debounce and restart stream with new filters if already streaming
    // Or just filter client-side if data is already loaded
    pagination.page = 1
}

// Cleanup on unmount
onBeforeUnmount(() => {
    if (abortController.value) {
        abortController.value.abort()
    }
})
</script>

<style scoped>
.results-container {
    min-height: 400px;
}
</style>
