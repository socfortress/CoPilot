<template>
    <n-modal v-model:show="showModal" preset="card" title="Bulk Delete Agents" class="bulk-delete-modal" :style="{ maxWidth: '600px' }">
        <n-tabs v-model:value="activeTab" type="line">
            <n-tab-pane name="selection" tab="By Selection">
                <div class="tab-content">
                    <n-alert v-if="!selectedAgents.length" type="warning" class="mb-4">
                        No agents selected. Please select agents from the list first.
                    </n-alert>
                    <template v-else>
                        <p class="mb-4">
                            You are about to delete <strong>{{ selectedAgents.length }}</strong> selected agent(s).
                        </p>
                        <n-scrollbar style="max-height: 200px" class="mb-4">
                            <div class="selected-agents-list">
                                <n-tag
                                    v-for="agent in selectedAgents"
                                    :key="agent.agent_id"
                                    closable
                                    class="mr-2 mb-2"
                                    @close="$emit('remove-selection', agent)"
                                >
                                    {{ agent.hostname }} ({{ agent.agent_id }})
                                </n-tag>
                            </div>
                        </n-scrollbar>
                    </template>
                </div>
            </n-tab-pane>

            <n-tab-pane name="filter" tab="By Filter">
                <div class="tab-content">
                    <n-form ref="filterFormRef" :model="filterForm" label-placement="top">
                        <n-alert type="info" class="mb-4">
                            At least one filter must be specified. This will delete all matching agents.
                        </n-alert>

                        <n-form-item label="Customer Code" path="customer_code">
                            <n-select
                                v-model:value="filterForm.customer_code"
                                :options="customerOptions"
                                placeholder="Select customer (optional)"
                                clearable
                                filterable
                            />
                        </n-form-item>

                        <n-form-item label="Agent Status" path="status">
                            <n-select
                                v-model:value="filterForm.status"
                                :options="statusOptions"
                                placeholder="Select status (optional)"
                                clearable
                            />
                        </n-form-item>

                        <n-form-item label="Disconnected Days" path="disconnected_days">
                            <n-input-number
                                v-model:value="filterForm.disconnected_days"
                                :min="1"
                                :max="365"
                                placeholder="Agents disconnected for more than X days"
                                clearable
                                class="w-full"
                            />
                        </n-form-item>
                    </n-form>
                </div>
            </n-tab-pane>
        </n-tabs>

        <!-- Results Section -->
        <template v-if="deleteResults">
            <n-divider />
            <div class="results-section">
                <n-alert :type="deleteResults.success ? 'success' : 'warning'" class="mb-4">
                    {{ deleteResults.message }}
                </n-alert>
                <div class="results-stats mb-4">
                    <n-space>
                        <n-tag type="info">Total: {{ deleteResults.total_requested }}</n-tag>
                        <n-tag type="success">Successful: {{ deleteResults.successful_deletions }}</n-tag>
                        <n-tag v-if="deleteResults.failed_deletions > 0" type="error">
                            Failed: {{ deleteResults.failed_deletions }}
                        </n-tag>
                    </n-space>
                </div>
                <n-collapse v-if="deleteResults.results.length > 0">
                    <n-collapse-item title="Deletion Details" name="details">
                        <n-scrollbar style="max-height: 200px">
                            <div v-for="result in deleteResults.results" :key="result.agent_id" class="result-item">
                                <n-tag :type="result.success ? 'success' : 'error'" size="small">
                                    {{ result.success ? "✓" : "✗" }}
                                </n-tag>
                                <span class="ml-2">{{ result.agent_id }}: {{ result.message }}</span>
                            </div>
                        </n-scrollbar>
                    </n-collapse-item>
                </n-collapse>
            </div>
        </template>

        <template #footer>
            <n-space justify="end">
                <n-button @click="closeModal">Cancel</n-button>
                <n-button
                    type="error"
                    :loading="loading"
                    :disabled="!canDelete"
                    @click="confirmDelete"
                >
                    <template #icon>
                        <n-icon><Icon :name="DeleteIcon" /></n-icon>
                    </template>
                    Delete Agents
                </n-button>
            </n-space>
        </template>
    </n-modal>

    <!-- Confirmation Dialog -->
    <n-modal v-model:show="showConfirmDialog" preset="dialog" type="warning" title="Confirm Bulk Deletion">
        <template #default>
            <p>Are you sure you want to delete these agents?</p>
            <p class="mt-2 text-red-500">This action cannot be undone.</p>
            <template v-if="activeTab === 'filter'">
                <p class="mt-2">
                    <strong>Filters:</strong>
                </p>
                <ul class="list-disc ml-4">
                    <li v-if="filterForm.customer_code">Customer: {{ filterForm.customer_code }}</li>
                    <li v-if="filterForm.status">Status: {{ filterForm.status }}</li>
                    <li v-if="filterForm.disconnected_days">Disconnected for: {{ filterForm.disconnected_days }}+ days</li>
                </ul>
            </template>
            <template v-else>
                <p class="mt-2">{{ selectedAgents.length }} agent(s) will be deleted.</p>
            </template>
        </template>
        <template #action>
            <n-button @click="showConfirmDialog = false">Cancel</n-button>
            <n-button type="error" :loading="loading" @click="executeDelete">
                Confirm Delete
            </n-button>
        </template>
    </n-modal>
