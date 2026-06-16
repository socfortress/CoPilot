<template>
	<div class="@container flex flex-col gap-4">
		<!-- Title row + framing copy -->
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-semibold">Coverage Gaps</h3>
			<p class="text-secondary text-sm">
				MITRE ATT&amp;CK techniques no rule covers — across both the CoPilot Searches corpus and the Wazuh
				ruleset. Sub-techniques are collapsed into their parents (coverage of T1059.001 counts as coverage for
				T1059). Use this list to spot where new detection authoring would expand your coverage.
			</p>
		</div>

		<!-- COVERAGE HERO STATS - same CardLink pattern used by the catalog header. -->
		<div v-if="!loading" class="grid grid-cols-1 gap-4 @2xl:grid-cols-3">
			<CardLink
				v-for="tile in coverageStatTiles"
				:key="tile.id"
				:title="tile.label"
				:value="tile.value"
				:icon-left="tile.icon"
				:color="tile.color"
				:subtitle="tile.sub"
				size="small"
			/>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			<n-input
				v-model:value="filter"
				size="small"
				placeholder="Filter by technique ID, name, or tactic…"
				clearable
				class="min-w-80 flex-1"
			>
				<template #prefix><Icon name="carbon:search" /></template>
			</n-input>

			<Badge type="splitted" color="primary" class="shrink-0">
				<template #label>Showing</template>
				<template #value>{{ filteredGaps.length }} / {{ gaps.length }}</template>
			</Badge>
		</div>

		<n-data-table :columns :data="filteredGaps" :loading size="small" :pagination :scroll-x="100" />
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { ApiError } from "@/types/common"
import type { CatalogCoverageGapRow } from "@/types/detectionCatalog.d"
import { NButton, NDataTable, NInput, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

interface CoverageStatTile {
	id: string
	label: string
	value: string
	icon: string
	sub: string
	color: CardLinkColor
}

const message = useMessage()

const gaps = ref<CatalogCoverageGapRow[]>([])
const gap_count = ref(0)
const total_techniques = ref(0)
const covered_count = ref(0)
const coverage_pct = ref(0)

const loading = ref(false)
const filter = ref("")

const ShieldIcon = "carbon:ibm-cloud-security-groups"
const CoveredIcon = "carbon:checkmark-outline"
const GapsIcon = "carbon:warning-square"

const pagination = {
	pageSize: 25,
	pageSizes: [10, 25, 50, 100],
	showSizePicker: true
}

const filteredGaps = computed<CatalogCoverageGapRow[]>(() => {
	const q = filter.value.trim().toLowerCase()
	if (!q) return gaps.value
	return gaps.value.filter(g =>
		[g.technique_id, g.technique_name, ...(g.tactics || [])].join(" ").toLowerCase().includes(q)
	)
})

const coverageStatTiles = computed<CoverageStatTile[]>(() => [
	{
		id: "coverage",
		label: "Coverage",
		value: `${coverage_pct.value}%`,
		icon: ShieldIcon,
		sub: "Across both corpora",
		color: "warning"
	},
	{
		id: "covered-techniques",
		label: "Covered techniques",
		value: covered_count.value.toLocaleString(),
		icon: CoveredIcon,
		sub: `of ${total_techniques.value.toLocaleString()} total`,
		color: "success"
	},
	{
		id: "gaps",
		label: "Gaps",
		value: gap_count.value.toLocaleString(),
		icon: GapsIcon,
		sub: "Techniques with no rule",
		color: "danger"
	}
])

const columns: DataTableColumns<CatalogCoverageGapRow> = [
	{
		title: "Technique ID",
		key: "technique_id",
		width: 150,
		fixed: "left",
		sorter: (a, b) => a.technique_id.localeCompare(b.technique_id),
		render: row =>
			row.url ? (
				<NButton
					tag="a"
					// @ts-expect-error tag="a" forwards native anchor attrs omitted from ButtonProps
					rel="noopener"
					href={row.url}
					target="_blank"
					size="tiny"
					icon-placement="right"
					secondary
					type="primary"
					v-slots={{
						icon: () => <Icon name="carbon:launch" />
					}}
				>
					{row.technique_id}
				</NButton>
			) : (
				<span class="text-secondary font-mono text-xs">{row.technique_id}</span>
			)
	},
	{
		title: "Technique",
		key: "technique_name",
		width: 400,
		sorter: (a, b) => a.technique_name.localeCompare(b.technique_name)
	},
	{
		title: "Tactics",
		key: "tactics",
		minWidth: 300,
		render: row =>
			row.tactics.length ? (
				<div class="flex flex-wrap gap-1">
					{row.tactics.map(t => (
						<NTag key={t} type="warning" size="small">
							{t.toUpperCase()}
						</NTag>
					))}
				</div>
			) : (
				<span class="text-tertiary text-xs">—</span>
			)
	}
]

function load() {
	loading.value = true
	Api.detectionCatalog
		.listCoverageGaps()
		.then(res => {
			if (res.data?.success) {
				gaps.value = res.data.gaps || []
				gap_count.value = res.data.gap_count
				total_techniques.value = res.data.total_techniques
				covered_count.value = res.data.covered_count
				coverage_pct.value = res.data.coverage_pct
			} else {
				message.warning(res.data?.message || "Failed to load coverage gaps")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to load coverage gaps")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(load)
</script>
