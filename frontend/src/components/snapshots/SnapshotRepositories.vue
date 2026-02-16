<template>
	<div class="flex flex-col gap-4">
		<n-alert type="info" :show-icon="true">
			<template #header>Repository Registration Required</template>
			Snapshot repositories must be manually registered in your Wazuh Indexer cluster.
			<n-a
				href="https://docs.opensearch.org/2.19/tuning-your-cluster/availability-and-recovery/snapshots/snapshot-restore/"
				target="_blank"
			>
				View the documentation
			</n-a>
			for instructions on how to register a snapshot repository.
		</n-alert>

		<div class="flex items-center justify-between">
			<h2 class="text-lg font-semibold">Snapshot Repositories</h2>
			<n-button type="primary" :loading="loading" @click="fetchRepositories">
				<template #icon>
					<Icon :name="RefreshIcon" :size="16" />
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
// TODO: refactor
import type { DataTableColumns } from "naive-ui"
import type { SnapshotRepository } from "@/types/snapshots.d"
import { NA, NAlert, NButton, NCard, NDataTable, NEmpty, NSpin, useMessage } from "naive-ui"
import { h, onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const RefreshIcon = "carbon:renew"

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
			return h("code", { class: "text-xs" }, JSON.stringify(row.settings, null, 2))
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
