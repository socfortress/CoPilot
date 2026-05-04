<template>
	<div class="flex flex-col gap-3">
		<div class="flex flex-wrap items-center gap-2">
			<div class="bg-default rounded-lg">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<n-button size="small" class="cursor-help!">
							<template #icon>
								<Icon :name="InfoIcon" />
							</template>
						</n-button>
					</template>
					<div v-if="coverage" class="flex flex-col gap-2">
						<div class="box">
							Tactics:
							<code>{{ coverage.stats.total_tactics }}</code>
						</div>
						<div class="box">
							Techniques:
							<code>{{ coverage.stats.total_techniques }}</code>
						</div>
						<div class="box">
							Covered:
							<code>{{ coverage.stats.covered_techniques }}</code>
						</div>
						<div class="box">
							Rules:
							<code>{{ coverage.stats.total_rules }}</code>
						</div>
					</div>
				</n-popover>
			</div>

			<n-input
				v-model:value="searchQuery"
				size="small"
				placeholder="Filter techniques..."
				class="max-w-60 grow"
				clearable
			>
				<template #prefix>
					<Icon :name="SearchIcon" />
				</template>
			</n-input>

			<n-checkbox v-model:checked="onlyCovered" size="small" class="shrink-0! whitespace-nowrap">
				<span class="text-xs">Only covered</span>
			</n-checkbox>

			<div v-if="coverage" class="text-secondary ml-auto text-xs">
				<strong>{{ coverage.stats.covered_techniques }}</strong>
				/
				<strong>{{ coverage.stats.total_techniques }}</strong>
				techniques ·
				<strong>{{ coverage.stats.total_rules }}</strong>
				rules
			</div>

			<n-button size="small" :loading="refreshing" @click="handleRefresh">
				<template #icon>
					<Icon :name="RefreshIcon" />
				</template>
				Refresh Matrix
			</n-button>
		</div>

		<div class="legend">
			<span class="text-secondary text-xs">Rule coverage:</span>
			<div v-for="step of legendSteps" :key="step.label" class="legend-item">
				<span class="legend-swatch" :class="step.cls" />
				<span class="text-secondary text-xs">{{ step.label }}</span>
			</div>
		</div>

		<n-spin :show="loading">
			<div class="matrix-scroll">
				<div class="matrix-grid">
					<div v-for="tactic of filteredTactics" :key="tactic.id" class="tactic-column">
						<div class="tactic-header">
							<div class="flex items-center justify-between gap-2">
								<div class="tactic-name">{{ tactic.name }}</div>
								<n-tag
									size="tiny"
									round
									:bordered="false"
									:type="tacticTagType(tactic)"
									class="tactic-coverage-tag"
									:title="`${tacticStats(tactic).covered} of ${tacticStats(tactic).total} techniques covered`"
								>
									{{ tacticStats(tactic).covered }}/{{ tacticStats(tactic).total }}
								</n-tag>
							</div>
							<div class="text-tertiary text-xs">{{ tactic.techniques.length }} shown</div>
						</div>

						<div class="technique-list">
							<div
								v-for="tech of tactic.techniques"
								:key="tactic.id + tech.id"
								class="technique-cell"
								:class="cellClass(tech)"
								:title="cellTooltip(tech)"
								@click="openTechnique(tech)"
							>
								<div class="technique-row">
									<div class="technique-id">{{ tech.id }}</div>
									<n-tag
										v-if="tech.total_rule_count > 0"
										size="tiny"
										round
										:bordered="false"
										class="count-tag"
									>
										{{ tech.total_rule_count }}
									</n-tag>
								</div>
								<div class="technique-name">{{ tech.name }}</div>

								<div
									v-if="tech.subtechniques.length"
									class="technique-sub-toggle"
									@click.stop="toggleExpand(tactic.id, tech.id)"
								>
									<Icon
										:name="expanded[tactic.id + tech.id] ? ChevronDown : ChevronRight"
										:size="10"
									/>
									{{ tech.subtechniques.length }} sub
								</div>

								<div
									v-if="expanded[tactic.id + tech.id]"
									class="subtechnique-list"
									@click.stop
								>
									<div
										v-for="sub of tech.subtechniques"
										:key="sub.id"
										class="subtechnique-cell"
										:class="cellClass(sub, true)"
										:title="subCellTooltip(sub)"
										@click="openSubTechnique(tech, sub)"
									>
										<div class="technique-row">
											<div class="subtechnique-id">{{ sub.id }}</div>
											<n-tag
												v-if="sub.rule_count > 0"
												size="tiny"
												round
												:bordered="false"
												class="count-tag"
											>
												{{ sub.rule_count }}
											</n-tag>
										</div>
										<div class="subtechnique-name">{{ sub.name }}</div>
									</div>
								</div>
							</div>

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
		</n-spin>

		<TechniqueDrawer
			v-model:show="drawerOpen"
			:technique="selectedTechnique"
			:sub-technique="selectedSubTechnique"
		/>
	</div>
