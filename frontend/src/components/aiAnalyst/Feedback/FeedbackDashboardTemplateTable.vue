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

<script setup lang="ts">
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
		render: row => row.template_used ?? "(none)"
	},
	{ title: "Total", key: "total", width: 80 },
	{
		title: "Up / Down",
		key: "verdict",
		width: 110,
		render: row => `${row.thumbs_up} / ${row.thumbs_down}`
	},
	{
		title: "C / P / W",
		key: "choice",
		width: 110,
		render: row => `${row.correct} / ${row.partial} / ${row.wrong}`
	},
	{
		title: "Instr",
		key: "avg_rating_instructions",
		width: 80,
		render: row => (row.avg_rating_instructions == null ? "—" : row.avg_rating_instructions.toFixed(2))
	},
	{
		title: "Artif",
		key: "avg_rating_artifacts",
		width: 80,
		render: row => (row.avg_rating_artifacts == null ? "—" : row.avg_rating_artifacts.toFixed(2))
	},
	{
		title: "Sev",
		key: "avg_rating_severity",
		width: 80,
		render: row => (row.avg_rating_severity == null ? "—" : row.avg_rating_severity.toFixed(2))
	}
])
</script>
