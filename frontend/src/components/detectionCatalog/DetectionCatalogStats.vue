<template>
	<div class="@container flex flex-col gap-4">
		<div class="flex items-center justify-end gap-2">
			<span v-if="stats" class="text-tertiary text-xs">
				Last refreshed
				<span v-if="stats.last_refresh">{{ formatRelativeTime(stats.last_refresh) }}</span>
				<span v-else>just now</span>
			</span>
			<n-button :loading="loadingStats" size="tiny" secondary @click="loadStats">
				<template #icon><Icon :name="RefreshIcon" :size="15" /></template>
				Refresh
			</n-button>
		</div>

		<n-spin :show="loadingStats">
			<div class="grid grid-cols-1 gap-4 @md:grid-cols-2 @2xl:grid-cols-3 @7xl:grid-cols-6">
				<CardLink
					v-for="tile in headerStatTiles"
					:key="tile.id"
					:title="tile.label"
					:value="tile.value"
					:icon="tile.icon"
					:subtitle="tile.sub"
				/>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CatalogStatsResponse } from "@/types/detectionCatalog.d"
import { NButton, NSpin } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardLink from "@/components/common/cards/CardLink.vue"
import Icon from "@/components/common/Icon.vue"
import dayjs from "@/utils/dayjs"

interface HeaderStatTileDef {
	id: string
	label: string
	icon?: string
	sub?: string
	value: (stats: CatalogStatsResponse | null) => number
	show?: (stats: CatalogStatsResponse | null) => boolean
}

interface HeaderStatTile {
	id: string
	label: string
	sub?: string
	icon?: string
	value: string
}

const stats = ref<CatalogStatsResponse | null>(null)
const loadingStats = ref(false)

const DetectionIcon = "carbon:radar"
const StoryIcon = "carbon:book"
const WazuhIcon = "carbon:document-security"
const TacticIcon = "carbon:flag"
const DataSourceIcon = "carbon:data-base"
const ProductIcon = "carbon:cube"
const RefreshIcon = "carbon:renew"

const HEADER_STAT_TILE_DEFS: HeaderStatTileDef[] = [
	{
		id: "detections",
		label: "Detections",
		icon: DetectionIcon,
		sub: "CoPilot Searches",
		value: s => s?.detection_count ?? 0
	},
	{
		id: "stories",
		label: "Stories",
		icon: StoryIcon,
		sub: "Analytic stories",
		value: s => s?.story_count ?? 0
	},
	{
		id: "wazuh-rules",
		label: "Wazuh rules",
		icon: WazuhIcon,
		sub: "From Wazuh Manager",
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
		value: tile.value(stats.value).toLocaleString()
	}))
)

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

function formatRelativeTime(iso: string): string {
	return dayjs(iso).fromNow()
}

onBeforeMount(loadStats)
</script>
