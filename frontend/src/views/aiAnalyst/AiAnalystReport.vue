<template>
	<div class="page flex flex-col pb-0!">
		<AlertReportDetails v-if="reportId != null" :report-id class="grow" full-width />
		<n-empty v-else description="Invalid report ID" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import { NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"
import AlertReportDetails from "@/components/aiAnalyst/AlertReportDetails.vue"

const route = useRoute()

const reportId = computed(() => {
	const id = Number(route.params.id)
	return Number.isFinite(id) ? id : null
})
</script>
