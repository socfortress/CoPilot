<template>
	<div class="page flex flex-col gap-4 pb-0!">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeAiAnalystReport())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="alert" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ alert.alert_name }}</span>
				<span class="text-secondary font-mono text-sm">#{{ alert.alert_id }}</span>
				<span class="text-secondary text-sm">{{ alert.source }}</span>
			</div>
		</div>

		<AlertReportDetails v-if="reportId != null" :report-id class="grow" full-width @loaded="alert = $event" />
		<n-empty v-else description="Invalid report ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AlertWithReport } from "@/types/ai-analyst"
import { NButton, NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import AlertReportDetails from "@/components/aiAnalyst/AlertReportDetails.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation, useRouteIdParam } from "@/composables/useNavigation"

const { goBack, routeAiAnalystReport } = useNavigation()

const BackIcon = "carbon:arrow-left"
const alert = ref<AlertWithReport | null>(null)

const reportId = useRouteIdParam("id")

watch(reportId, () => {
	alert.value = null
})
</script>
