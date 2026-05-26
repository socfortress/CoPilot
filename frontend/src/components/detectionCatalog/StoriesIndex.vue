<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-wrap items-end justify-between gap-3">
			<div class="flex flex-col gap-1">
				<h3 class="text-lg font-semibold">Analytic Stories</h3>
				<p class="text-secondary text-sm">
					Each story is a threat narrative covered by one or more CoPilot Searches detections. Click a row to
					see the member detections, data sources, and references.
				</p>
			</div>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			<n-input
				v-model:value="filter"
				size="small"
				placeholder="Filter by story name, data source, tactic, or product…"
				clearable
				class="min-w-80 flex-1"
			>
				<template #prefix><Icon name="carbon:search" /></template>
			</n-input>
			<Badge type="splitted" color="primary" class="shrink-0">
				<template #label>Showing</template>
				<template #value>{{ filteredStories.length }} / {{ stories.length }}</template>
			</Badge>
		</div>

		<n-data-table :columns :data="filteredStories" :loading size="small" :row-props :pagination :scroll-x="1200" />

		<n-modal
			v-model:show="showStoryModal"
			preset="card"
			:style="{ maxWidth: 'min(1080px, 94vw)' }"
			title="Analytic Story"
			:bordered="false"
			segmented
			@after-leave="selectedStoryName = null"
		>
			<StoryDetail v-if="selectedStoryName" :story-name="selectedStoryName" />
		</n-modal>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { CatalogStoryRow } from "@/types/detectionCatalog.d"
import { NDataTable, NInput, NModal, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import StoryDetail from "./StoryDetail.vue"

const MAX_SOURCES_TAG = 3
const MAX_TACTICS_TAG = 3
const MAX_PRODUCTS_TAG = 3

const message = useMessage()
const stories = ref<CatalogStoryRow[]>([])
const loading = ref(false)
const filter = ref("")
const showStoryModal = ref(false)
const selectedStoryName = ref<string | null>(null)
const dFormats = useSettingsStore().dateFormat

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
		class: "cursor-pointer",
		onClick: () => openStoryDetail(row.name)
	}
}

function openStoryDetail(storyName: string) {
	selectedStoryName.value = storyName
	showStoryModal.value = true
}

const columns: DataTableColumns<CatalogStoryRow> = [
	{
		title: "Story",
		key: "name",
		fixed: "left",
		width: 200,
		sorter: (a, b) => a.name.localeCompare(b.name),
		render: row => (
			<div class="flex flex-col gap-1 py-1">
				<div class="leading-snug font-semibold">{row.name}</div>
				<div class="text-secondary font-mono text-xs uppercase">
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
					{row.data_sources.slice(0, MAX_SOURCES_TAG).map(s => (
						<NTag size="small" type="primary" key={s}>
							{s}
						</NTag>
					))}
					{row.data_sources.length > MAX_SOURCES_TAG && (
						<NTag size="small">{`+${row.data_sources.length - MAX_SOURCES_TAG}`}</NTag>
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
					{row.tactics.slice(0, MAX_TACTICS_TAG).map(t => (
						<NTag size="small" type="warning" key={t}>
							{t.toUpperCase()}
						</NTag>
					))}
					{row.tactics.length > MAX_TACTICS_TAG && (
						<NTag size="small">{`+${row.tactics.length - MAX_TACTICS_TAG}`}</NTag>
					)}
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
					{row.products.slice(0, MAX_PRODUCTS_TAG).map(p => (
						<NTag size="small" key={p}>
							{p}
						</NTag>
					))}
					{row.products.length > MAX_PRODUCTS_TAG && (
						<NTag size="small">{`+${row.products.length - MAX_PRODUCTS_TAG}`}</NTag>
					)}
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
				<span class="font-mono text-xs">{formatDate(row.date, dFormats.date)}</span>
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
