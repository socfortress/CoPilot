<template>
	<div class="page-wrapper flex flex-col gap-6 p-6">
		<div class="flex items-center justify-between">
			<h1 class="text-2xl font-bold">Snapshot & Restore</h1>
		</div>

		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="repositories" tab="Repositories">
				<SnapshotRepositories />
			</n-tab-pane>
			<n-tab-pane name="snapshots" tab="Snapshots">
				<SnapshotList />
			</n-tab-pane>
			<n-tab-pane name="schedules" tab="Scheduled Snapshots">
				<SnapshotSchedules />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
// TODO: refactor
import { NTabPane, NTabs } from "naive-ui"
import { ref } from "vue"
import SnapshotList from "@/components/snapshots/SnapshotList.vue"
import SnapshotRepositories from "@/components/snapshots/SnapshotRepositories.vue"
import SnapshotSchedules from "@/components/snapshots/SnapshotSchedules.vue"

const activeTab = ref("repositories")
</script>

<style scoped>
.page-wrapper {
	min-height: 100%;
}
</style>
