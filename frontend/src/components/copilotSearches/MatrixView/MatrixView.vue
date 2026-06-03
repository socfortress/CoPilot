<template>
	<div class="flex flex-col gap-3">
		<MatrixViewToolbar
			v-model:search-query="searchQuery"
			v-model:show-filters="showFilters"
			v-model:selected-platform="selectedPlatform"
			v-model:selected-severity="selectedSeverity"
			v-model:selected-status="selectedStatus"
			v-model:has-graylog-filter="hasGraylogFilter"
			v-model:only-covered="onlyCovered"
			:coverage
			:refreshing
			@export-csv="exportCoverageCsv"
			@refresh="handleRefresh"
			@reset-filters="resetFilters"
		/>

		<MatrixViewLegend :coverage />

		<MatrixViewGrid
			v-model:expanded="expanded"
			:loading
			:coverage
			:filtered-tactics
			:rules-index
			@clear-filters="clearAllFilters"
			@open-technique="openTechnique"
			@open-sub-technique="openSubTechnique"
			@open-rule="openQuickRule"
		/>

		<n-drawer
			v-model:show="drawerOpen"
			:width="techniqueDrawerWidth"
			placement="right"
			display-directive="show"
			class="max-w-[92vw]"
			@update:show="onDrawerToggle"
		>
			<n-drawer-content :title="techniqueDrawerTitle" closable :native-scrollbar="false">
				<TechniqueDetails
					v-if="selectedTechnique"
					:technique="selectedTechnique"
					:sub-technique="selectedSubTechnique"
				/>
			</n-drawer-content>
		</n-drawer>

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
import { useLocalStorage, useWindowSize, watchDebounced } from "@vueuse/core"
import { saveAs } from "file-saver"
import { NDrawer, NDrawerContent, NModal, useMessage } from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import RuleCardContent from "../RuleCardContent.vue"
import TechniqueDetails from "../TechniqueDetails.vue"
import MatrixViewGrid from "./MatrixViewGrid.vue"
import MatrixViewLegend from "./MatrixViewLegend.vue"
import MatrixViewToolbar from "./MatrixViewToolbar.vue"
import "./matrix-coverage.css"

const route = useRoute()
const router = useRouter()
const message = useMessage()

const { width: viewportWidth } = useWindowSize()

const loading = ref(false)
const refreshing = ref(false)
const coverage = ref<MitreCoverageResponse | null>(null)
const onlyCovered = useLocalStorage("copilot-searches/matrix/only-covered", false)
const searchQuery = ref("")
const expanded = useLocalStorage<Record<string, boolean>>("copilot-searches/matrix/expanded", {})

const selectedPlatform = ref<PlatformFilter | null>(null)
const selectedSeverity = ref<RuleSeverity | null>(null)
const selectedStatus = ref<RuleStatus | null>(null)
const hasGraylogFilter = ref(false)
const showFilters = ref(false)

const drawerOpen = ref(false)
const selectedTechnique = ref<MitreTechnique | null>(null)
const selectedSubTechnique = ref<MitreSubTechnique | null>(null)
const selectedTacticIdForDeepLink = ref<string | null>(null)

const techniqueDrawerTitle = computed(() => {
	if (!selectedTechnique.value) return "Technique"
	if (selectedSubTechnique.value) {
		return `${selectedSubTechnique.value.id} ${selectedSubTechnique.value.name}`
	}
	return `${selectedTechnique.value.id} ${selectedTechnique.value.name}`
})

const techniqueDrawerWidth = computed(() => Math.min(820, viewportWidth.value - 40))

// Direct-from-hover rule modal
const quickRuleOpen = ref(false)
const quickRuleId = ref<string | null>(null)
function openQuickRule(ruleId: string) {
	quickRuleId.value = ruleId
	quickRuleOpen.value = true
}

const ready = ref(false)

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
	const stamp = new Date().toISOString().slice(0, 10)
	saveAs(new Blob([csv], { type: "text/csv;charset=utf-8;" }), `copilot-mitre-coverage-${stamp}.csv`)
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
</script>
