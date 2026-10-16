<template>
	<div class="page flex flex-col pb-0!">
		<n-tabs v-model:value="activeTab" type="segment" animated tab-class="px-5!" class="[&_.n-tabs-nav]:mx-auto">
			<n-tab-pane name="overview" tab="Overview" display-directive="show:lazy">
				<TalonOverview />
			</n-tab-pane>
			<n-tab-pane name="talon" tab="Talon Chat" display-directive="show:lazy">
				<!-- The v2 chat (threads, a customer per thread) only with the "Talon v2" setting on; else v1, unchanged. -->
				<template v-if="talonV2Settled">
					<TalonV2Chat v-if="talonV2Available" class="h-fixed" />
					<TalonChat v-else class="h-fixed" />
				</template>
				<div v-else class="h-fixed flex items-center justify-center">
					<n-spin size="small" />
				</div>
			</n-tab-pane>
			<n-tab-pane name="reports" tab="Reports" display-directive="show:lazy">
				<AlertsReportsList />
			</n-tab-pane>
			<n-tab-pane name="feedback" tab="Feedback" display-directive="show:lazy">
				<FeedbackDashboard class="pt-8" />
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { NSpin, NTabPane, NTabs } from "naive-ui"
import { defineAsyncComponent, ref } from "vue"
import AlertsReportsList from "@/components/aiAnalyst/AlertsReportsList.vue"
import FeedbackDashboard from "@/components/aiAnalyst/Feedback/FeedbackDashboard.vue"
import TalonOverview from "@/components/aiAnalyst/TalonOverview.vue"
import TalonChat from "@/components/talonChat/TalonChatContainer.vue"
import { useTalonV2Availability } from "@/composables/useTalonV2Availability"

// Loaded only when the setting is on: with it off, the page is the v1 chat as before.
const TalonV2Chat = defineAsyncComponent(() => import("@/components/talonChat/v2/TalonV2Chat.vue"))

const activeTab = ref("overview")
const { available: talonV2Available, settled: talonV2Settled } = useTalonV2Availability()
</script>

<style lang="scss">
.h-fixed {
	height: calc(100svh - var(--toolbar-height) - var(--view-padding) - 70px);
}
</style>
