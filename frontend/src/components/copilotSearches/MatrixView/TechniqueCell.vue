<template>
	<n-popover
		trigger="hover"
		:delay="350"
		:duration="80"
		:show-arrow="false"
		placement="right"
		:disabled="tech.total_rule_count === 0"
	>
		<template #trigger>
			<div
				class="hover:border-primary/50 hover:bg-primary/6 border-default cursor-pointer rounded border px-2 py-1.5 text-xs"
				:class="[
					cellClass(tech),
					hoveredTechniqueId === tech.id && hoveredTacticId !== tactic.id && 'ring-primary/45 ring-2'
				]"
				:title="cellTooltip(tech)"
				@click="emit('open-technique', tactic, tech)"
				@mouseenter="emit('technique-hover', tactic.id, tech.id)"
				@mouseleave="emit('technique-leave')"
			>
				<div class="flex items-center justify-between gap-1.5">
					<div class="text-default font-mono text-xs font-semibold">{{ tech.id }}</div>
					<n-tag
						v-if="tech.total_rule_count > 0"
						size="tiny"
						:bordered="false"
						class="px-1! font-mono text-[11px]!"
					>
						{{ tech.total_rule_count }}
					</n-tag>
				</div>
				<div class="text-secondary mt-0.5 text-xs leading-tight">{{ tech.name }}</div>

				<n-button
					v-if="tech.subtechniques.length"
					text
					size="tiny"
					@click.stop="toggleExpand(tactic.id, tech.id)"
				>
					<template #icon>
						<Icon :name="expanded[tactic.id + tech.id] ? ChevronDown : ChevronRight" :size="12" />
					</template>
					{{ tech.subtechniques.length }} sub
				</n-button>

				<div
					v-if="expanded[tactic.id + tech.id]"
					class="bg-secondary border-default/70 mt-1 flex flex-col gap-0.5 rounded-sm border p-1"
					@click.stop
				>
					<SubTechniqueCell
						v-for="sub of visibleSubs(tech, expandKey)"
						:key="sub.id"
						:tactic
						:tech
						:sub
						:rules-index
						@open-sub-technique="
							(t, technique, subTech) => emit('open-sub-technique', t, technique, subTech)
						"
						@open-rule="ruleId => emit('open-rule', ruleId)"
					/>

					<div
						v-if="tech.subtechniques.length > SUB_PREVIEW_LIMIT"
						class="border-default text-tertiary hover:border-primary/50 hover:bg-primary/6 hover:text-primary mt-0.5 cursor-pointer rounded-sm border border-dashed px-1.5 py-0.5 text-center text-xs select-none"
						@click.stop="toggleShowAllSubs(expandKey)"
					>
						{{ showAllSubs[expandKey] ? `Show fewer` : `Show all ${tech.subtechniques.length}` }}
					</div>
				</div>
			</div>
		</template>

		<RulePreviewList
			:rule-ids="tech.rule_ids"
			:index="rulesIndex"
			:extra-via-subs="tech.total_rule_count - tech.rule_count"
			@open-rule="ruleId => emit('open-rule', ruleId)"
		/>
	</n-popover>
</template>

<script setup lang="ts">
import type { MitreRuleIndexEntry, MitreSubTechnique, MitreTactic, MitreTechnique } from "@/types/copilotSearches.d"
import { NButton, NPopover, NTag } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import RulePreviewList from "../RulePreviewList.vue"
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

const showAllSubs = ref<Record<string, boolean>>({})

const SUB_PREVIEW_LIMIT = 5

const expandKey = computed(() => props.tactic.id + props.tech.id)

function visibleSubs(tech: MitreTechnique, key: string) {
	if (showAllSubs.value[key]) return tech.subtechniques
	return tech.subtechniques.slice(0, SUB_PREVIEW_LIMIT)
}

function toggleShowAllSubs(key: string) {
	showAllSubs.value[key] = !showAllSubs.value[key]
}

function cellClass(technique: MitreTechnique) {
	const count = technique.total_rule_count
	if (count === 0) return "cov-empty"
	if (count === 1) return "cov-1"
	if (count <= 3) return "cov-2"
	if (count <= 7) return "cov-3"
	return "cov-4"
}

function cellTooltip(tech: MitreTechnique) {
	if (tech.total_rule_count === 0) return `${tech.id} ${tech.name} — no CoPilot rules`
	const subDelta = tech.total_rule_count - tech.rule_count
	return subDelta
		? `${tech.id} ${tech.name} — ${tech.rule_count} direct, +${subDelta} via sub-techniques`
		: `${tech.id} ${tech.name} — ${tech.rule_count} rule(s)`
}

function toggleExpand(tacticId: string, techId: string) {
	const k = tacticId + techId
	const willOpen = !expanded.value[k]
	if (willOpen) {
		for (const otherKey of Object.keys(expanded.value)) {
			if (otherKey.startsWith(tacticId) && otherKey !== k) {
				expanded.value[otherKey] = false
			}
		}
	}
	expanded.value[k] = willOpen
}
</script>
