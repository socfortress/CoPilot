<template>
	<n-card size="small" embedded title="Template choice distribution">
		<div class="flex flex-col gap-2">
			<TemplateChoiceBar
				label="Correct"
				color="success"
				:count="stats.template_choice_correct"
				:total="templateChoiceTotal"
			/>
			<TemplateChoiceBar
				label="Partial"
				color="warning"
				:count="stats.template_choice_partial"
				:total="templateChoiceTotal"
			/>
			<TemplateChoiceBar
				label="Wrong"
				color="error"
				:count="stats.template_choice_wrong"
				:total="templateChoiceTotal"
			/>
			<p v-if="templateChoiceTotal === 0" class="text-sm">No template choice feedback yet.</p>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { AiAnalystReviewStats } from "@/types/aiAnalyst.d"
import { NCard } from "naive-ui"
import { computed, toRefs } from "vue"
import TemplateChoiceBar from "./FeedbackTemplateChoiceBar.vue"

const props = defineProps<{
	stats: AiAnalystReviewStats
}>()

const { stats } = toRefs(props)

const templateChoiceTotal = computed(() =>
	stats.value
		? stats.value.template_choice_correct + stats.value.template_choice_partial + stats.value.template_choice_wrong
		: 0
)
</script>
