<template>
	<n-popover
		trigger="hover"
		:delay="350"
		:duration="80"
		:show-arrow="false"
		placement="right"
		:disabled="sub.rule_count === 0"
	>
		<template #trigger>
			<div
				class="bg-default border-default hover:border-primary/60 hover:bg-primary/8 cursor-pointer rounded-sm border px-1.5 py-1 text-xs"
				:class="cellClass(sub)"
				:title="cellTooltip(sub)"
				@click="emit('open-sub-technique', tactic, tech, sub)"
			>
				<div class="flex items-center justify-between gap-1.5">
					<div class="text-default font-mono text-xs font-semibold">
						{{ sub.id }}
					</div>
					<n-tag
						v-if="sub.rule_count > 0"
						size="tiny"
						:bordered="false"
						class="px-1! font-mono text-[11px]!"
					>
						{{ sub.rule_count }}
					</n-tag>
				</div>
				<div class="text-secondary text-xs leading-tight">
					{{ sub.name }}
				</div>
			</div>
		</template>

		<RulePreviewList
			:rule-ids="sub.rule_ids"
			:index="rulesIndex"
			@open-rule="ruleId => emit('open-rule', ruleId)"
		/>
	</n-popover>
</template>

<script setup lang="ts">
import type {
	MitreRuleIndexEntry,
	MitreSubTechnique,
	MitreTactic,
	MitreTechnique
} from "@/types/copilotSearches.d"
import { NPopover, NTag } from "naive-ui"
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
