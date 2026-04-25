<template>
	<div class="@container w-full">
		<div class="grid grid-cols-1 gap-3 @lg:grid-cols-2 @3xl:grid-cols-4">
			<MetricTile label="Total reviews" :value="stats.total_reviews.toString()" />
			<MetricTile
				label="Thumbs up"
				:value="pctLabel(stats.thumbs_up_pct)"
				:sub="`${stats.thumbs_up} up / ${stats.thumbs_down} down`"
				:color="pctColor(stats.thumbs_up_pct)"
			/>
			<MetricTile
				label="IOC verdict accuracy"
				:value="pctLabel(stats.ioc_accuracy.accuracy_pct)"
				:sub="`${stats.ioc_accuracy.correct}/${stats.ioc_accuracy.total} IOCs correct`"
				:color="pctColor(stats.ioc_accuracy.accuracy_pct)"
			/>
			<MetricTile
				label="Avg rating (overall)"
				:value="avgOverall == null ? '—' : `${avgOverall.toFixed(2)} / 5`"
				:sub="ratingSubtitle"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AiAnalystReviewStats } from "@/types/aiAnalyst.d"
import { computed, toRefs } from "vue"
import MetricTile from "./FeedbackMetricTile.vue"

const props = defineProps<{
	stats: AiAnalystReviewStats
}>()

const { stats } = toRefs(props)

// Composite avg across the three rubric axes — only counts axes with data.
const avgOverall = computed(() => {
	if (!stats.value) return null
	const parts = [
		stats.value.avg_rating_instructions,
		stats.value.avg_rating_artifacts,
		stats.value.avg_rating_severity
	].filter((v): v is number => v !== null)
	if (!parts.length) return null
	return parts.reduce((a, b) => a + b, 0) / parts.length
})

const ratingSubtitle = computed(() => {
	if (!stats.value) return ""
	const i = stats.value.avg_rating_instructions
	const a = stats.value.avg_rating_artifacts
	const s = stats.value.avg_rating_severity
	return `instr ${i ?? "—"} · artif ${a ?? "—"} · sev ${s ?? "—"}`
})

function pctLabel(pct: number | null): string {
	return pct === null || pct === undefined ? "—" : `${pct.toFixed(1)}%`
}

function pctColor(pct: number | null): "success" | "warning" | "danger" | undefined {
	if (pct === null) return undefined
	if (pct >= 75) return "success"
	if (pct >= 50) return "warning"
	return "danger"
}
</script>