</template>

<script setup lang="ts">
import type { MitreCoverageResponse, MitreSubTechnique, MitreTactic, MitreTechnique } from "@/types/copilotSearches.d"
import { useLocalStorage } from "@vueuse/core"
import { NButton, NCheckbox, NEmpty, NInput, NPopover, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import TechniqueDrawer from "./TechniqueDrawer.vue"

const InfoIcon = "carbon:information"
const SearchIcon = "carbon:search"
const RefreshIcon = "carbon:renew"
const ChevronRight = "carbon:chevron-right"
const ChevronDown = "carbon:chevron-down"

const loading = ref(false)
const refreshing = ref(false)
const coverage = ref<MitreCoverageResponse | null>(null)
const onlyCovered = useLocalStorage("copilot-searches/matrix/only-covered", false)
const searchQuery = ref("")
const expanded = useLocalStorage<Record<string, boolean>>("copilot-searches/matrix/expanded", {})

const drawerOpen = ref(false)
const selectedTechnique = ref<MitreTechnique | null>(null)
const selectedSubTechnique = ref<MitreSubTechnique | null>(null)

const message = useMessage()

const filteredTactics = computed<MitreTactic[]>(() => {
	if (!coverage.value) return []
	const q = searchQuery.value.trim().toLowerCase()
	return coverage.value.tactics.map(tactic => ({
		...tactic,
		techniques: tactic.techniques.filter(tech => {
			if (onlyCovered.value && tech.total_rule_count === 0) return false
			if (q) {
				const haystack = `${tech.id} ${tech.name}`.toLowerCase()
				if (!haystack.includes(q)) return false
			}
			return true
		})
	}))
})

const legendSteps = [
	{ label: "0", cls: "cov-empty" },
	{ label: "1", cls: "cov-1" },
	{ label: "2-3", cls: "cov-2" },
	{ label: "4-7", cls: "cov-3" },
	{ label: "8+", cls: "cov-4" }
] as const

function tacticStats(tactic: MitreTactic) {
	// Count against the unfiltered tactic data so the badge is stable across filters.
	const source = coverage.value?.tactics.find(t => t.id === tactic.id)?.techniques ?? tactic.techniques
	const total = source.length
	const covered = source.filter(t => t.total_rule_count > 0).length
	return { total, covered }
}

function tacticTagType(tactic: MitreTactic): "default" | "success" | "warning" | "info" {
	const { covered, total } = tacticStats(tactic)
	if (total === 0) return "default"
	const ratio = covered / total
	if (ratio === 0) return "default"
	if (ratio < 0.25) return "warning"
	if (ratio < 0.66) return "info"
	return "success"
}

function cellClass(item: MitreTechnique | MitreSubTechnique, isSub = false) {
	const count = "total_rule_count" in item ? item.total_rule_count : item.rule_count
	const base = isSub ? "subtechnique-cell" : "technique-cell"
	if (count === 0) return `cov-empty`
	if (count === 1) return `cov-1`
	if (count <= 3) return `cov-2`
	if (count <= 7) return `cov-3`
	return `cov-4`
}

function cellTooltip(tech: MitreTechnique) {
	if (tech.total_rule_count === 0) return `${tech.id} ${tech.name} — no CoPilot rules`
	const subDelta = tech.total_rule_count - tech.rule_count
	return subDelta
		? `${tech.id} ${tech.name} — ${tech.rule_count} direct, +${subDelta} via sub-techniques`
		: `${tech.id} ${tech.name} — ${tech.rule_count} rule(s)`
}
function subCellTooltip(sub: MitreSubTechnique) {
	return sub.rule_count
		? `${sub.id} ${sub.name} — ${sub.rule_count} rule(s)`
		: `${sub.id} ${sub.name} — no rules`
}

function toggleExpand(tacticId: string, techId: string) {
	const k = tacticId + techId
	expanded.value[k] = !expanded.value[k]
}

function openTechnique(tech: MitreTechnique) {
	selectedTechnique.value = tech
	selectedSubTechnique.value = null
	drawerOpen.value = true
}
function openSubTechnique(tech: MitreTechnique, sub: MitreSubTechnique) {
	selectedTechnique.value = tech
	selectedSubTechnique.value = sub
	drawerOpen.value = true
}

async function load() {
	loading.value = true
	try {
		const res = await Api.copilotSearches.getMitreCoverage()
		if (res.data?.success) {
			coverage.value = res.data
		} else {
			message.warning(res.data?.message || "Failed to load MITRE coverage")
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to load MITRE coverage")
	} finally {
		loading.value = false
	}
}

async function handleRefresh() {
	refreshing.value = true
	try {
		await Api.copilotSearches.refreshMitreMatrix()
		await load()
		message.success("MITRE matrix refreshed")
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to refresh MITRE matrix")
	} finally {
		refreshing.value = false
	}
}

onMounted(load)
</script>

<style scoped lang="scss">
.legend {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 10px;
	padding: 6px 10px;
	background: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: 6px;
}

.legend-item {
	display: inline-flex;
	align-items: center;
	gap: 5px;
}

.legend-swatch {
	display: inline-block;
	width: 14px;
	height: 14px;
	border-radius: 3px;
	border: 1px solid var(--border-color);
}

.tactic-coverage-tag {
	font-weight: 700;
	min-width: 36px;
	justify-content: center;
}

.matrix-scroll {
	overflow-x: auto;
	padding-bottom: 8px;
}

.matrix-grid {
	display: flex;
	gap: 6px;
	min-width: max-content;
}

.tactic-column {
	width: 200px;
	flex-shrink: 0;
	display: flex;
	flex-direction: column;
}

.tactic-header {
	padding: 8px 10px;
	background: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: 6px 6px 0 0;
	border-bottom-width: 2px;
}

.tactic-name {
	font-weight: 600;
	font-size: 0.85rem;
	color: var(--fg-default-color);
}

.technique-list {
	display: flex;
	flex-direction: column;
	gap: 3px;
	padding-top: 3px;
}

.technique-cell {
	padding: 6px 8px;
	border-radius: 4px;
	cursor: pointer;
	transition: background-color 0.12s, border-color 0.12s;
	font-size: 0.75rem;
	border: 1px solid var(--border-color);
	background: var(--bg-default-color);
}

.technique-cell:hover {
	border-color: rgba(var(--primary-color-rgb) / 0.6);
	background: rgba(var(--primary-color-rgb) / 0.08);
}

.technique-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 6px;
}

.technique-id {
	font-weight: 600;
	font-family: var(--font-family-mono, monospace);
	color: var(--fg-default-color);
	font-size: 0.72rem;
}

.technique-name {
	font-size: 0.7rem;
	color: var(--fg-secondary-color);
	margin-top: 2px;
	line-height: 1.25;
}

.count-tag {
	font-weight: 700;
	min-width: 22px;
	justify-content: center;
}

.technique-sub-toggle {
	margin-top: 4px;
	font-size: 0.65rem;
	color: var(--fg-tertiary-color);
	cursor: pointer;
	user-select: none;
	display: inline-flex;
	align-items: center;
	gap: 3px;
	padding: 2px 4px;
	border-radius: 3px;
	width: fit-content;
}

.technique-sub-toggle:hover {
	color: var(--primary-color);
	background: rgba(var(--primary-color-rgb) / 0.08);
}

.subtechnique-list {
	margin-top: 4px;
	padding-left: 6px;
	display: flex;
	flex-direction: column;
	gap: 2px;
	border-left: 2px solid var(--border-color);
}

.subtechnique-cell {
	padding: 4px 6px;
	border-radius: 3px;
	cursor: pointer;
	font-size: 0.7rem;
	border: 1px solid var(--border-color);
	background: var(--bg-default-color);
	transition: background-color 0.12s, border-color 0.12s;
}

.subtechnique-cell:hover {
	border-color: rgba(var(--primary-color-rgb) / 0.6);
	background: rgba(var(--primary-color-rgb) / 0.08);
}

.subtechnique-id {
	font-family: var(--font-family-mono, monospace);
	font-weight: 600;
	font-size: 0.65rem;
	color: var(--fg-default-color);
}

.subtechnique-name {
	font-size: 0.65rem;
	color: var(--fg-secondary-color);
	line-height: 1.25;
}

/* Coverage heat — primary brand color with opacity steps */
.cov-empty {
	background: var(--bg-default-color);
}
.cov-1 {
	background: rgba(var(--primary-color-rgb) / 0.12);
	border-color: rgba(var(--primary-color-rgb) / 0.25);
}
.cov-2 {
	background: rgba(var(--primary-color-rgb) / 0.25);
	border-color: rgba(var(--primary-color-rgb) / 0.4);
}
.cov-3 {
	background: rgba(var(--primary-color-rgb) / 0.45);
	border-color: rgba(var(--primary-color-rgb) / 0.6);
}
.cov-4 {
	background: rgba(var(--primary-color-rgb) / 0.7);
	border-color: rgba(var(--primary-color-rgb) / 0.85);
}
.cov-1 .technique-name,
.cov-2 .technique-name,
.cov-3 .technique-name,
.cov-4 .technique-name,
.cov-1 .subtechnique-name,
.cov-2 .subtechnique-name,
.cov-3 .subtechnique-name,
.cov-4 .subtechnique-name {
	color: var(--fg-default-color);
}
</style>
