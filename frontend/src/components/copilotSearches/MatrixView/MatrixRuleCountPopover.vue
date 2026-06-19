<template>
	<n-popover v-bind="MATRIX_RULE_POPOVER" :disabled="ruleCount === 0">
		<template #trigger>
			<span>
				<n-tag v-if="ruleCount > 0" :size="tagSize" :bordered="false" :class="MATRIX_RULE_TAG_CLASS">
					<div class="flex items-center gap-1">
						<Icon name="carbon:information" :size="iconSize" />
						{{ ruleCount }}
					</div>
				</n-tag>
			</span>
		</template>
		<RulePreviewList :rule-ids :index :extra-via-subs @open-rule="ruleId => emit('open-rule', ruleId)" />
	</n-popover>
</template>

<script setup lang="ts">
import type { MitreRuleIndexEntry } from "@/types/copilotSearches"
import { NPopover, NTag } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import RulePreviewList from "../RulePreviewList.vue"
import { MATRIX_RULE_POPOVER, MATRIX_RULE_TAG_CLASS } from "./matrixCoverage"

withDefaults(
	defineProps<{
		ruleIds: string[]
		ruleCount: number
		index: Record<string, MitreRuleIndexEntry>
		extraViaSubs?: number
		tagSize?: "tiny" | "small"
		iconSize?: number
	}>(),
	{ tagSize: "tiny", iconSize: 11 }
)

const emit = defineEmits<{
	(e: "open-rule", ruleId: string): void
}>()
</script>
