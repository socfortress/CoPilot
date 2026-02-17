<template>
	<div class="pipe-details flex flex-wrap justify-between gap-1">
		<div class="flex w-full flex-wrap items-center justify-between gap-2">
			<p v-if="pipeline.description">
				{{ pipeline.description }}
			</p>

			<div class="text-secondary text-right font-mono text-sm">
				{{ formatDate(pipeline.modified_at, dFormats.datetimesec) }}
			</div>
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
								<Icon :name="RulesIcon" :size="18" />
							</template>
							Rules
							<span class="text-secondary ml-2 font-mono">{{ stage.rules.length }}</span>
						</n-button>
					</template>

					<RulesSmallList :rules="stage.rules" style="margin: 0 -10px" @click="emit('clickRule', $event)" />
				</n-popover>
			</n-timeline-item>
		</n-timeline>
	</n-scrollbar>
</template>

<script setup lang="ts">
// TODO: refactor
import type { RuleExtended } from "./RulesSmallList.vue"
import type { PipelineFull, PipelineFullStage } from "@/types/graylog/pipelines.d"
import { NButton, NPopover, NScrollbar, NTimeline, NTimelineItem } from "naive-ui"
import { computed, toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import RulesSmallList from "./RulesSmallList.vue"

interface PipelineFullStageExt extends Omit<PipelineFullStage, "rules" | "rule_ids"> {
	rules: RuleExtended[]
}

const props = defineProps<{ pipeline: PipelineFull }>()

const emit = defineEmits<{
	(e: "clickRule", value: string): void
}>()

const { pipeline } = toRefs(props)

const RulesIcon = "ic:outline-swipe-right-alt"

const dFormats = useSettingsStore().dateFormat

function sanitizeStage(stage: PipelineFullStage): PipelineFullStageExt {
	const rules: RuleExtended[] = []

	for (const i in stage.rules) {
		rules.push({
			title: stage.rules[i] ?? "",
			id: stage.rule_ids[i] ?? ""
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
