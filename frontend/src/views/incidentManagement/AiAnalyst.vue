<template>
	<div class="page flex flex-col">
		<n-tabs v-model:value="activeTab" type="line" animated>
			<n-tab-pane name="overview" display-directive="show:lazy">
				<template #tab>
					<div class="flex items-center gap-1.5">
						<Icon name="carbon:machine-learning-model" :size="14" class="text-primary" />
						<span>Overview</span>
					</div>
				</template>
				<TalonOverview />
			</n-tab-pane>
			<n-tab-pane name="reports" tab="Reports" display-directive="show:lazy">
				<AlertsReportsList />
			</n-tab-pane>
			<n-tab-pane name="talon" tab="Talon Chat" display-directive="show:lazy" class="p-0!">
				<div class="h-[calc(100vh-200px)]">
					<TalonChat />
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
import TalonOverview from "@/components/aiAnalyst/TalonOverview.vue"
import Icon from "@/components/common/Icon.vue"

const activeTab = ref("overview")
</script>
