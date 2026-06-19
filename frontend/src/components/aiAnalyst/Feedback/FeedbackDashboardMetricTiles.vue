<template>
	<div class="@container w-full">
		<div class="grid grid-cols-1 gap-3 @lg:grid-cols-2 @3xl:grid-cols-4">
			<CardLink
				v-for="tile of metricTiles"
				:key="tile.title"
				size="small"
				:title="tile.title"
				:value="tile.value"
				:subtitle="tile.subtitle"
				:color="tile.color"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { AiAnalystReviewStats } from "@/types/aiAnalyst"
import { computed, toRefs } from "vue"
import CardLink from "@/components/common/cards/CardLink.vue"

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

interface MetricTileConfig {
	title: string
	value: string | number
	subtitle?: string
	color?: CardLinkColor
}

const metricTiles = computed<MetricTileConfig[]>(() => {
	const s = stats.value
	const avg = avgOverall.value

	return [
		{
			title: "Total reviews",
			value: s.total_reviews,
			subtitle: `correct ${s.template_choice_correct} · partial ${s.template_choice_partial} · wrong ${s.template_choice_wrong}`
		},
		{
			title: "Thumbs up",
			value: pctLabel(s.thumbs_up_pct),
			subtitle: `${s.thumbs_up} up / ${s.thumbs_down} down`,
			color: pctColor(s.thumbs_up_pct)
		},
		{
			title: "IOC verdict accuracy",
			value: pctLabel(s.ioc_accuracy.accuracy_pct),
			subtitle: `${s.ioc_accuracy.correct}/${s.ioc_accuracy.total} IOCs correct`,
			color: pctColor(s.ioc_accuracy.accuracy_pct)
		},
		{
			title: "Avg rating (overall)",
			value: avg == null ? "—" : `${avg.toFixed(2)} / 5`,
			subtitle: ratingSubtitle.value
		}
	]
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
