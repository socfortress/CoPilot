<template>
	<div ref="matrixScrollWrapRef" class="relative" :style="matrixScrollWrapStyle">
		<n-spin v-if="loading && coverage" show class="absolute inset-0 flex items-center justify-center" />

		<div
			class="scrollbar-styled bg-secondary border-default h-full overflow-auto rounded-lg border pb-1"
			:class="{ 'opacity-55': loading && coverage }"
		>
			<n-empty
				v-if="!loading && coverage && filteredTactics.length === 0"
				description="No techniques match your filters."
				class="min-h-96"
			>
				<template #extra>
					<n-button size="small" @click="emit('clear-filters')">Clear filters</n-button>
				</template>
			</n-empty>

			<n-spin v-else-if="loading && !coverage" show class="flex min-h-96 w-full items-center justify-center" />

			<div v-else class="flex min-w-max gap-1.5 p-1">
				<div v-for="tactic of filteredTactics" :key="tactic.id" class="flex w-50 shrink-0 flex-col">
					<div
						class="bg-secondary border-default sticky top-0 z-2 rounded-t-md border border-b-2 px-2.5 py-2"
						:class="{
							'border-warning/55 border-b-warning/70 bg-warning/6': isTacticUncovered(tactic)
						}"
					>
						<div class="flex items-center justify-between gap-2">
							<div class="text-default text-sm font-semibold">{{ tactic.name }}</div>
							<n-tag
								size="tiny"
								:type="isTacticUncovered(tactic) ? 'warning' : 'default'"
								:title="`${tacticStats(tactic).covered} of ${tacticStats(tactic).total} techniques covered by CoPilot rules`"
							>
								<span class="font-mono text-[10px]">{{ tacticStats(tactic).covered }}</span>
								<span class="text-tertiary mx-1 text-xs">/</span>
								<span class="font-mono text-[10px]">{{ tacticStats(tactic).total }}</span>
							</n-tag>
						</div>
						<div class="text-tertiary text-xs">{{ tactic.techniques.length }} shown</div>
					</div>

					<div class="flex flex-col gap-1 pt-1">
						<n-popover
							v-for="tech of tactic.techniques"
							:key="tactic.id + tech.id"
							trigger="hover"
							:delay="350"
							:duration="80"
							:show-arrow="false"
							placement="right"
							:disabled="tech.total_rule_count === 0"
						>
							<template #trigger>
								<div
									class="bg-default border-default hover:border-primary/60 hover:bg-primary/8 cursor-pointer rounded border px-2 py-1.5 text-xs"
									:class="[
										cellClass(tech),
										hoveredTechniqueId === tech.id &&
											hoveredTacticId !== tactic.id &&
											'ring-primary/45 ring-2'
									]"
									:title="cellTooltip(tech)"
									@click="emit('open-technique', tactic, tech)"
									@mouseenter="onCellEnter(tactic.id, tech.id)"
									@mouseleave="onCellLeave"
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
											<Icon
												:name="expanded[tactic.id + tech.id] ? ChevronDown : ChevronRight"
												:size="12"
											/>
										</template>
										{{ tech.subtechniques.length }} sub
									</n-button>

									<div
										v-if="expanded[tactic.id + tech.id]"
										class="mt-1 flex flex-col gap-0.5"
										@click.stop
									>
										<n-popover
											v-for="sub of visibleSubs(tech, tactic.id + tech.id)"
											:key="sub.id"
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
													:title="subCellTooltip(sub)"
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

										<div
											v-if="tech.subtechniques.length > SUB_PREVIEW_LIMIT"
											class="border-default text-tertiary hover:border-primary/50 hover:bg-primary/6 hover:text-primary mt-0.5 cursor-pointer rounded-sm border border-dashed px-1.5 py-0.5 text-center text-xs select-none"
											@click.stop="toggleShowAllSubs(tactic.id + tech.id)"
										>
											{{
												showAllSubs[tactic.id + tech.id]
													? `Show fewer`
													: `Show all ${tech.subtechniques.length}`
											}}
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

						<n-empty
							v-if="!tactic.techniques.length"
							description="No techniques"
							class="py-4"
							size="small"
						/>
					</div>
				</div>
			</div>
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
import { useElementBounding, useWindowSize } from "@vueuse/core"
import { NButton, NEmpty, NPopover, NSpin, NTag } from "naive-ui"
import { computed, ref, useTemplateRef } from "vue"
import Icon from "@/components/common/Icon.vue"
import RulePreviewList from "../RulePreviewList.vue"

