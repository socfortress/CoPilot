<template>
    <div class="flex flex-col gap-4">
        <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold">Snapshots</h2>
            <div class="flex items-center gap-2">
                <n-select
                    v-model:value="selectedRepository"
                    :options="repositoryOptions"
                    placeholder="Select Repository"
                    style="width: 200px"
                    @update:value="fetchSnapshots"
                />
                <n-button type="primary" @click="showCreateModal = true" :disabled="!selectedRepository">
                    <template #icon>
                        <n-icon><AddIcon /></n-icon>
                    </template>
                    Create Snapshot
                </n-button>
            </div>
        </div>

        <n-spin :show="loading">
            <n-card>
                <n-data-table
                    :columns="columns"
                    :data="snapshots"
                    :bordered="false"
                    :single-line="false"
                    size="small"
                    :row-key="(row: SnapshotInfo) => row.snapshot"
                />
            </n-card>
        </n-spin>

        <n-empty v-if="!loading && !selectedRepository" description="Select a repository to view snapshots" />
        <n-empty v-else-if="!loading && snapshots.length === 0" description="No snapshots found in this repository" />

        <!-- Create Snapshot Modal -->
        <n-modal v-model:show="showCreateModal" preset="dialog" title="Create Snapshot">
            <CreateSnapshotForm
                :repository="selectedRepository"
                @success="onSnapshotCreated"
                @cancel="showCreateModal = false"
            />
        </n-modal>

        <!-- Restore Snapshot Modal -->
        <n-modal v-model:show="showRestoreModal" preset="dialog" title="Restore Snapshot">
            <RestoreSnapshotForm
                :repository="selectedRepository"
                :snapshot="selectedSnapshot"
                @success="onSnapshotRestored"
                @cancel="showRestoreModal = false"
            />
        </n-modal>
    </div>
</template>

<script setup lang="ts">
import { NButton, NCard, NDataTable, NEmpty, NIcon, NModal, NSelect, NSpin, NTag, useMessage } from "naive-ui"
import { AddOutline as AddIcon, RefreshOutline as RefreshIcon } from "@vicons/ionicons5"
import { computed, h, onMounted, ref } from "vue"
import type { DataTableColumns, SelectOption } from "naive-ui"
import type { SnapshotInfo, SnapshotRepository } from "@/types/snapshots.d"
import Api from "@/api"
import CreateSnapshotForm from "./CreateSnapshotForm.vue"
import RestoreSnapshotForm from "./RestoreSnapshotForm.vue"

const message = useMessage()
const loading = ref(false)
const repositories = ref<SnapshotRepository[]>([])
const selectedRepository = ref<string | null>(null)
const snapshots = ref<SnapshotInfo[]>([])
const showCreateModal = ref(false)
const showRestoreModal = ref(false)
const selectedSnapshot = ref<SnapshotInfo | null>(null)

const repositoryOptions = computed<SelectOption[]>(() =>
    repositories.value.map(repo => ({
        label: repo.name,
        value: repo.name
    }))
)

const columns: DataTableColumns<SnapshotInfo> = [
    {
        title: "Snapshot",
        key: "snapshot",
        sorter: "default"
    },
    {
        title: "State",
        key: "state",
        render(row) {
            const typeMap: Record<string, "success" | "warning" | "error" | "info"> = {
                SUCCESS: "success",
                IN_PROGRESS: "warning",
                PARTIAL: "warning",
                FAILED: "error"
            }
            return h(NTag, { type: typeMap[row.state] || "info", size: "small" }, () => row.state)
        }
    },
    {
        title: "Indices",
        key: "indices",
        render(row) {
            return h("span", {}, `${row.indices.length} indices`)
        }
    },
    {
        title: "Start Time",
        key: "start_time",
        render(row) {
            return row.start_time ? new Date(row.start_time).toLocaleString() : "-"
        }
    },
    {
        title: "End Time",
        key: "end_time",
        render(row) {
            return row.end_time ? new Date(row.end_time).toLocaleString() : "-"
        }
    },
    {
        title: "Duration",
        key: "duration_in_millis",
        render(row) {
            if (!row.duration_in_millis) return "-"
            const seconds = Math.floor(row.duration_in_millis / 1000)
            if (seconds < 60) return `${seconds}s`
            const minutes = Math.floor(seconds / 60)
            return `${minutes}m ${seconds % 60}s`
        }
    },
    {
        title: "Actions",
        key: "actions",
        render(row) {
            return h(
                NButton,
                {
                    size: "small",
                    type: "primary",
                    onClick: () => openRestoreModal(row)
                },
                () => "Restore"
            )
        }
    }
]

function openRestoreModal(snapshot: SnapshotInfo) {
    selectedSnapshot.value = snapshot
    showRestoreModal.value = true
}

async function fetchRepositories() {
    try {
        const response = await Api.snapshots.getRepositories()
        if (response.data.success) {
            repositories.value = response.data.repositories
        }
    } catch (error: any) {
        message.error(error.message || "Failed to fetch repositories")
    }
}

async function fetchSnapshots() {
    if (!selectedRepository.value) return

    loading.value = true
    try {
        const response = await Api.snapshots.listSnapshots(selectedRepository.value)
        if (response.data.success) {
            snapshots.value = response.data.snapshots
        } else {
            message.error(response.data.message)
        }
    } catch (error: any) {
        message.error(error.message || "Failed to fetch snapshots")
    } finally {
        loading.value = false
    }
}

function onSnapshotCreated() {
    showCreateModal.value = false
    fetchSnapshots()
    message.success("Snapshot creation initiated")
}

function onSnapshotRestored() {
    showRestoreModal.value = false
    message.success("Snapshot restoration initiated")
}

onMounted(() => {
    fetchRepositories()
})
</script>
