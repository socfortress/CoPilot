<template>
	<div class="coverage-gaps-index flex flex-col gap-4">
		<!-- Title row + framing copy -->
		<div class="flex flex-wrap items-end justify-between gap-3">
			<div class="flex flex-col gap-1">
				<h3 class="m-0 text-lg font-semibold">Coverage Gaps</h3>
				<p class="text-secondary m-0 max-w-3xl text-sm">
					MITRE ATT&amp;CK techniques no rule covers — across both the CoPilot Searches corpus and the Wazuh
					ruleset. Sub-techniques are collapsed into their parents (coverage of T1059.001 counts as coverage
					for T1059). Use this list to spot where new detection authoring would expand your coverage.
				</p>
			</div>
			<Badge type="splitted" color="primary">
				<template #label>Showing</template>
				<template #value>{{ filteredGaps.length }} / {{ gaps.length }}</template>
			</Badge>
		</div>

		<!-- COVERAGE HERO STATS - tiles using the shared CatalogStatTile so
		     visual identity matches the catalog header. -->
		<div v-if="!loading" class="gaps-stats-grid">
			<CatalogStatTile
				label="Coverage"
				:value="`${coverage_pct}%`"
				:icon="ShieldIcon"
				:accent="coveragePctAccent"
				sub="Across both corpora"
			/>
			<CatalogStatTile
				label="Covered techniques"
				:value="covered_count"
				:icon="CoveredIcon"
				accent="success"
				:sub="`of ${total_techniques} total`"
			/>
			<CatalogStatTile
				label="Gaps"
				:value="gap_count"
				:icon="GapsIcon"
				accent="danger"
				sub="Techniques with no rule"
			/>
		</div>

		<n-input v-model:value="filter" size="medium" placeholder="Filter by technique ID, name, or tactic…" clearable>
			<template #prefix><Icon name="carbon:search" /></template>
		</n-input>

		<n-spin :show="loading">
			<n-data-table :columns :data="filteredGaps" :loading size="small" :pagination class="catalog-table" />
		</n-spin>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { CatalogCoverageGapRow } from "@/types/detectionCatalog.d"
import { NDataTable, NInput, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import CatalogStatTile from "./CatalogStatTile.vue"

const message = useMessage()

const gaps = ref<CatalogCoverageGapRow[]>([])
const gap_count = ref(0)
const total_techniques = ref(0)
const covered_count = ref(0)
const coverage_pct = ref(0)

const loading = ref(false)
const filter = ref("")

const ShieldIcon = "carbon:shield-check"
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

// Color the Coverage tile by quality bucket — green high, red low. Makes the
// tile a glanceable health indicator.
const coveragePctAccent = computed<"success" | "warning" | "danger">(() => {
	if (coverage_pct.value >= 70) return "success"
	if (coverage_pct.value >= 40) return "warning"
	return "danger"
})

const columns: DataTableColumns<CatalogCoverageGapRow> = [
	{
		title: "Technique ID",
		key: "technique_id",
		width: 140,
		sorter: (a, b) => a.technique_id.localeCompare(b.technique_id),
		render: row =>
			row.url ? (
				<a href={row.url} target="_blank" rel="noopener" class="technique-link">
					{row.technique_id}
					<Icon name="carbon:launch" size={11} />
				</a>
			) : (
				<span class="text-secondary font-mono text-xs">{row.technique_id}</span>
			)
	},
	{
		title: "Technique",
		key: "technique_name",
		sorter: (a, b) => a.technique_name.localeCompare(b.technique_name),
		render: row => <span class="font-medium">{row.technique_name}</span>
	},
	{
		title: "Tactics",
		key: "tactics",
		render: row =>
			row.tactics.length ? (
				<div class="flex flex-wrap gap-1">
					{row.tactics.map(t => (
						<span key={t} class="chip chip-tactic">
							{t.toUpperCase()}
						</span>
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
			message.error(err.response?.data?.detail || err.response?.data?.message || "Failed to load coverage gaps")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(load)
</script>

<style scoped lang="scss">
.gaps-stats-grid {
	display: grid;
	gap: 12px;
	grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

/* Catalog table reuse */
.catalog-table :deep(.n-data-table-th) {
	background-color: var(--bg-secondary-color);
	font-weight: 600;
	font-size: 12px;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--fg-secondary-color);
}
.catalog-table :deep(.n-data-table-tr) {
	transition: background-color 0.15s var(--bezier-ease);
}
.catalog-table :deep(.n-data-table-tr:hover) {
	background-color: rgba(var(--primary-color-rgb) / 0.04);
}
.catalog-table :deep(.n-data-table-td) {
	padding: 10px 12px;
}

:deep(.technique-link) {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	font-family: var(--font-family-mono);
	font-size: 0.78rem;
	font-weight: 500;
	color: var(--primary-color);
	transition: color 0.15s var(--bezier-ease);

	&:hover {
		text-decoration: underline;
	}
}

:deep(.chip) {
	display: inline-flex;
	align-items: center;
	padding: 2px 8px;
	font-size: 0.72rem;
	font-weight: 500;
	line-height: 1.4;
	border-radius: 6px;
	border: 1px solid transparent;
	white-space: nowrap;
}
:deep(.chip-tactic) {
	color: var(--warning-color);
	background-color: rgba(var(--warning-color-rgb) / 0.08);
	border-color: rgba(var(--warning-color-rgb) / 0.2);
	font-weight: 600;
	letter-spacing: 0.04em;
}
</style>
