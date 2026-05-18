<template>
	<div class="coverage-gaps-index flex flex-col gap-3">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h3>Coverage Gaps</h3>
			<div v-if="!loading" class="text-tertiary text-xs">
				<strong>{{ gap_count }}</strong>
				gap{{ gap_count === 1 ? "" : "s" }} across
				<strong>{{ total_techniques }}</strong>
				technique{{ total_techniques === 1 ? "" : "s" }}
				· <strong>{{ coverage_pct }}%</strong> covered
			</div>
		</div>

		<p class="text-secondary text-sm">
			MITRE ATT&amp;CK techniques no rule covers — across both CoPilot Searches and the Wazuh
			ruleset. Sub-techniques are collapsed into their parents (a hit on T1059.001 counts as
			coverage for T1059). Use this list to spot where new detections would expand coverage.
		</p>

		<n-input
			v-model:value="filter"
			size="small"
			placeholder="Filter by technique ID, name, tactic…"
			clearable
		>
			<template #prefix><Icon name="carbon:search" /></template>
		</n-input>

		<n-spin :show="loading">
			<n-data-table
				:columns="columns"
				:data="filteredGaps"
				:loading
				size="small"
				:pagination="pagination"
				class="coverage-gaps-table"
			/>
		</n-spin>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { CatalogCoverageGapRow } from "@/types/detectionCatalog.d"
import { NDataTable, NInput, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const message = useMessage()

const gaps = ref<CatalogCoverageGapRow[]>([])
const gap_count = ref(0)
const total_techniques = ref(0)
const coverage_pct = ref(0)

const loading = ref(false)
const filter = ref("")

// Same pagination defaults as the Wazuh tab — keeps the catalog feel
// consistent across browse modes.
const pagination = {
	pageSize: 50,
	pageSizes: [25, 50, 100, 200],
	showSizePicker: true
}

const filteredGaps = computed<CatalogCoverageGapRow[]>(() => {
	const q = filter.value.trim().toLowerCase()
	if (!q) return gaps.value
	return gaps.value.filter(g =>
		[g.technique_id, g.technique_name, ...(g.tactics || [])]
			.join(" ")
			.toLowerCase()
			.includes(q)
	)
})

const columns: DataTableColumns<CatalogCoverageGapRow> = [
	{
		title: "Technique ID",
		key: "technique_id",
		width: 130,
		sorter: (a, b) => a.technique_id.localeCompare(b.technique_id),
		render: row =>
			row.url
				? (
					<a
						href={row.url}
						target="_blank"
						rel="noopener"
						class="font-mono text-xs text-primary hover:underline"
					>
						{row.technique_id}
					</a>
				)
				: <span class="font-mono text-xs">{row.technique_id}</span>
	},
	{
		title: "Technique",
		key: "technique_name",
		sorter: (a, b) => a.technique_name.localeCompare(b.technique_name),
		render: row => <span>{row.technique_name}</span>
	},
	{
		title: "Tactics",
		key: "tactics",
		render: row =>
			row.tactics.length
				? (
					<div class="flex flex-wrap gap-1">
						{row.tactics.map(t => (
							<NTag key={t} size="tiny" type="warning" bordered={false}>{t}</NTag>
						))}
					</div>
				)
				: <em class="text-tertiary">—</em>
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
.coverage-gaps-table :deep(.n-data-table-tr:hover) {
	background: rgba(var(--primary-color-rgb) / 0.04);
}
</style>
