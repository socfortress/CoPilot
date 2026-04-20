<template>
	<div class="page flex flex-col">
		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="overview" tab="Overview" display-directive="show:lazy">
				<TalonOverview />
			</n-tab-pane>
			<n-tab-pane name="reports" tab="Reports" display-directive="show:lazy">
				<AlertsReportsList />
			</n-tab-pane>
			<n-tab-pane name="talon" tab="Talon Chat" display-directive="show:lazy">
				<TalonChat />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { NTabPane, NTabs } from "naive-ui"
import { ref } from "vue"
import AlertsReportsList from "@/components/aiAnalyst/AlertsReportsList.vue"
import TalonChat from "@/components/aiAnalyst/TalonChat.vue"
import TalonOverview from "@/components/aiAnalyst/TalonOverview.vue"

const activeTab = ref("overview")
</script>
