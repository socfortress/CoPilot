<template>
	<div class="page flex flex-col">
		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="reports" tab="Reports">
				<AlertsReportsList />
			</n-tab-pane>
			<n-tab-pane name="talon" tab="Talon Chat" display-directive="show:lazy" class="!p-0">
				<div class="h-[calc(100vh-200px)]">
					<TalonChat ref="talonChatRef" />
				</div>
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import { NTabPane, NTabs } from "naive-ui"
import { ref } from "vue"
import AlertsReportsList from "@/components/aiAnalyst/AlertsReportsList.vue"
import TalonChat from "@/components/aiAnalyst/TalonChat.vue"

const activeTab = ref("reports")
</script>
