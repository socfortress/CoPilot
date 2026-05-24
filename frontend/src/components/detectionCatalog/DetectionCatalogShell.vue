<template>
	<div class="flex flex-col gap-6">
		<!-- HERO HEADER ------------------------------------------------------
		     Title row + descriptive blurb + responsive grid of stat tiles.
		     The tiles double as navigation: click "Stories" tile → jump to
		     Stories tab; click "Wazuh rules" → Wazuh tab; etc. The whole
		     header is hidden when a story is open so the detail page has
		     room to breathe.
		-->
		<header v-if="!openStoryName" class="@container flex flex-col gap-4">
			<div class="flex flex-wrap items-end justify-between gap-3">
				<div class="flex flex-col gap-1">
					<div class="flex items-center gap-3">
						<Icon :name="CatalogIcon" :size="22" />
						<h2 class="m-0 text-2xl font-semibold">Detections Catalog</h2>
					</div>
					<p class="text-sm">
						Discovery surface for the CoPilot detection corpus and the Wazuh ruleset. Browse the CoPilot
						Searches grouped by analytic story, inspect every Wazuh rule shipped by the manager, see your
						MITRE coverage gaps, and pivot by compliance framework.
					</p>
				</div>
				<div v-if="stats" class="text-tertiary flex items-center gap-2 text-xs">
					<n-spin v-if="loadingStats" size="small" />
					<span v-else>
						Data refreshed
						<span v-if="stats.last_refresh">{{ formatRelativeTime(stats.last_refresh) }}</span>
						<span v-else>just now</span>
					</span>
				</div>
			</div>

			<div class="grid grid-cols-1 gap-4 @md:grid-cols-2 @2xl:grid-cols-3 @7xl:grid-cols-6">
				<CardLink
					v-for="tile in headerStatTiles"
					:key="tile.id"
					:title="tile.label"
					:value="tile.value"
					:icon="tile.icon"
					:subtitle="tile.sub"
					:clickable="!!tile.to"
					@click="onHeaderTileClick(tile)"
				/>
			</div>
		</header>

		<!-- TAB STRIP --------------------------------------------------------
		     URL-synced via ?tab=<key>. When a story detail is open we hide
		     the tabs entirely — that's its own dedicated surface.
		-->
		<n-tabs v-if="!openStoryName" :value="activeTab" type="line" animated @update:value="setTab">
			<n-tab-pane name="stories">
				<template #tab>
					<div class="flex items-center gap-2">
						<Icon :name="StoryIcon" :size="15" />
						CoPilot Searches
					</div>
				</template>
				<StoriesIndex @open-story="openStory" />
			</n-tab-pane>
			<n-tab-pane name="wazuh">
				<template #tab>
					<div class="flex items-center gap-2">
						<Icon :name="WazuhIcon" :size="15" />
						Wazuh Rules
					</div>
				</template>
				<WazuhRulesIndex />
			</n-tab-pane>
			<n-tab-pane name="gaps">
				<template #tab>
					<div class="flex items-center gap-2">
						<Icon :name="GapsIcon" :size="15" />
						Coverage Gaps
					</div>
				</template>
				<CoverageGapsIndex />
			</n-tab-pane>
			<n-tab-pane name="compliance">
				<template #tab>
					<div class="flex items-center gap-2">
						<Icon :name="ComplianceIcon" :size="15" />
						Compliance
					</div>
				</template>
				<ComplianceIndex />
			</n-tab-pane>
		</n-tabs>

		<!-- Full-pane story detail surface. -->
		<StoryDetail v-else :story-name="openStoryName" @back="closeStory" />
	</div>
</template>

<script setup lang="ts">
import type { CatalogStatsResponse } from "@/types/detectionCatalog.d"
import { NSpin, NTabPane, NTabs } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import CardLink from "@/components/common/cards/CardLink.vue"
import Icon from "@/components/common/Icon.vue"
import dayjs from "@/utils/dayjs"
import ComplianceIndex from "./ComplianceIndex.vue"
import CoverageGapsIndex from "./CoverageGapsIndex.vue"
import StoriesIndex from "./StoriesIndex.vue"
import StoryDetail from "./StoryDetail.vue"
import WazuhRulesIndex from "./WazuhRulesIndex.vue"

type TabKey = "stories" | "wazuh" | "gaps" | "compliance"

