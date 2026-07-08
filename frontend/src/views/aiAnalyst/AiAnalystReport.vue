<template>
	<div class="page flex flex-col gap-4 pb-0!">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="alert" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span class="truncate text-lg font-semibold">{{ alert.alert_name }}</span>
				<span class="font-mono text-sm text-secondary">#{{ alert.alert_id }}</span>
				<span class="text-sm text-secondary">{{ alert.source }}</span>
			</div>
		</div>

		<AlertReportDetails
			v-if="reportId != null"
			:report-id
			class="grow"
			full-width
			@loaded="alert = $event"
		/>
		<n-empty v-else description="Invalid report ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { AlertWithReport } from "@/types/ai-analyst"
import { NButton, NEmpty } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import AlertReportDetails from "@/components/aiAnalyst/AlertReportDetails.vue"
import Icon from "@/components/common/Icon.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"
const alert = ref<AlertWithReport | null>(null)

const reportId = computed(() => {
	const id = Number(route.params.id)
	return Number.isFinite(id) ? id : null
})

watch(reportId, () => {
	alert.value = null
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	router.push({ name: "AiAnalyst" })
}
</script>
