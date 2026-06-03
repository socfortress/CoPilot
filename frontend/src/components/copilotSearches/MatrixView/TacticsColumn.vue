<template>
	<div class="flex w-60 shrink-0 flex-col">
		<div
			class="bg-secondary border-default sticky top-0 z-2 flex flex-col gap-1 rounded-t-md border border-b-2 px-2.5 py-2"
			:class="{
				'border-warning/55 border-b-warning/70 bg-warning/6': isTacticUncovered
			}"
		>
			<div class="flex justify-between gap-2">
				<div class="text-default text-sm leading-tight font-medium">{{ tactic.name }}</div>
				<n-tag
					size="tiny"
					:type="isTacticUncovered ? 'warning' : 'default'"
					:title="`${stats.covered} of ${stats.total} techniques covered by CoPilot rules`"
				>
					<span class="font-mono text-[10px]">{{ stats.covered }}</span>
					<span class="text-tertiary mx-1 text-xs">/</span>
					<span class="font-mono text-[10px]">{{ stats.total }}</span>
				</n-tag>
			</div>
			<div class="text-tertiary text-xs">{{ tactic.techniques.length }} shown</div>
		</div>

		<div class="flex flex-col gap-1 pt-1">
			<TechniqueCell
				v-for="tech of tactic.techniques"
				:key="tactic.id + tech.id"
				v-model:expanded="expanded"
				:tactic
				:tech
				:rules-index
				:hovered-technique-id
				:hovered-tactic-id
				@open-technique="(t, technique) => emit('open-technique', t, technique)"
				@open-sub-technique="(t, technique, sub) => emit('open-sub-technique', t, technique, sub)"
				@open-rule="ruleId => emit('open-rule', ruleId)"
				@technique-hover="(tacticId, techId) => emit('technique-hover', tacticId, techId)"
				@technique-leave="emit('technique-leave')"
			/>

			<n-empty v-if="!tactic.techniques.length" description="No techniques" class="py-4" size="small" />
		</div>
	</div>
</template>

<script setup lang="ts">
import type {
	MitreCoverageResponse,
	MitreRuleIndexEntry,
	MitreSubTechnique,
	MitreTactic,
	MitreTechnique
} from "@/types/copilotSearches.d"
import { NEmpty, NTag } from "naive-ui"
import { computed } from "vue"
import TechniqueCell from "./TechniqueCell.vue"

const props = defineProps<{
	tactic: MitreTactic
	coverage: MitreCoverageResponse | null
	rulesIndex: Record<string, MitreRuleIndexEntry>
	hoveredTechniqueId: string | null
	hoveredTacticId: string | null
}>()

const emit = defineEmits<{
	(e: "open-technique", tactic: MitreTactic, tech: MitreTechnique): void
	(e: "open-sub-technique", tactic: MitreTactic, tech: MitreTechnique, sub: MitreSubTechnique): void
	(e: "open-rule", ruleId: string): void
	(e: "technique-hover", tacticId: string, techId: string): void
	(e: "technique-leave"): void
}>()

const expanded = defineModel<Record<string, boolean>>("expanded", { required: true })

const stats = computed(() => {
	const source = props.coverage?.tactics.find(t => t.id === props.tactic.id)?.techniques ?? props.tactic.techniques
	const total = source.length
	const covered = source.filter(t => t.total_rule_count > 0).length
	return { total, covered }
})

const isTacticUncovered = computed(() => {
	const { covered, total } = stats.value
	return total > 0 && covered === 0
})
</script>
