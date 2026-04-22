<template>
	<div class="flex flex-col gap-3">
		<div class="flex flex-wrap items-center gap-2">
			<Badge v-if="report.severity_assessment" type="splitted" bright :color="severityColor">
				<template #label>Severity</template>
				<template #value>{{ report.severity_assessment }}</template>
			</Badge>
			<Badge type="splitted">
				<template #label>Report</template>
				<template #value>#{{ report.id }}</template>
			</Badge>
			<Badge type="splitted">
				<template #label>Created</template>
				<template #value>{{ formatDate(report.created_at, "MMM D, YYYY HH:mm") }}</template>
			</Badge>
		</div>

		<CardKV v-if="report.summary">
			<template #key>Summary</template>
			<template #value>{{ report.summary }}</template>
		</CardKV>

		<CardKV v-if="report.recommended_actions">
			<template #key>Recommended actions</template>
			<template #value>{{ report.recommended_actions }}</template>
		</CardKV>

		<n-collapse>
			<n-collapse-item name="markdown">
				<template #header>
					<span class="font-medium">Full report</span>
				</template>
				<div v-if="report.report_markdown" class="pt-2">
					<Markdown :source="report.report_markdown" breaks />
				</div>
				<n-empty v-else description="No report content" class="min-h-20 justify-center" />
			</n-collapse-item>
		</n-collapse>
	</div>
</template>

<script setup lang="ts">
import type { AiAnalystReport } from "@/types/aiAnalyst.d"
import { NCollapse, NCollapseItem, NEmpty } from "naive-ui"
import { computed, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Markdown from "@/components/common/Markdown.vue"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	report: AiAnalystReport
}>()

const { report } = toRefs(props)

const severityColor = computed(() => {
	const severity = report.value.severity_assessment
	if (severity === "Critical" || severity === "High") return "danger"
	if (severity === "Medium") return "warning"
	if (severity === "Low" || severity === "Informational") return "success"
	return undefined
})
</script>
