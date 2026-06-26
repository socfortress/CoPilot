<template>
	<div
		class="hover:border-primary/50 hover:bg-primary/6 border-default cursor-pointer rounded-sm border px-1.5 py-1 text-xs"
		:class="coverageClass(sub.rule_count)"
		:title="subTechniqueCellTooltip(sub)"
		@click="emit('open-sub-technique', tactic, tech, sub)"
	>
		<div class="flex items-center justify-between gap-1.5">
			<div class="text-default font-mono text-xs font-semibold">{{ sub.id }}</div>
			<MatrixRuleCountPopover
				:rule-ids="sub.rule_ids"
				:rule-count="sub.rule_count"
				:index="rulesIndex"
				@open-rule="ruleId => emit('open-rule', ruleId)"
			/>
		</div>
		<div class="text-secondary text-xs leading-tight">{{ sub.name }}</div>
	</div>
</template>

<script setup lang="ts">
import type { MitreRuleIndexEntry, MitreSubTechnique, MitreTactic, MitreTechnique } from "@/types/copilot-searches"
import { coverageClass, subTechniqueCellTooltip } from "./matrix-coverage"
import MatrixRuleCountPopover from "./MatrixRuleCountPopover.vue"

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
</script>