</template>

<script setup lang="ts">
import type { Agent, BulkDeleteAgentsResponse, BulkDeleteFilterRequest } from "@/types/agents.d"
import { computed, ref, watch } from "vue"
import {
    NAlert,
    NButton,
    NCollapse,
    NCollapseItem,
    NDivider,
    NForm,
    NFormItem,
    NIcon,
    NInputNumber,
    NModal,
    NScrollbar,
    NSelect,
    NSpace,
    NTab,
    NTabPane,
    NTabs,
    NTag,
    useMessage
} from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
    show: boolean
    selectedAgents: Agent[]
    customers: string[]
}>()

const emit = defineEmits<{
    (e: "update:show", value: boolean): void
    (e: "remove-selection", agent: Agent): void
    (e: "deleted"): void
}>()

const message = useMessage()
const DeleteIcon = "carbon:trash-can"

const showModal = computed({
    get: () => props.show,
    set: (value) => emit("update:show", value)
})

const activeTab = ref<"selection" | "filter">("selection")
const loading = ref(false)
const showConfirmDialog = ref(false)
const deleteResults = ref<BulkDeleteAgentsResponse | null>(null)

const filterForm = ref<BulkDeleteFilterRequest>({
    customer_code: undefined,
    status: undefined,
    disconnected_days: undefined
})

const customerOptions = computed(() => {
    return props.customers.map(code => ({ label: code, value: code }))
})

const statusOptions = [
    { label: "Disconnected", value: "disconnected" },
    { label: "Never Connected", value: "never_connected" },
    { label: "Active", value: "active" }
]

const hasFilters = computed(() => {
    return filterForm.value.customer_code || filterForm.value.status || filterForm.value.disconnected_days
})

const canDelete = computed(() => {
    if (activeTab.value === "selection") {
        return props.selectedAgents.length > 0
    }
    return hasFilters.value
})

function closeModal() {
    showModal.value = false
    deleteResults.value = null
}

function confirmDelete() {
    showConfirmDialog.value = true
}

async function executeDelete() {
    showConfirmDialog.value = false
    loading.value = true
    deleteResults.value = null

    try {
        let response
        if (activeTab.value === "selection") {
            const agentIds = props.selectedAgents.map(a => a.agent_id)
            response = await Api.agents.bulkDeleteAgents(agentIds)
        } else {
            response = await Api.agents.bulkDeleteAgentsByFilter(filterForm.value)
        }

        deleteResults.value = response.data

        if (response.data.success) {
            message.success(response.data.message)
            emit("deleted")
        } else {
            message.warning(response.data.message)
        }
    } catch (err: any) {
        message.error(err.response?.data?.detail || err.response?.data?.message || "Failed to delete agents")
    } finally {
        loading.value = false
    }
}

// Reset form when modal closes
watch(showModal, (newVal) => {
    if (!newVal) {
        filterForm.value = {
            customer_code: undefined,
            status: undefined,
            disconnected_days: undefined
        }
        deleteResults.value = null
    }
})

// Switch to selection tab if agents are selected
watch(() => props.selectedAgents.length, (len) => {
    if (len > 0) {
        activeTab.value = "selection"
    }
})
</script>

<style lang="scss" scoped>
.bulk-delete-modal {
    .tab-content {
        padding-top: 16px;
    }

    .selected-agents-list {
        display: flex;
        flex-wrap: wrap;
    }

    .result-item {
        display: flex;
        align-items: center;
        padding: 4px 0;
        border-bottom: 1px solid var(--border-color);

        &:last-child {
            border-bottom: none;
        }
    }

    .w-full {
        width: 100%;
    }
}
</style>
