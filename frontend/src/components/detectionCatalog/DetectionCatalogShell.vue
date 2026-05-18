<template>
	<div class="detection-catalog-shell flex flex-col gap-4">
		<!-- Page header with stats strip -->
		<div class="flex flex-col gap-2">
			<div class="flex flex-wrap items-baseline gap-x-4 gap-y-1">
				<h2>Detections Catalog</h2>
				<n-spin v-if="loadingStats" size="small" />
				<div v-else-if="stats" class="text-secondary text-xs">
					<strong>{{ stats.detection_count }}</strong>
					{{ pluralize("detection", stats.detection_count) }} ·
					<strong>{{ stats.story_count }}</strong>
					{{ pluralize("story", stats.story_count, "stories") }} ·
					<strong>{{ stats.tactic_count }}</strong>
					{{ pluralize("tactic", stats.tactic_count) }} ·
					<strong>{{ stats.data_source_count }}</strong>
					{{ pluralize("data source", stats.data_source_count) }} ·
					<strong>{{ stats.product_count }}</strong>
					{{ pluralize("product", stats.product_count) }}
					<template v-if="stats.wazuh_available">
						· <strong>{{ stats.wazuh_rule_count }}</strong>
						{{ pluralize("Wazuh rule", stats.wazuh_rule_count) }}
					</template>
				</div>
			</div>
			<p class="text-secondary text-sm">
				Discovery surface for the CoPilot detection corpus and the Wazuh ruleset. Browse by
				analytic story to see CoPilot coverage for a given threat, or open the Wazuh Rules tab
				to inspect every rule shipped by the Wazuh Manager.
			</p>
		</div>

		<!-- Tab strip. Three browse modes:
		     - "Analytic Stories" → CoPilot Searches rules grouped by story (the original v1)
		     - "Wazuh Rules"      → flat searchable grid over the Wazuh Manager ruleset
		     - "Coverage Gaps"    → MITRE techniques no rule (either corpus) addresses
		     Tab state is mirrored to `?tab=` so deep-links and back/forward preserve which
		     mode the user was in. When a story is open we DON'T render the tabs — the
		     story detail page is its own dedicated surface and showing tabs there would
		     imply switching modes is meaningful, which it isn't. -->
		<n-tabs
			v-if="!openStoryName"
			:value="activeTab"
			type="line"
			animated
			@update:value="setTab"
		>
			<n-tab-pane name="stories" tab="Analytic Stories">
				<StoriesIndex @open-story="openStory" />
			</n-tab-pane>
			<n-tab-pane name="wazuh" tab="Wazuh Rules">
				<WazuhRulesIndex />
			</n-tab-pane>
			<n-tab-pane name="gaps" tab="Coverage Gaps">
				<CoverageGapsIndex />
			</n-tab-pane>
		</n-tabs>

		<!-- Story detail view. Lives outside the tab strip on purpose — it's a
		     full-pane child surface, not a tab content. -->
		<StoryDetail v-else :story-name="openStoryName" @back="closeStory" />
	</div>
</template>

<script setup lang="ts">
import type { CatalogStatsResponse } from "@/types/detectionCatalog.d"
import { onBeforeMount, ref, watch, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import CoverageGapsIndex from "./CoverageGapsIndex.vue"
import StoriesIndex from "./StoriesIndex.vue"
import StoryDetail from "./StoryDetail.vue"
import WazuhRulesIndex from "./WazuhRulesIndex.vue"
import { NSpin, NTabs, NTabPane } from "naive-ui"

type TabKey = "stories" | "wazuh" | "gaps"

const route = useRoute()
const router = useRouter()

const openStoryName = ref<string | null>(null)
const stats = ref<CatalogStatsResponse | null>(null)
const loadingStats = ref(false)

// Active tab derived from the URL so back/forward and direct links work.
// Anything that isn't a recognized tab key falls through to "stories" — the default.
const activeTab = computed<TabKey>(() => {
	const t = route.query.tab
	if (t === "wazuh" || t === "gaps") return t
	return "stories"
})

function pluralize(singular: string, count: number, plural?: string): string {
	if (count === 1) return singular
	return plural ?? `${singular}s`
}

function setTab(next: TabKey) {
	// Use `replace` (not `push`): switching tabs is a mode change within the
	// same page, not a navigation. Browser-back should still go to whatever
	// was open before the catalog, not bounce between tabs.
	const nextQuery = { ...route.query }
	if (next === "stories") {
		delete nextQuery.tab
	} else {
		nextQuery.tab = next
	}
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
			// Stats are best-effort cosmetic; don't surface an error here.
		})
		.finally(() => {
			loadingStats.value = false
		})
}

function openStory(name: string) {
	openStoryName.value = name
	const next = { ...route.query, story: name }
	// `push` (not `replace`) so opening a story creates a real history entry.
	// That way browser-back from /detection-catalog?story=Foo lands on
	// /detection-catalog (the index), not on whatever was open before the
	// catalog. closeStory() below intentionally uses `replace` so clicking
	// the in-app "All Stories" button doesn't pollute history with a second
	// /detection-catalog entry.
	router.push({ query: next })
}

function closeStory() {
	openStoryName.value = null
	const next = { ...route.query }
	delete next.story
	router.replace({ query: next })
}

// Deep-link support: ?story=<name> opens that story on mount + when the URL changes
// (back/forward navigation). Kept self-contained so the catalog feels like its own
// little SPA without needing additional routes registered.
watch(
	() => route.query.story,
	q => {
		const v = typeof q === "string" ? q : null
		openStoryName.value = v
	},
	{ immediate: true }
)

onBeforeMount(loadStats)
</script>
