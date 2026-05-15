<template>
	<div class="flex flex-col gap-3">
		<div class="flex flex-wrap items-center justify-end gap-2">
			<div class="flex min-w-80 grow gap-2">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-button size="small" class="cursor-help!">
								<template #icon>
									<Icon :name="InfoIcon" />
								</template>
							</n-button>
						</div>
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
							Rules in scope:
							<code>{{ coverage.stats.total_rules }}</code>
						</div>
					</div>
				</n-popover>

				<n-input
					v-model:value="searchQuery"
					size="small"
					placeholder="Search techniques or rule names..."
					class="max-w-120"
					clearable
				>
					<template #prefix>
						<Icon :name="SearchIcon" />
					</template>
				</n-input>

				<n-popover :show="showFilters" trigger="manual" overlap placement="bottom-start" class="px-0!">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-badge :show="anyFiltersActive" dot type="success" :offset="[-4, 0]">
								<n-button size="small" @click="showFilters = !showFilters">
									<template #icon>
										<Icon :name="FilterIcon" />
									</template>
								</n-button>
							</n-badge>
						</div>
					</template>
					<div class="divide-border flex w-50 flex-col gap-0 divide-y">
						<div class="flex flex-col gap-2.5 px-3 pt-1 pb-3">
							<n-select
								v-model:value="selectedPlatform"
								:options="platformOptions"
								size="small"
								placeholder="Platform"
								class="w-full"
								clearable
								:consistent-menu-width="false"
							/>
							<n-select
								v-model:value="selectedSeverity"
								:options="severityOptions"
								clearable
								size="small"
								placeholder="Severity"
								class="w-full"
								:consistent-menu-width="false"
							/>
							<n-select
								v-model:value="selectedStatus"
								:options="statusOptions"
								clearable
								size="small"
								placeholder="Status"
								class="w-full"
								:consistent-menu-width="false"
							/>
							<n-checkbox v-model:checked="hasGraylogFilter" size="small">
								<span class="text-xs">Graylog Only</span>
							</n-checkbox>
						</div>
						<div class="flex justify-between gap-2 px-3 pt-2">
							<n-button size="small" quaternary @click="showFilters = false">Close</n-button>
							<n-button size="small" secondary @click="resetFilters">Reset</n-button>
						</div>
					</div>
				</n-popover>

				<n-checkbox v-model:checked="onlyCovered" size="small" class="shrink-0! self-center whitespace-nowrap">
					<span class="text-xs">Only covered</span>
				</n-checkbox>
			</div>

			<n-tooltip placement="bottom-end">
				<template #trigger>
					<n-button size="small" :disabled="!coverage" @click="exportCoverageCsv">
						<template #icon>
							<Icon :name="ExportIcon" />
						</template>
						Export CSV
					</n-button>
				</template>
				Download a CSV of the current coverage (one row per technique and sub-technique, with rule counts and
				IDs).
			</n-tooltip>

			<n-tooltip placement="bottom-end">
				<template #trigger>
					<n-button size="small" :loading="refreshing" @click="handleRefresh">
						<template #icon>
							<Icon :name="RefreshIcon" />
						</template>
						Refresh Matrix
					</n-button>
				</template>
				Force a re-fetch of the MITRE ATT&amp;CK STIX bundle from
				<code>github.com/mitre/cti</code>
				, bypassing the 24-hour cache. Use this if MITRE published a new release and you want the matrix to pick
				it up immediately.
			</n-tooltip>
		</div>

		<div class="legend">
			<span class="text-tertiary text-xs">Rules:</span>
			<div v-for="step of legendSteps" :key="step.label" class="legend-item">
				<span class="legend-swatch" :class="step.cls" />
				<span class="text-secondary text-xs">{{ step.label }}</span>
			</div>
			<div v-if="coverage" class="text-secondary ml-auto text-xs">
				<strong>{{ coverage.stats.covered_techniques }}</strong>
				/
				<strong>{{ coverage.stats.total_techniques }}</strong>
				techniques ·
				<strong>{{ coverage.stats.total_rules }}</strong>
				rules
			</div>
		</div>

		<div class="matrix-scroll-wrap">
			<!-- Subtle top progress bar replaces the heavy spin overlay during refetches. -->
			<div v-if="loading && coverage" class="matrix-progress" />

			<div class="matrix-scroll" :class="{ 'matrix-scroll-loading': loading && coverage }">
				<n-empty
					v-if="!loading && coverage && filteredTactics.length === 0"
					description="No techniques match your filters."
					class="matrix-empty"
				>
					<template #extra>
						<n-button size="small" @click="clearAllFilters">Clear filters</n-button>
					</template>
				</n-empty>

				<n-spin v-else-if="loading && !coverage" show class="matrix-initial-load" />

				<div v-else class="matrix-grid">
					<div v-for="tactic of filteredTactics" :key="tactic.id" class="tactic-column">
						<div class="tactic-header" :class="{ 'tactic-uncovered': isTacticUncovered(tactic) }">
							<div class="flex items-center justify-between gap-2">
								<div class="tactic-name">{{ tactic.name }}</div>
								<span
									class="tactic-coverage"
									:class="{ 'tactic-coverage-zero': isTacticUncovered(tactic) }"
									:title="`${tacticStats(tactic).covered} of ${tacticStats(tactic).total} techniques covered by CoPilot rules`"
								>
									{{ tacticStats(tactic).covered }}/{{ tacticStats(tactic).total }}
								</span>
							</div>
							<div class="text-tertiary text-xs">{{ tactic.techniques.length }} shown</div>
						</div>

						<div class="technique-list">
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
										class="technique-cell"
										:class="[
											cellClass(tech),
											{
												'cell-cross-tactic':
													hoveredTechniqueId === tech.id && hoveredTacticId !== tactic.id
											}
										]"
										:title="cellTooltip(tech)"
										@click="openTechnique(tactic, tech)"
										@mouseenter="onCellEnter(tactic.id, tech.id)"
										@mouseleave="onCellLeave"
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

										<div v-if="expanded[tactic.id + tech.id]" class="subtechnique-list" @click.stop>
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
														class="subtechnique-cell"
														:class="cellClass(sub)"
														:title="subCellTooltip(sub)"
														@click="openSubTechnique(tactic, tech, sub)"
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
												</template>

												<RulePreviewList :rule-ids="sub.rule_ids" :index="rulesIndex" />
											</n-popover>

											<div
												v-if="tech.subtechniques.length > SUB_PREVIEW_LIMIT"
												class="show-all-subs"
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

		<TechniqueDrawer
			v-model:show="drawerOpen"
			:technique="selectedTechnique"
			:sub-technique="selectedSubTechnique"
			@update:show="onDrawerToggle"
		/>

		<!-- Direct-from-hover rule detail modal: skips the drawer entirely
		     when the user clicks a rule name inside the hover preview. -->
		<n-modal
			v-model:show="quickRuleOpen"
			preset="card"
			:style="{ maxWidth: 'min(750px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			title="Detection Rule"
			:bordered="false"
			segmented
		>
			<RuleCardContent v-if="quickRuleId" :rule-id="quickRuleId" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type {
	MitreCoverageQuery,
	MitreCoverageResponse,
	MitreRuleIndexEntry,
	MitreSubTechnique,
	MitreTactic,
	MitreTechnique,
	PlatformFilter,
	RuleSeverity,
	RuleStatus
} from "@/types/copilotSearches.d"
import { useLocalStorage, watchDebounced } from "@vueuse/core"
import {
	NBadge,
	NButton,
	NCheckbox,
	NEmpty,
	NInput,
	NModal,
	NPopover,
	NSelect,
	NSpin,
	NTag,
	NTooltip,
	useMessage
} from "naive-ui"
import { computed, h, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import RuleCardContent from "./RuleCardContent.vue"
import TechniqueDrawer from "./TechniqueDrawer.vue"

const InfoIcon = "carbon:information"
const SearchIcon = "carbon:search"
const RefreshIcon = "carbon:renew"
const FilterIcon = "carbon:filter-edit"
const ExportIcon = "carbon:download"
const ChevronRight = "carbon:chevron-right"
const ChevronDown = "carbon:chevron-down"

const route = useRoute()
const router = useRouter()
const message = useMessage()

const loading = ref(false)
const refreshing = ref(false)
const coverage = ref<MitreCoverageResponse | null>(null)
const onlyCovered = useLocalStorage("copilot-searches/matrix/only-covered", false)
const searchQuery = ref("")
const expanded = useLocalStorage<Record<string, boolean>>("copilot-searches/matrix/expanded", {})
const showAllSubs = ref<Record<string, boolean>>({})

const SUB_PREVIEW_LIMIT = 5

function visibleSubs(tech: MitreTechnique, key: string) {
	if (showAllSubs.value[key]) return tech.subtechniques
	return tech.subtechniques.slice(0, SUB_PREVIEW_LIMIT)
}
function toggleShowAllSubs(key: string) {
	showAllSubs.value[key] = !showAllSubs.value[key]
}

const selectedPlatform = ref<PlatformFilter | null>(null)
const selectedSeverity = ref<RuleSeverity | null>(null)
const selectedStatus = ref<RuleStatus | null>(null)
const hasGraylogFilter = ref(false)
const showFilters = ref(false)

const drawerOpen = ref(false)
const selectedTechnique = ref<MitreTechnique | null>(null)
const selectedSubTechnique = ref<MitreSubTechnique | null>(null)
const selectedTacticIdForDeepLink = ref<string | null>(null)

// Direct-from-hover rule modal
const quickRuleOpen = ref(false)
const quickRuleId = ref<string | null>(null)
function openQuickRule(ruleId: string) {
	quickRuleId.value = ruleId
	quickRuleOpen.value = true
}

const hoveredTechniqueId = ref<string | null>(null)
const hoveredTacticId = ref<string | null>(null)

// Suppresses the filter-change watcher during the initial URL→ref hydration
// so we don't fire a duplicate fetch right after the first load.
const ready = ref(false)

const platformOptions = [
	{ label: "Linux", value: "linux" },
	{ label: "Windows", value: "windows" },
	{ label: "PowerShell", value: "powershell" },
	{ label: "CVE", value: "cve" }
]
const severityOptions = [
	{ label: "Low", value: "low" },
	{ label: "Medium", value: "medium" },
	{ label: "High", value: "high" },
	{ label: "Critical", value: "critical" }
]
const statusOptions = [
	{ label: "Production", value: "production" },
	{ label: "Experimental", value: "experimental" },
	{ label: "Deprecated", value: "deprecated" }
]

const anyFiltersActive = computed(
	() => !!selectedPlatform.value || !!selectedSeverity.value || !!selectedStatus.value || !!hasGraylogFilter.value
)

const rulesIndex = computed<Record<string, MitreRuleIndexEntry>>(() => coverage.value?.rules_index ?? {})

/**
 * Match against rule names/IDs via the in-memory rules_index. Used to surface
 * techniques whose rules — not whose own name — match the search query.
 */
function ruleIdsMatch(ruleIds: string[], q: string): boolean {
	const idx = rulesIndex.value
	for (const id of ruleIds) {
		if (id.toLowerCase().includes(q)) return true
		const r = idx[id]
		if (r && r.name.toLowerCase().includes(q)) return true
	}
	return false
}

const filteredTactics = computed<MitreTactic[]>(() => {
	if (!coverage.value) return []
	const q = searchQuery.value.trim().toLowerCase()
	const tactics = coverage.value.tactics.map(tactic => ({
		...tactic,
		techniques: tactic.techniques.filter(tech => {
			if (onlyCovered.value && tech.total_rule_count === 0) return false
			if (q) {
				const techHaystack = `${tech.id} ${tech.name}`.toLowerCase()
				const techMatches = techHaystack.includes(q)
				const ruleMatches =
					ruleIdsMatch(tech.rule_ids, q) || tech.subtechniques.some(s => ruleIdsMatch(s.rule_ids, q))
				if (!techMatches && !ruleMatches) return false
			}
			return true
		})
	}))
	// When the user is actively searching, drop tactics with no matches so the
	// matrix collapses to just the relevant columns. Without an active search,
	// we keep empty tactics visible (they're informative on their own).
	return q ? tactics.filter(t => t.techniques.length > 0) : tactics
})

const legendSteps = [
	{ label: "0", cls: "cov-empty" },
	{ label: "1", cls: "cov-1" },
	{ label: "2-3", cls: "cov-2" },
	{ label: "4-7", cls: "cov-3" },
	{ label: "8+", cls: "cov-4" }
] as const

function tacticStats(tactic: MitreTactic) {
	const source = coverage.value?.tactics.find(t => t.id === tactic.id)?.techniques ?? tactic.techniques
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
	return sub.rule_count ? `${sub.id} ${sub.name} — ${sub.rule_count} rule(s)` : `${sub.id} ${sub.name} — no rules`
}

function toggleExpand(tacticId: string, techId: string) {
	const k = tacticId + techId
	const willOpen = !expanded.value[k]
	if (willOpen) {
		// Auto-collapse other expanded techniques in the same tactic so columns
		// don't sprawl vertically when several are open at once.
		for (const otherKey of Object.keys(expanded.value)) {
			if (otherKey.startsWith(tacticId) && otherKey !== k) {
				expanded.value[otherKey] = false
			}
		}
	}
	expanded.value[k] = willOpen
}

function clearAllFilters() {
	selectedPlatform.value = null
	selectedSeverity.value = null
	selectedStatus.value = null
	hasGraylogFilter.value = false
	searchQuery.value = ""
	onlyCovered.value = false
}

function exportCoverageCsv() {
	if (!coverage.value) return
	const rows: string[][] = [
		[
			"tactic_id",
			"tactic_name",
			"technique_id",
			"technique_name",
			"rule_count_direct",
			"rule_count_total",
			"rule_ids"
		]
	]
	for (const tactic of coverage.value.tactics) {
		for (const tech of tactic.techniques) {
			rows.push([
				tactic.id,
				tactic.name,
				tech.id,
				tech.name,
				String(tech.rule_count),
				String(tech.total_rule_count),
				tech.rule_ids.join("|")
			])
			for (const sub of tech.subtechniques) {
				rows.push([
					tactic.id,
					tactic.name,
					sub.id,
					sub.name,
					String(sub.rule_count),
					String(sub.rule_count),
					sub.rule_ids.join("|")
				])
			}
		}
	}
	const csv = rows.map(r => r.map(cell => `"${cell.replace(/"/g, '""')}"`).join(",")).join("\n")
	const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
	const url = URL.createObjectURL(blob)
	const link = document.createElement("a")
	link.href = url
	link.download = `copilot-mitre-coverage-${new Date().toISOString().slice(0, 10)}.csv`
	document.body.appendChild(link)
	link.click()
	document.body.removeChild(link)
	URL.revokeObjectURL(url)
}

function onCellEnter(tacticId: string, techId: string) {
	hoveredTacticId.value = tacticId
	hoveredTechniqueId.value = techId
}
function onCellLeave() {
	hoveredTacticId.value = null
	hoveredTechniqueId.value = null
}

function resetFilters() {
	selectedPlatform.value = null
	selectedSeverity.value = null
	selectedStatus.value = null
	hasGraylogFilter.value = false
	showFilters.value = false
}

function openTechnique(tactic: MitreTactic, tech: MitreTechnique) {
	selectedTacticIdForDeepLink.value = tactic.id
	selectedTechnique.value = tech
	selectedSubTechnique.value = null
	drawerOpen.value = true
	syncRouteFromSelection()
}
function openSubTechnique(tactic: MitreTactic, tech: MitreTechnique, sub: MitreSubTechnique) {
	selectedTacticIdForDeepLink.value = tactic.id
	selectedTechnique.value = tech
	selectedSubTechnique.value = sub
	drawerOpen.value = true
	syncRouteFromSelection()
}

function onDrawerToggle(open: boolean) {
	if (!open) {
		// Drawer just closed — drop the technique deep-link query.
		const next = { ...route.query }
		delete next.technique
		delete next.sub
		router.replace({ query: next })
	}
}

function syncRouteFromSelection() {
	if (!selectedTechnique.value) return
	const next: Record<string, string> = { ...(route.query as Record<string, string>) }
	next.view = "matrix"
	next.technique = selectedTechnique.value.id
	if (selectedSubTechnique.value) next.sub = selectedSubTechnique.value.id
	else delete next.sub
	router.replace({ query: next })
}

function syncFiltersToUrl() {
	const next: Record<string, string> = { ...(route.query as Record<string, string>) }
	if (selectedPlatform.value) next.platform = selectedPlatform.value
	else delete next.platform
	if (selectedSeverity.value) next.severity = selectedSeverity.value
	else delete next.severity
	if (selectedStatus.value) next.status = selectedStatus.value
	else delete next.status
	if (hasGraylogFilter.value) next.has_graylog = "true"
	else delete next.has_graylog
	router.replace({ query: next })
}

function applyFiltersFromUrl() {
	const q = route.query
	const platform = q.platform as string | undefined
	const severity = q.severity as string | undefined
	const status = q.status as string | undefined

	const validPlatforms: PlatformFilter[] = ["all", "linux", "windows", "powershell", "cve"]
	const validSeverities: RuleSeverity[] = ["low", "medium", "high", "critical"]
	const validStatuses: RuleStatus[] = ["production", "experimental", "deprecated"]

	selectedPlatform.value =
		platform && (validPlatforms as string[]).includes(platform) ? (platform as PlatformFilter) : null
	selectedSeverity.value =
		severity && (validSeverities as string[]).includes(severity) ? (severity as RuleSeverity) : null
	selectedStatus.value = status && (validStatuses as string[]).includes(status) ? (status as RuleStatus) : null
	hasGraylogFilter.value = q.has_graylog === "true"
}

function applyDeepLinkFromRoute() {
	if (!coverage.value) return
	const techId = (route.query.technique as string | undefined)?.toUpperCase()
	const subId = (route.query.sub as string | undefined)?.toUpperCase()
	if (!techId) return

	for (const tactic of coverage.value.tactics) {
		const tech = tactic.techniques.find(t => t.id === techId)
		if (!tech) continue
		if (subId) {
			const sub = tech.subtechniques.find(s => s.id === subId)
			if (sub) {
				expanded.value[tactic.id + tech.id] = true
				openSubTechnique(tactic, tech, sub)
				return
			}
		}
		openTechnique(tactic, tech)
		return
	}
}

async function load(opts: { preserveDeepLink?: boolean } = {}) {
	loading.value = true
	const query: MitreCoverageQuery = {
		platform: selectedPlatform.value || undefined,
		severity: selectedSeverity.value || undefined,
		status: selectedStatus.value || undefined,
		has_graylog: hasGraylogFilter.value || undefined
	}
	try {
		const res = await Api.copilotSearches.getMitreCoverage(query)
		if (res.data?.success) {
			coverage.value = res.data
			if (opts.preserveDeepLink) applyDeepLinkFromRoute()
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

watchDebounced(
	[selectedPlatform, selectedSeverity, selectedStatus, hasGraylogFilter],
	() => {
		if (!ready.value) return
		syncFiltersToUrl()
		load()
	},
	{ debounce: 250 }
)

// React to deep-link URL changes (back/forward, paste-link, etc.).
watch(
	() => [route.query.technique, route.query.sub] as const,
	() => applyDeepLinkFromRoute()
)

onMounted(async () => {
	applyFiltersFromUrl()
	await load({ preserveDeepLink: true })
	ready.value = true
})

// ---------------------------------------------------------------------------
// Hover preview list — inline component. Rule rows are clickable; clicking
// one opens the existing rule-detail modal directly without going through
// the technique drawer.
// ---------------------------------------------------------------------------
const platformIcon: Record<string, string> = {
	linux: "logos:linux-tux",
	windows: "logos:microsoft-icon",
	powershell: "vscode-icons:file-type-powershell",
	cve: "carbon:security",
	unknown: "carbon:help"
}

function RulePreviewList(props: {
	ruleIds: string[]
	index: Record<string, MitreRuleIndexEntry>
	extraViaSubs?: number
}) {
	const ids = props.ruleIds || []
	if (!ids.length) {
		return h("div", { class: "preview-empty text-secondary text-xs" }, "No rules")
	}
	const shown = ids.slice(0, 6)
	const remainder = ids.length - shown.length
	return h("div", { class: "preview-wrap flex flex-col gap-1" }, [
		h(
			"div",
			{ class: "text-tertiary text-xs uppercase tracking-wide" },
			`${ids.length} rule${ids.length === 1 ? "" : "s"}${
				props.extraViaSubs ? ` · +${props.extraViaSubs} via sub-techniques` : ""
			}`
		),
		...shown.map(id => {
			const entry = props.index[id]
			const platform = (entry?.platform || "unknown").toLowerCase()
			const iconName = platformIcon[platform] || platformIcon.unknown
			const dataSources = entry?.data_sources || []
			return h(
				"div",
				{
					class: "preview-row flex flex-col gap-1",
					key: id,
					onClick: (e: MouseEvent) => {
						e.stopPropagation()
						openQuickRule(id)
					},
					title: "Click to open rule details"
				},
				[
					h("div", { class: "flex items-center gap-2" }, [
						h(Icon as any, { name: iconName, size: 14, class: "preview-platform shrink-0" }),
						h("span", { class: "preview-name text-default text-xs" }, entry?.name || id),
						entry?.severity
							? h(
									"span",
									{ class: `preview-sev preview-sev-${entry.severity.toLowerCase()} text-xs` },
									entry.severity
								)
							: null
					]),
					dataSources.length
						? h(
								"div",
								{ class: "preview-sources flex flex-wrap items-center gap-1" },
								dataSources.map(s => h("span", { class: "preview-source text-xs", key: s }, s))
							)
						: null
				]
			)
		}),
		remainder > 0
			? h("div", { class: "text-tertiary text-xs" }, `+ ${remainder} more — click cell to view all`)
			: null
	])
}
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
	border-radius: var(--border-radius);
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

.tactic-coverage {
	font-family: var(--font-family-mono, monospace);
	font-size: 0.7rem;
	font-weight: 600;
	color: var(--fg-secondary-color);
	background: var(--bg-default-color);
	border: 1px solid var(--border-color);
	border-radius: 3px;
	padding: 1px 6px;
	white-space: nowrap;
}

.matrix-scroll-wrap {
	position: relative;
}

/* Subtle indeterminate progress bar shown during filter refetches in place
   of a heavy spin overlay. Sits at the top of the scroll container and
   doesn't shift the layout when it appears/disappears. */
.matrix-progress {
	position: absolute;
	left: 0;
	right: 0;
	top: 0;
	height: 2px;
	overflow: hidden;
	background: rgba(var(--primary-color-rgb) / 0.1);
	z-index: 3;
	pointer-events: none;
	border-radius: var(--border-radius) var(--border-radius) 0 0;
}
.matrix-progress::after {
	content: "";
	position: absolute;
	top: 0;
	left: -40%;
	width: 40%;
	height: 100%;
	background: var(--primary-color);
	animation: matrix-progress-slide 1.1s ease-in-out infinite;
}
@keyframes matrix-progress-slide {
	0% {
		left: -40%;
	}
	100% {
		left: 100%;
	}
}

/* Matrix scrolls inside its own bounded box so the horizontal scrollbar
   is always reachable without scrolling the whole page. Height adapts to
   the viewport minus app chrome + our toolbar/legend rows. */
.matrix-scroll {
	overflow: auto;
	max-height: calc(100vh - 260px);
	min-height: 420px;
	padding-bottom: 4px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background: var(--bg-secondary-color);
	transition: opacity 0.18s ease;
}

/* During a filter refetch, fade existing data slightly so the user sees
   the fresh load is happening without the matrix disappearing. */
.matrix-scroll-loading {
	opacity: 0.55;
}

.matrix-empty {
	height: 100%;
	min-height: 380px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.matrix-initial-load {
	display: flex;
	align-items: center;
	justify-content: center;
	min-height: 380px;
	width: 100%;
}

.matrix-grid {
	display: flex;
	gap: 6px;
	min-width: max-content;
	padding: 4px;
}

.tactic-column {
	width: 200px;
	flex-shrink: 0;
	display: flex;
	flex-direction: column;
}

/* Tactic headers stick to the top of the scroll container so the column
   label is always visible while scrolling vertically through techniques. */
.tactic-header {
	position: sticky;
	top: 0;
	z-index: 2;
	padding: 8px 10px;
	background: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: 6px 6px 0 0;
	border-bottom-width: 2px;
}

/* Tactic with no covered techniques — soft warning border so coverage gaps
   surface at a glance without screaming. */
.tactic-header.tactic-uncovered {
	border-color: rgba(var(--warning-color-rgb) / 0.55);
	border-bottom-color: rgba(var(--warning-color-rgb) / 0.7);
	background: rgba(var(--warning-color-rgb) / 0.06);
}

.tactic-coverage-zero {
	color: var(--warning-color);
	border-color: rgba(var(--warning-color-rgb) / 0.55);
	background: rgba(var(--warning-color-rgb) / 0.08);
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
	transition:
		background-color 0.12s,
		border-color 0.12s,
		box-shadow 0.12s;
	font-size: 0.75rem;
	border: 1px solid var(--border-color);
	background: var(--bg-default-color);
}

.technique-cell:hover {
	border-color: rgba(var(--primary-color-rgb) / 0.6);
	background: rgba(var(--primary-color-rgb) / 0.08);
}

/* Same technique appearing in another tactic column — gets a soft outline
   so you can see cross-tactic membership at a glance. */
.cell-cross-tactic {
	box-shadow: 0 0 0 2px rgba(var(--primary-color-rgb) / 0.45);
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
	transition:
		background-color 0.12s,
		border-color 0.12s;
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

.show-all-subs {
	margin-top: 2px;
	padding: 3px 6px;
	font-size: 0.65rem;
	color: var(--fg-tertiary-color);
	cursor: pointer;
	border-radius: 3px;
	user-select: none;
	text-align: center;
	border: 1px dashed var(--border-color);
}
.show-all-subs:hover {
	color: var(--primary-color);
	border-color: rgba(var(--primary-color-rgb) / 0.5);
	background: rgba(var(--primary-color-rgb) / 0.06);
}

/* Coverage heat — subtle brand-tinted backgrounds, neutral borders so the
   grid still reads as a grid. Text never goes white-on-orange. */
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

<style lang="scss">
/* Unscoped: applies to the inline RulePreviewList rendered inside n-popover bodies,
   which sit outside the component tree. */
.preview-wrap {
	max-width: 360px;
}
.preview-row {
	cursor: pointer;
	padding: 2px 4px;
	border-radius: 3px;
	transition: background-color 0.1s;
}
.preview-row:hover {
	background: rgba(var(--primary-color-rgb) / 0.1);
}
.preview-row:hover .preview-name {
	color: var(--primary-color);
}
.preview-row .preview-name {
	flex: 1;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.preview-platform {
	opacity: 0.85;
}

.preview-sources {
	margin-left: 22px;
}
.preview-source {
	font-size: 0.6rem;
	font-weight: 500;
	letter-spacing: 0.02em;
	color: var(--fg-tertiary-color);
	background: var(--bg-default-color);
	border: 1px solid var(--border-color);
	border-radius: 3px;
	padding: 1px 5px;
}
.preview-sev {
	font-size: 0.65rem;
	font-weight: 600;
	text-transform: uppercase;
	padding: 1px 6px;
	border-radius: 3px;
	border: 1px solid var(--border-color);
	color: var(--fg-secondary-color);
}
.preview-sev-low {
	color: var(--info-color);
	border-color: rgba(var(--info-color-rgb) / 0.4);
	background: rgba(var(--info-color-rgb) / 0.1);
}
.preview-sev-medium {
	color: var(--warning-color);
	border-color: rgba(var(--warning-color-rgb) / 0.4);
	background: rgba(var(--warning-color-rgb) / 0.1);
}
.preview-sev-high {
	color: var(--error-color);
	border-color: rgba(var(--error-color-rgb) / 0.4);
	background: rgba(var(--error-color-rgb) / 0.1);
}
.preview-sev-critical {
	color: var(--error-color);
	border-color: var(--error-color);
	background: rgba(var(--error-color-rgb) / 0.18);
}
</style>
