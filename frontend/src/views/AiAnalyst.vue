<template>
	<div class="page flex flex-col pb-0!">
		<n-tabs v-model:value="activeTab" type="segment" animated tab-class="px-5!" class="[&_.n-tabs-nav]:mx-auto">
			<n-tab-pane name="overview" tab="Overview" display-directive="show:lazy">
				<TalonOverview />
			</n-tab-pane>
			<n-tab-pane name="talon" tab="Talon Chat" display-directive="show:lazy">
				<TalonChat class="h-fixed" />
			</n-tab-pane>
			<n-tab-pane name="reports" tab="Reports" display-directive="show:lazy">
				<AlertsReportsList />
			</n-tab-pane>
			<n-tab-pane name="feedback" tab="Feedback" display-directive="show:lazy">
				<FeedbackDashboard />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { NTabPane, NTabs } from "naive-ui"
import { ref } from "vue"
import AlertsReportsList from "@/components/aiAnalyst/AlertsReportsList.vue"
import FeedbackDashboard from "@/components/aiAnalyst/FeedbackDashboard.vue"
import TalonOverview from "@/components/aiAnalyst/TalonOverview.vue"
import TalonChat from "@/components/talonChat/TalonChatContainer.vue"

const activeTab = ref("overview")
</script>

<style lang="scss">
.h-fixed {
	height: calc(100svh - var(--toolbar-height) - var(--view-padding) - 70px);
}
</style>
