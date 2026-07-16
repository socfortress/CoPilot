<template>
	<div class="page flex flex-col gap-4 pb-0!">
		<DetailPageHeader :title="alert?.alert_name || undefined" :back-route="routeAiAnalystReport()">
			<template v-if="alert" #meta>
				<span class="text-secondary font-mono text-sm">#{{ alert.alert_id }}</span>
				<span class="text-secondary text-sm">{{ alert.source }}</span>
			</template>
		</DetailPageHeader>

		<AlertReportDetails v-if="reportId != null" :report-id class="grow" full-width @loaded="alert = $event" />
		<n-empty v-else description="Invalid report ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AlertWithReport } from "@/types/ai-analyst"
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import AlertReportDetails from "@/components/aiAnalyst/AlertReportDetails.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { routeAiAnalystReport } = useNavigation()

const alert = ref<AlertWithReport | null>(null)

const reportId = useRouteIdParam("id")

watch(reportId, () => {
	alert.value = null
})
</script>
