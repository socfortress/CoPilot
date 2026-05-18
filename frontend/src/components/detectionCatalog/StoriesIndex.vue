<template>
	<div class="stories-index flex flex-col gap-3">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h3>Analytic Stories</h3>
			<div class="text-tertiary text-xs">
				<strong>{{ filteredStories.length }}</strong>
				/ {{ stories.length }}
			</div>
		</div>

		<n-input v-model:value="filter" size="small" placeholder="Filter Table Values" clearable>
			<template #prefix><Icon name="carbon:search" /></template>
		</n-input>

		<n-spin :show="loading">
			<n-data-table
				:columns="columns"
				:data="filteredStories"
				:loading
				size="small"
				:row-props="rowProps"
				class="stories-table"
			/>
		</n-spin>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { CatalogStoryRow } from "@/types/detectionCatalog.d"
import { NDataTable, NInput, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{
	(e: "open-story", name: string): void
}>()


const message = useMessage()
const stories = ref<CatalogStoryRow[]>([])
const loading = ref(false)
const filter = ref("")

const filteredStories = computed<CatalogStoryRow[]>(() => {
	const q = filter.value.trim().toLowerCase()
	if (!q) return stories.value
	return stories.value.filter(s => {
		const haystack = [
			s.name,
			...(s.data_sources || []),
			...(s.tactics || []),
			...(s.products || [])
		]
			.join(" ")
			.toLowerCase()
		return haystack.includes(q)
	})
})

// Splunk-style row click navigates to the story detail page. We use row-props
// rather than per-cell click handlers so the whole row is the affordance.
function rowProps(row: CatalogStoryRow) {
	return {
		style: "cursor: pointer;",
		onClick: () => emit("open-story", row.name)
	}
}

const columns: DataTableColumns<CatalogStoryRow> = [
	{
		title: "Name",
		key: "name",
		sorter: (a, b) => a.name.localeCompare(b.name),
		render: row => (
			<div class="flex items-center gap-2">
				<span class="font-medium">{row.name}</span>
				<NTag size="tiny" bordered={false}>
					{`${row.detection_count} detection${row.detection_count === 1 ? "" : "s"}`}
				</NTag>
			</div>
		)
	},
	{
		title: "Data Sources",
		key: "data_sources",
		render: row =>
			row.data_sources.length
				? row.data_sources.map(s => (
						<NTag key={s} size="tiny" type="info" bordered={false} class="mr-1 mb-1">
							{s}
						</NTag>
					))
				: <em class="text-tertiary">—</em>
	},
	{
		title: "Tactics",
		key: "tactics",
		render: row =>
			row.tactics.length
				? row.tactics.map(t => (
						<NTag key={t} size="tiny" bordered={false} class="mr-1 mb-1 tactic-tag">
							{t.toUpperCase()}
						</NTag>
					))
				: <em class="text-tertiary">—</em>
	},
	{
		title: "Products",
		key: "products",
		width: 160,
		minWidth: 120,
		className: "whitespace-nowrap",
		render: row =>
			row.products.length
				? (
					<div class="flex flex-wrap gap-1">
						{row.products.map(p => (
							<span key={p} class="product-chip">{p}</span>
						))}
					</div>
				)
				: <em class="text-tertiary">—</em>
	},
	{
		title: "Date",
		key: "date",
		width: 120,
		sorter: (a, b) => (a.date || "").localeCompare(b.date || ""),
		render: row =>
			row.date
				? <span class="font-mono text-xs">{row.date}</span>
				: <em class="text-tertiary">—</em>
	}
]

function load() {
	loading.value = true
	Api.detectionCatalog
		.listStories()
		.then(res => {
			if (res.data?.success) {
				stories.value = res.data.stories || []
			} else {
				message.warning(res.data?.message || "Failed to load analytic stories")
			}
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
.stories-table :deep(.n-data-table-tr:hover) {
	background: rgba(var(--primary-color-rgb) / 0.04);
}
.tactic-tag {
	font-weight: 600;
	letter-spacing: 0.04em;
}

/* Product chip — simple text in a bordered pill. Matches the visual weight
   of the data-source / tactic tags without competing for attention. */
.stories-table :deep(.product-chip) {
	display: inline-flex;
	align-items: center;
	padding: 2px 8px;
	font-size: 0.72rem;
	font-weight: 500;
	color: var(--fg-default-color);
	background: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: 999px;
	white-space: nowrap;
}
</style>