interface HeaderStatTileDef {
	id: string
	label: string
	icon?: string
	sub?: string
	to?: TabKey
	value: (stats: CatalogStatsResponse | null) => number
	show?: (stats: CatalogStatsResponse | null) => boolean
}

interface HeaderStatTile {
	id: string
	label: string
	sub?: string
	icon?: string
	to?: TabKey
	value: string
}

const route = useRoute()
const router = useRouter()

const openStoryName = ref<string | null>(null)
const stats = ref<CatalogStatsResponse | null>(null)
const loadingStats = ref(false)

// Carbon icons across the catalog. Centralized here so adding a new tile/
// tab is one constant + one mount, not a hunt across files.
const CatalogIcon = "carbon:catalog"
const DetectionIcon = "carbon:radar"
const StoryIcon = "carbon:book"
const WazuhIcon = "carbon:document-security"
const GapsIcon = "carbon:warning-square"
const ComplianceIcon = "carbon:certificate-check"
const TacticIcon = "carbon:flag"
const DataSourceIcon = "carbon:data-base"
const ProductIcon = "carbon:cube"

const HEADER_STAT_TILE_DEFS: HeaderStatTileDef[] = [
	{
		id: "detections",
		label: "Detections",
		icon: DetectionIcon,
		sub: "CoPilot Searches",
		to: "stories",
		value: s => s?.detection_count ?? 0
	},
	{
		id: "stories",
		label: "Stories",
		icon: StoryIcon,
		sub: "Analytic stories",
		to: "stories",
		value: s => s?.story_count ?? 0
	},
	{
		id: "wazuh-rules",
		label: "Wazuh rules",
		icon: WazuhIcon,
		sub: "From Wazuh Manager",
		to: "wazuh",
		show: s => !!s?.wazuh_available,
		value: s => s?.wazuh_rule_count ?? 0
	},
	{
		id: "mitre-tactics",
		label: "MITRE tactics",
		icon: TacticIcon,
		sub: "Covered",
		value: s => s?.tactic_count ?? 0
	},
	{
		id: "data-sources",
		label: "Data sources",
		icon: DataSourceIcon,
		sub: "Distinct sources",
		value: s => s?.data_source_count ?? 0
	},
	{
		id: "products",
		label: "Products",
		icon: ProductIcon,
		sub: "Distinct products",
		value: s => s?.product_count ?? 0
	}
]

const headerStatTiles = computed<HeaderStatTile[]>(() =>
	HEADER_STAT_TILE_DEFS.filter(tile => !tile.show || tile.show(stats.value)).map(tile => ({
		id: tile.id,
		label: tile.label,
		sub: tile.sub,
		icon: tile.icon,
		to: tile.to,
		value: tile.value(stats.value).toLocaleString()
	}))
)

function onHeaderTileClick(tile: HeaderStatTile) {
	if (tile.to) setTab(tile.to)
}

const activeTab = computed<TabKey>(() => {
	const t = route.query.tab
	if (t === "wazuh" || t === "gaps" || t === "compliance") return t
	return "stories"
})

function setTab(next: string) {
	// `replace` so tab switching doesn't pile up history entries.
	const nextQuery = { ...route.query }
	if (next === "stories") delete nextQuery.tab
	else nextQuery.tab = next
	router.replace({ query: nextQuery })
}

function loadStats() {
	loadingStats.value = true
	Api.detectionCatalog
		.getStats()
		.then(res => {
			if (res.data?.success) stats.value = res.data
		})
		.catch(() => {
			/* Stats are best-effort cosmetic; don't toast an error. */
		})
		.finally(() => {
			loadingStats.value = false
		})
}

function openStory(name: string) {
	openStoryName.value = name
	const next = { ...route.query, story: name }
	// `push` so browser-back lands on /detection-catalog (the index) instead
	// of skipping past the catalog entirely.
	router.push({ query: next })
}

function closeStory() {
	openStoryName.value = null
	const next = { ...route.query }
	delete next.story
	router.replace({ query: next })
}

// Deep-link support: ?story=<name> opens that story on mount + when the URL
// changes (back/forward).
watch(
	() => route.query.story,
	q => {
		openStoryName.value = typeof q === "string" ? q : null
	},
	{ immediate: true }
)

function formatRelativeTime(iso: string): string {
	return dayjs(iso).fromNow()
}

onBeforeMount(loadStats)
</script>
