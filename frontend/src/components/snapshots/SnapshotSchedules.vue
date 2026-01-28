<template>
    <div class="flex flex-col gap-4">
        <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold">Scheduled Snapshots</h2>
            <div class="flex items-center gap-2">
                <n-button @click="fetchSchedules" :loading="loading">
                    <template #icon>
                        <Icon :name="RefreshIcon" :size="16" />
                    </template>
                    Refresh
                </n-button>
                <n-button type="primary" @click="showCreateModal = true">
                    <template #icon>
                        <Icon :name="AddIcon" :size="16" />
                    </template>
                    Create Schedule
                </n-button>
            </div>
        </div>

        <n-spin :show="loading">
            <n-card>
                <n-data-table
                    :columns="columns"
                    :data="schedules"
                    :bordered="false"
                    :single-line="false"
                    size="small"
                    :row-key="(row: SnapshotScheduleResponse) => row.id"
                />
            </n-card>
        </n-spin>

        <n-empty v-if="!loading && schedules.length === 0" description="No snapshot schedules configured" />

        <!-- Create Schedule Modal -->
        <n-modal v-model:show="showCreateModal" preset="dialog" title="Create Snapshot Schedule" style="width: 600px">
            <SnapshotScheduleForm
                @success="onScheduleCreated"
                @cancel="showCreateModal = false"
            />
        </n-modal>

        <!-- Edit Schedule Modal -->
        <n-modal v-model:show="showEditModal" preset="dialog" title="Edit Snapshot Schedule" style="width: 600px">
            <SnapshotScheduleForm
                :schedule="selectedSchedule"
                @success="onScheduleUpdated"
                @cancel="showEditModal = false"
            />
        </n-modal>
    </div>
</template>

<script setup lang="ts">
import {
    NButton,
    NCard,
    NDataTable,
    NEmpty,
    NModal,
    NPopconfirm,
    NSpin,
    NSwitch,
    NTag,
    useMessage
} from "naive-ui"
import { Icon } from "@iconify/vue"
import { h, onMounted, ref } from "vue"
import type { DataTableColumns } from "naive-ui"
import type { SnapshotScheduleResponse } from "@/types/snapshots.d"
import Api from "@/api"
import SnapshotScheduleForm from "./SnapshotScheduleForm.vue"

const AddIcon = "carbon:add"
const RefreshIcon = "carbon:refresh"

const message = useMessage()
const loading = ref(false)
const schedules = ref<SnapshotScheduleResponse[]>([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const selectedSchedule = ref<SnapshotScheduleResponse | null>(null)

const columns: DataTableColumns<SnapshotScheduleResponse> = [
    {
        title: "Name",
        key: "name",
        sorter: "default"
    },
    {
        title: "Index Pattern",
        key: "index_pattern",
        render(row) {
            return h("code", { class: "text-sm" }, row.index_pattern)
        }
    },
    {
        title: "Repository",
        key: "repository"
    },
    {
        title: "Enabled",
        key: "enabled",
        render(row) {
            return h(NSwitch, {
                value: row.enabled,
                onUpdateValue: (value: boolean) => toggleEnabled(row, value)
            })
        }
    },
    {
        title: "Retention",
        key: "retention_days",
        render(row) {
            return row.retention_days ? `${row.retention_days} days` : "Forever"
        }
    },
    {
        title: "Last Execution",
        key: "last_execution_time",
        render(row) {
            if (!row.last_execution_time) return "-"
            return h("div", { class: "flex flex-col" }, [
                h("span", {}, new Date(row.last_execution_time).toLocaleString()),
                h(
                    NTag,
                    {
                        type: row.last_execution_status?.startsWith("SUCCESS") ? "success" :
                              row.last_execution_status?.startsWith("SKIPPED") ? "warning" : "error",
                        size: "small",
                        class: "mt-1"
                    },
                    () => row.last_execution_status?.split(":")[0] || "Unknown"
                )
            ])
        }
    },
    {
        title: "Last Snapshot",
        key: "last_snapshot_name",
        render(row) {
            return row.last_snapshot_name || "-"
        }
    },
    {
        title: "Actions",
        key: "actions",
        width: 150,
        render(row) {
            return h("div", { class: "flex gap-2" }, [
                h(
                    NButton,
                    {
                        size: "small",
                        onClick: () => openEditModal(row)
                    },
                    () => "Edit"
                ),
                h(
                    NPopconfirm,
                    {
                        onPositiveClick: () => deleteSchedule(row)
                    },
                    {
                        trigger: () => h(NButton, { size: "small", type: "error" }, () => "Delete"),
                        default: () => "Are you sure you want to delete this schedule?"
                    }
                )
            ])
        }
    }
]

function openEditModal(schedule: SnapshotScheduleResponse) {
    selectedSchedule.value = schedule
    showEditModal.value = true
}

async function toggleEnabled(schedule: SnapshotScheduleResponse, enabled: boolean) {
    try {
        const response = await Api.snapshots.updateSchedule(schedule.id, { enabled })
        if (response.data.success) {
            message.success(`Schedule ${enabled ? "enabled" : "disabled"}`)
            fetchSchedules()
        } else {
            message.error(response.data.message)
        }
    } catch (error: any) {
        message.error(error.message || "Failed to update schedule")
    }
}

async function deleteSchedule(schedule: SnapshotScheduleResponse) {
    try {
        const response = await Api.snapshots.deleteSchedule(schedule.id)
        if (response.data.success) {
            message.success("Schedule deleted")
            fetchSchedules()
        } else {
            message.error(response.data.message)
        }
    } catch (error: any) {
        message.error(error.message || "Failed to delete schedule")
    }
}

async function fetchSchedules() {
    loading.value = true
    try {
        const response = await Api.snapshots.getSchedules()
        if (response.data.success) {
            schedules.value = response.data.schedules
        } else {
            message.error(response.data.message)
        }
    } catch (error: any) {
        message.error(error.message || "Failed to fetch schedules")
    } finally {
        loading.value = false
    }
}

function onScheduleCreated() {
    showCreateModal.value = false
    fetchSchedules()
    message.success("Schedule created successfully")
}

function onScheduleUpdated() {
    showEditModal.value = false
    fetchSchedules()
    message.success("Schedule updated successfully")
}

onMounted(() => {
    fetchSchedules()
})
</script>
