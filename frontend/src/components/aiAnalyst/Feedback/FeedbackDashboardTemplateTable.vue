<template>
	<n-card size="small" title="Per-template performance" embedded>
		<n-empty v-if="!stats.per_template.length" description="No reviews yet" class="min-h-20 justify-center" />
		<n-data-table
			v-else
			:columns="perTemplateColumns"
			:data="stats.per_template"
			size="small"
			:row-key="(r: ReviewStatsTemplate) => r.template_used ?? '__null__'"
		/>
	</n-card>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { AiAnalystReviewStats, ReviewStatsTemplate } from "@/types/aiAnalyst.d"
import { NCard, NDataTable, NEmpty } from "naive-ui"
import { computed, toRefs } from "vue"

const props = defineProps<{
	stats: AiAnalystReviewStats
}>()

const { stats } = toRefs(props)

const perTemplateColumns = computed<DataTableColumns<ReviewStatsTemplate>>(() => [
	{
		title: "Template",
		key: "template_used",
		minWidth: 200,
		render: row => <div class="min-w-40">{row.template_used ?? "(none)"}</div>
	},
	{ title: "Total", key: "total", width: 80, render: row => <div class="min-w-14">{row.total}</div> },
	{
		title: "Up / Down",
		key: "verdict",
		width: 110,
		render: row => (
			<div class="min-w-18">
				{row.thumbs_up}
				{" / "}
				{row.thumbs_down}
			</div>
		)
	},
	{
		title: "C / P / W",
		key: "choice",
		width: 110,
		render: row => (
			<div class="min-w-22">
				{row.correct}
				{" / "}
				{row.partial}
				{" / "}
				{row.wrong}
			</div>
		)
	},
	{
		title: "Instr",
		key: "avg_rating_instructions",
		width: 80,
		render: row => (
			<div class="min-w-14">
				{row.avg_rating_instructions == null ? "—" : row.avg_rating_instructions.toFixed(2)}
			</div>
		)
	},
	{
		title: "Artif",
		key: "avg_rating_artifacts",
		width: 80,
		render: row => (
			<div class="min-w-14">{row.avg_rating_artifacts == null ? "—" : row.avg_rating_artifacts.toFixed(2)}</div>
		)
	},
	{
		title: "Sev",
		key: "avg_rating_severity",
		width: 80,
		render: row => (
			<div class="min-w-14">{row.avg_rating_severity == null ? "—" : row.avg_rating_severity.toFixed(2)}</div>
		)
	}
])
</script>