const props = defineProps<{
	loading: boolean
	coverage: MitreCoverageResponse | null
	filteredTactics: MitreTactic[]
	rulesIndex: Record<string, MitreRuleIndexEntry>
}>()

const emit = defineEmits<{
	(e: "clear-filters"): void
	(e: "open-technique", tactic: MitreTactic, tech: MitreTechnique): void
	(e: "open-sub-technique", tactic: MitreTactic, tech: MitreTechnique, sub: MitreSubTechnique): void
	(e: "open-rule", ruleId: string): void
}>()

const expanded = defineModel<Record<string, boolean>>("expanded", { required: true })

const ChevronRight = "carbon:chevron-right"
const ChevronDown = "carbon:chevron-down"

const matrixScrollWrapRef = useTemplateRef<HTMLDivElement>("matrixScrollWrapRef")
const { top: matrixScrollWrapTop } = useElementBounding(matrixScrollWrapRef)
const { height: viewportHeight } = useWindowSize()

const matrixScrollWrapStyle = computed(() => {
	const height = viewportHeight.value - matrixScrollWrapTop.value - 50
	if (height <= 0) return undefined
	return { height: `${Math.floor(height)}px` }
})

const showAllSubs = ref<Record<string, boolean>>({})
const hoveredTechniqueId = ref<string | null>(null)
const hoveredTacticId = ref<string | null>(null)

const SUB_PREVIEW_LIMIT = 5

function visibleSubs(tech: MitreTechnique, key: string) {
	if (showAllSubs.value[key]) return tech.subtechniques
	return tech.subtechniques.slice(0, SUB_PREVIEW_LIMIT)
}

function toggleShowAllSubs(key: string) {
	showAllSubs.value[key] = !showAllSubs.value[key]
}

function tacticStats(tactic: MitreTactic) {
	const source = props.coverage?.tactics.find(t => t.id === tactic.id)?.techniques ?? tactic.techniques
	const total = source.length
	const covered = source.filter(t => t.total_rule_count > 0).length
	return { total, covered }
}

function isTacticUncovered(tactic: MitreTactic): boolean {
	const { covered, total } = tacticStats(tactic)
	return total > 0 && covered === 0
}

function cellClass(item: MitreTechnique | MitreSubTechnique) {
	const count = "total_rule_count" in item ? item.total_rule_count : item.rule_count
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

function subCellTooltip(sub: MitreSubTechnique) {
	return sub.rule_count ? `${sub.id} ${sub.name} — ${sub.rule_count} rule(s)` : `${sub.id} ${sub.name} — no rules`
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

function onCellEnter(tacticId: string, techId: string) {
	hoveredTacticId.value = tacticId
	hoveredTechniqueId.value = techId
}

function onCellLeave() {
	hoveredTacticId.value = null
	hoveredTechniqueId.value = null
}
</script>

<style scoped lang="scss">
.cov-empty {
	background: var(--bg-default-color);
}
.cov-1 {
	background: rgba(var(--primary-color-rgb) / 0.07);
}
.cov-2 {
	background: rgba(var(--primary-color-rgb) / 0.16);
}
.cov-3 {
	background: rgba(var(--primary-color-rgb) / 0.28);
}
.cov-4 {
	background: rgba(var(--primary-color-rgb) / 0.45);
}
</style>
