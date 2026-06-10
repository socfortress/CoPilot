<template>
	<div class="page">
		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="repositories" tab="Repositories" display-directive="show">
				<SnapshotRepositories @loaded="snapshotRepositories = $event" />
			</n-tab-pane>
			<n-tab-pane name="snapshots" tab="Snapshots" display-directive="show:lazy">
				<SnapshotList :repositories="snapshotRepositories" />
			</n-tab-pane>
			<n-tab-pane name="schedules" tab="Scheduled Snapshots" display-directive="show:lazy">
				<SnapshotSchedules />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import type { SnapshotRepository } from "@/types/snapshots.d"
import { NTabPane, NTabs } from "naive-ui"
import { ref } from "vue"
import SnapshotList from "@/components/snapshots/SnapshotList.vue"
import SnapshotRepositories from "@/components/snapshots/SnapshotRepositories.vue"
import SnapshotSchedules from "@/components/snapshots/SnapshotSchedules.vue"

const activeTab = ref("repositories")
const snapshotRepositories = ref<SnapshotRepository[]>([])
</script>
