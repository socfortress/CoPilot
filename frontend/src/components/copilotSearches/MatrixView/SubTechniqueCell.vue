<template>
	<div
		class="hover:border-primary/50 hover:bg-primary/6 border-default cursor-pointer rounded-sm border px-1.5 py-1 text-xs"
		:class="cellClass(sub)"
		:title="cellTooltip(sub)"
		@click="emit('open-sub-technique', tactic, tech, sub)"
	>
		<div class="flex items-center justify-between gap-1.5">
			<div class="text-default font-mono text-xs font-semibold">
				{{ sub.id }}
			</div>
			<n-popover
				trigger="hover"
				:delay="350"
				:duration="80"
				:show-arrow="false"
				placement="right"
				:disabled="sub.rule_count === 0"
			>
				<template #trigger>
					<span>
						<n-tag
							v-if="sub.rule_count > 0"
							size="tiny"
							:bordered="false"
							class="flex cursor-help! items-center px-1! font-mono text-[11px]! [&_.n-tag\_\_content]:flex [&_.n-tag\_\_content]:items-center"
						>
							<div class="flex items-center gap-1">
								<Icon name="carbon:information" :size="11" />
								{{ sub.rule_count }}
							</div>
						</n-tag>
					</span>
				</template>

				<RulePreviewList
					:rule-ids="sub.rule_ids"
					:index="rulesIndex"
					@open-rule="ruleId => emit('open-rule', ruleId)"
				/>
			</n-popover>
		</div>
		<div class="text-secondary text-xs leading-tight">
			{{ sub.name }}
		</div>
	</div>
</template>

<script setup lang="ts">
import type { MitreRuleIndexEntry, MitreSubTechnique, MitreTactic, MitreTechnique } from "@/types/copilotSearches.d"
import { NPopover, NTag } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import RulePreviewList from "../RulePreviewList.vue"

defineProps<{
	tactic: MitreTactic
	tech: MitreTechnique
	sub: MitreSubTechnique
	rulesIndex: Record<string, MitreRuleIndexEntry>
}>()

const emit = defineEmits<{
	(e: "open-sub-technique", tactic: MitreTactic, tech: MitreTechnique, sub: MitreSubTechnique): void
	(e: "open-rule", ruleId: string): void
}>()

function cellClass(sub: MitreSubTechnique) {
	const count = sub.rule_count
	if (count === 0) return "cov-empty"
	if (count === 1) return "cov-1"
	if (count <= 3) return "cov-2"
	if (count <= 7) return "cov-3"
	return "cov-4"
}

function cellTooltip(sub: MitreSubTechnique) {
	return sub.rule_count ? `${sub.id} ${sub.name} — ${sub.rule_count} rule(s)` : `${sub.id} ${sub.name} — no rules`
}
</script>
