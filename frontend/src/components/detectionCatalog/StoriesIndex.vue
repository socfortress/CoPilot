<template>
	<div class="stories-index flex flex-col gap-4">
		<!-- TOOLBAR ----------------------------------------------------------
		     Search + visible-count + framing copy. Same layout pattern the
		     Wazuh and Coverage Gaps tabs use, so the analyst's eye doesn't
		     have to re-learn the tab on each switch.
		-->
		<div class="flex flex-wrap items-end justify-between gap-3">
			<div class="flex flex-col gap-1">
				<h3 class="m-0 text-lg font-semibold">Analytic Stories</h3>
				<p class="text-secondary m-0 text-sm">
					Each story is a threat narrative covered by one or more CoPilot Searches detections. Click a row to
					see the member detections, data sources, and references.
				</p>
			</div>
			<Badge type="splitted" color="primary">
				<template #label>Showing</template>
				<template #value>{{ filteredStories.length }} / {{ stories.length }}</template>
			</Badge>
		</div>

		<n-input
			v-model:value="filter"
			size="medium"
			placeholder="Filter by story name, data source, tactic, or product…"
			clearable
		>
			<template #prefix><Icon name="carbon:search" /></template>
		</n-input>

		<n-spin :show="loading">
			<n-data-table
				:columns
				:data="filteredStories"
				:loading
				size="small"
				:row-props
				:pagination
				class="catalog-table stories-table"
			/>
		</n-spin>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { CatalogStoryRow } from "@/types/detectionCatalog.d"
import { NDataTable, NInput, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{ (e: "open-story", name: string): void }>()

const message = useMessage()
const stories = ref<CatalogStoryRow[]>([])
const loading = ref(false)
const filter = ref("")

const pagination = {
	pageSize: 25,
	pageSizes: [10, 25, 50, 100],
	showSizePicker: true
}

const filteredStories = computed<CatalogStoryRow[]>(() => {
	const q = filter.value.trim().toLowerCase()
	if (!q) return stories.value
	return stories.value.filter(s =>
		[s.name, ...(s.data_sources || []), ...(s.tactics || []), ...(s.products || [])]
			.join(" ")
			.toLowerCase()
			.includes(q)
	)
})

function rowProps(row: CatalogStoryRow) {
	return {
		class: "catalog-table-row",
		style: "cursor: pointer;",
		onClick: () => emit("open-story", row.name)
	}
}

const columns: DataTableColumns<CatalogStoryRow> = [
	{
		title: "Story",
		key: "name",
		sorter: (a, b) => a.name.localeCompare(b.name),
		render: row => (
			<div class="flex flex-col gap-1 py-1">
				<div class="leading-snug font-semibold">{row.name}</div>
				<div class="text-tertiary text-xs">
					{`${row.detection_count} detection`}
					{row.detection_count === 1 ? "" : "s"}
				</div>
			</div>
		)
	},
	{
		title: "Data sources",
		key: "data_sources",
		render: row =>
			row.data_sources.length ? (
				<div class="flex flex-wrap gap-1">
					{row.data_sources.slice(0, 4).map(s => (
						<span key={s} class="chip chip-info">
							{s}
						</span>
					))}
					{row.data_sources.length > 4 && (
						<span class="chip chip-muted">{`+${row.data_sources.length - 4}`}</span>
					)}
				</div>
			) : (
				<span class="text-tertiary text-xs">—</span>
			)
	},
	{
		title: "MITRE tactics",
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
	},
	{
		title: "Products",
		key: "products",
		width: 180,
		render: row =>
			row.products.length ? (
				<div class="flex flex-wrap gap-1">
					{row.products.map(p => (
						<span key={p} class="chip chip-product">
							{p}
						</span>
					))}
				</div>
			) : (
				<span class="text-tertiary text-xs">—</span>
			)
	},
	{
		title: "Last updated",
		key: "date",
		width: 130,
		sorter: (a, b) => (a.date || "").localeCompare(b.date || ""),
		render: row =>
			row.date ? (
				<span class="text-secondary font-mono text-xs">{row.date}</span>
			) : (
				<span class="text-tertiary text-xs">—</span>
			)
	}
]

function load() {
	loading.value = true
	Api.detectionCatalog
		.listStories()
		.then(res => {
			if (res.data?.success) stories.value = res.data.stories || []
			else message.warning(res.data?.message || "Failed to load analytic stories")
		})
		.catch(err => {
			message.error(err.response?.data?.message || "Failed to load analytic stories")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(load)
</script>

<style scoped lang="scss">
/* Catalog-wide table styling. Defined here but reused via the .catalog-table
   class on all four tab tables — keeps the visual identity consistent across
   Stories / Wazuh / Gaps / Compliance without a separate stylesheet. */
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

/* Chip mini-component — used inline in render functions. Three variants
   so different facets (data sources / tactics / products) have visually
   distinct treatment without inventing custom NTag colors. */
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
:deep(.chip-info) {
	color: var(--primary-color);
	background-color: rgba(var(--primary-color-rgb) / 0.08);
	border-color: rgba(var(--primary-color-rgb) / 0.18);
}
:deep(.chip-tactic) {
	color: var(--warning-color);
	background-color: rgba(var(--warning-color-rgb) / 0.08);
	border-color: rgba(var(--warning-color-rgb) / 0.2);
	font-weight: 600;
	letter-spacing: 0.04em;
}
:deep(.chip-product) {
	color: var(--fg-default-color);
	background-color: var(--bg-secondary-color);
	border-color: var(--border-color);
}
:deep(.chip-muted) {
	color: var(--fg-secondary-color);
	background-color: rgba(var(--border-color-rgb) / 0.15);
	border-color: var(--border-color);
}
</style>
