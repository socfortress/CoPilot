<template>
	<div class="pipe-details flex flex-wrap justify-between gap-1">
		<div class="description">
			<p v-if="pipeline.description">
				{{ pipeline.description }}
			</p>
		</div>

		<div class="time">
			{{ formatDate(pipeline.modified_at, dFormats.datetimesec) }}
		</div>
	</div>

	<n-scrollbar x-scrollable trigger="none" class="mt-5">
		<n-timeline horizontal size="large" style="width: max-content" class="mb-4">
			<n-timeline-item
				v-for="stage of stages"
				:key="stage.stage"
				:type="stage.match === 'EITHER' ? undefined : 'info'"
				:title="`Stage ${stage.stage}`"
			>
				<p class="mb-1">
					{{ stage.match }}
				</p>
				<n-popover trigger="click" style="max-height: 240px" scrollable placement="bottom">
					<template #trigger>
						<n-button size="tiny">
							<template #icon>
								<Icon :name="RulesIcon" :size="18"></Icon>
							</template>
							Rules
							<span class="font-mono ml-2 text-secondary-color">{{ stage.rules.length }}</span>
						</n-button>
					</template>

					<RulesSmallList :rules="stage.rules" style="margin: 0 -10px" @click="emit('clickRule', $event)" />
				</n-popover>
			</n-timeline-item>
		</n-timeline>
	</n-scrollbar>
</template>

<script setup lang="ts">
import { NTimeline, NTimelineItem, NButton, NScrollbar, NPopover } from "naive-ui"
import { computed, toRefs } from "vue"
import type { PipelineFull, PipelineFullStage } from "@/types/graylog/pipelines.d"
import Icon from "@/components/common/Icon.vue"
import RulesSmallList, { type RuleExtended } from "./RulesSmallList.vue"
import { formatDate } from "@/utils"
import { useSettingsStore } from "@/stores/settings"

interface PipelineFullStageExt extends Omit<PipelineFullStage, "rules" | "rule_ids"> {
	rules: RuleExtended[]
}

const emit = defineEmits<{
	(e: "clickRule", value: string): void
}>()

const props = defineProps<{ pipeline: PipelineFull }>()
const { pipeline } = toRefs(props)

const RulesIcon = "ic:outline-swipe-right-alt"

const dFormats = useSettingsStore().dateFormat

function sanitizeStage(stage: PipelineFullStage): PipelineFullStageExt {
	const rules: RuleExtended[] = []

	for (const i in stage.rules) {
		rules.push({
			title: stage.rules[i],
			id: stage.rule_ids[i]
		})
	}

	const stageExt: PipelineFullStageExt = {
		rules,
		match: stage.match,
		stage: stage.stage
	}

	return stageExt
}

const stages = computed<PipelineFullStageExt[]>(() => {
	const stages: PipelineFullStageExt[] = []

	for (const stage of pipeline.value.stages) {
		stages.push(sanitizeStage(stage))
	}

	return stages
})
</script>

<style lang="scss" scoped>
.time {
	font-family: var(--font-family-mono);
	font-size: 13px;
	text-align: right;
	color: var(--fg-secondary-color);
	line-height: 1.6;
}
</style>
