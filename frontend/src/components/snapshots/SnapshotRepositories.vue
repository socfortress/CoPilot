<template>
    <div class="flex flex-col gap-4">
        <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold">Snapshot Repositories</h2>
            <n-button type="primary" @click="fetchRepositories" :loading="loading">
                <template #icon>
                    <n-icon><RefreshIcon /></n-icon>
                </template>
                Refresh
            </n-button>
        </div>

        <n-spin :show="loading">
            <n-card>
                <n-data-table
                    :columns="columns"
                    :data="repositories"
                    :bordered="false"
                    :single-line="false"
                    size="small"
                />
            </n-card>
        </n-spin>

        <n-empty v-if="!loading && repositories.length === 0" description="No snapshot repositories found" />
    </div>
</template>

<script setup lang="ts">
import { NButton, NCard, NDataTable, NEmpty, NIcon, NSpin, useMessage } from "naive-ui"
import { RefreshOutline as RefreshIcon } from "@vicons/ionicons5"
import { h, onMounted, ref } from "vue"
import type { DataTableColumns } from "naive-ui"
import type { SnapshotRepository } from "@/types/snapshots.d"
import Api from "@/api"

const message = useMessage()
const loading = ref(false)
const repositories = ref<SnapshotRepository[]>([])

const columns: DataTableColumns<SnapshotRepository> = [
    {
        title: "Name",
        key: "name",
        sorter: "default"
    },
    {
        title: "Type",
        key: "type",
        sorter: "default"
    },
    {
        title: "Settings",
        key: "settings",
        render(row) {
            return h(
                "code",
                { class: "text-xs" },
                JSON.stringify(row.settings, null, 2)
            )
        }
    }
]

async function fetchRepositories() {
    loading.value = true
    try {
        const response = await Api.snapshots.getRepositories()
        if (response.data.success) {
            repositories.value = response.data.repositories
        } else {
            message.error(response.data.message)
        }
    } catch (error: any) {
        message.error(error.message || "Failed to fetch repositories")
    } finally {
        loading.value = false
    }
}

onMounted(() => {
    fetchRepositories()
})
</script>