<template>
	<div
		class="hover:border-primary/50 hover:bg-primary/6 border-default flex flex-col gap-1 rounded border px-2 py-1.5 text-xs"
		:class="[
			coverageClass(tech.total_rule_count),
			hoveredTechniqueId === tech.id && hoveredTacticId !== tactic.id && 'ring-primary/45 ring-2'
		]"
		:title="techniqueCellTooltip(tech)"
		@mouseenter="emit('technique-hover', tactic.id, tech.id)"
		@mouseleave="emit('technique-leave')"
	>
		<div class="flex items-center justify-between gap-1.5">
			<div class="text-default font-mono text-xs font-semibold">{{ tech.id }}</div>
			<div class="flex items-center gap-1">
				<n-tag
					size="small"
					:bordered="false"
					class="hover:text-primary! flex max-h-5 cursor-pointer! items-center px-1! font-mono text-[11px]! [&_.n-tag\_\_content]:flex [&_.n-tag\_\_content]:items-center"
					@click="emit('open-technique', tactic, tech)"
				>
					<Icon name="carbon:view" :size="12" class="mx-0.5" />
				</n-tag>
				<MatrixRuleCountPopover
					:rule-ids="tech.rule_ids"
					:rule-count="tech.total_rule_count"
					:index="rulesIndex"
					tag-size="small"
					:icon-size="11"
					:extra-via-subs="tech.total_rule_count - tech.rule_count"
					@open-rule="ruleId => emit('open-rule', ruleId)"
				/>
			</div>
		</div>

		<div class="text-secondary mt-0.5 text-xs leading-tight">{{ tech.name }}</div>

		<n-button
			v-if="tech.subtechniques.length"
			text
			size="tiny"
			class="max-h-4 w-fit!"
			@click.stop="toggleExpand(tactic.id, tech.id)"
		>
			<template #icon>
				<Icon :name="expanded[tactic.id + tech.id] ? ChevronDown : ChevronRight" :size="12" />
			</template>
			{{ tech.subtechniques.length }} sub
		</n-button>

		<n-collapse-transition :show="!!expanded[expandKey]">
			<div class="bg-secondary border-default/70 mt-1 flex flex-col gap-1 rounded-lg border p-1">
				<SubTechniqueCell
					v-for="sub of visibleSubs(tech, expandKey)"
					:key="sub.id"
					:tactic
					:tech
					:sub
					:rules-index
					@open-sub-technique="(t, technique, subTech) => emit('open-sub-technique', t, technique, subTech)"
					@open-rule="ruleId => emit('open-rule', ruleId)"
				/>
				<button
					v-if="tech.subtechniques.length > SUB_PREVIEW_LIMIT"
					type="button"
					class="border-default text-tertiary hover:border-primary/50 hover:bg-primary/6 hover:text-primary mt-0.5 w-full cursor-pointer rounded-sm border border-dashed px-1.5 py-0.5 text-center text-xs select-none"
					@click.stop="toggleShowAllSubs(expandKey)"
				>
					{{ showAllSubs[expandKey] ? "Show fewer" : `Show all ${tech.subtechniques.length}` }}
				</button>
			</div>
		</n-collapse-transition>
	</div>
</template>

<script setup lang="ts">
import type { MitreRuleIndexEntry, MitreSubTechnique, MitreTactic, MitreTechnique } from "@/types/copilotSearches"
import { NButton, NCollapseTransition, NTag } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import { coverageClass, techniqueCellTooltip } from "./matrixCoverage"
import MatrixRuleCountPopover from "./MatrixRuleCountPopover.vue"
import SubTechniqueCell from "./SubTechniqueCell.vue"

const props = defineProps<{
	tactic: MitreTactic
	tech: MitreTechnique
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

const ChevronRight = "carbon:chevron-right"
const ChevronDown = "carbon:chevron-down"
const SUB_PREVIEW_LIMIT = 5

const showAllSubs = ref<Record<string, boolean>>({})
const expandKey = computed(() => props.tactic.id + props.tech.id)

function visibleSubs(tech: MitreTechnique, key: string) {
	return showAllSubs.value[key] ? tech.subtechniques : tech.subtechniques.slice(0, SUB_PREVIEW_LIMIT)
}

function toggleShowAllSubs(key: string) {
	showAllSubs.value[key] = !showAllSubs.value[key]
}

function toggleExpand(tacticId: string, techId: string) {
	const k = tacticId + techId
	const willOpen = !expanded.value[k]
	if (willOpen) {
		for (const otherKey of Object.keys(expanded.value)) {
			if (otherKey.startsWith(tacticId) && otherKey !== k) expanded.value[otherKey] = false
		}
	}
	expanded.value[k] = willOpen
}
</script>
