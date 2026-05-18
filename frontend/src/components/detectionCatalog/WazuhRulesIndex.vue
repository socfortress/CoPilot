<template>
	<div class="wazuh-rules-index flex flex-col gap-3">
		<!-- Logtest panel — collapsible. Above the table so analysts find it
		     when they're looking at the rules; collapsed by default so it
		     doesn't push the table down for routine browsing. -->
		<WazuhLogTest @open-rule="openRuleById" />

		<div class="flex flex-wrap items-center justify-between gap-3">
			<h3>Wazuh Rules</h3>
			<div class="text-tertiary text-xs">
				<strong>{{ filteredRules.length }}</strong>
				/ {{ rules.length }}
			</div>
		</div>

		<n-input
			v-model:value="filter"
			size="small"
			placeholder="Filter by ID, description, group, MITRE ID, file…"
			clearable
		>
			<template #prefix><Icon name="carbon:search" /></template>
		</n-input>

		<!-- Quick filter chips. Only shown when firing stats are available —
		     these slice on hit counts, which we don't have when the indexer
		     is unreachable. -->
		<div v-if="firingStatsAvailable" class="flex flex-wrap items-center gap-2">
			<span class="text-tertiary text-xs">Quick filters:</span>
			<n-tag
				:type="activeChip === 'all' ? 'primary' : 'default'"
				:bordered="false"
				size="small"
				class="cursor-pointer"
				@click="activeChip = 'all'"
			>
				All
			</n-tag>
			<n-tag
				:type="activeChip === 'noisy' ? 'primary' : 'default'"
				:bordered="false"
				size="small"
				class="cursor-pointer"
				@click="activeChip = 'noisy'"
			>
				Top noisy (50)
			</n-tag>
			<n-tag
				:type="activeChip === 'dead' ? 'primary' : 'default'"
				:bordered="false"
				size="small"
				class="cursor-pointer"
				@click="activeChip = 'dead'"
			>
				Dead (0 hits 30d)
			</n-tag>
		</div>

		<!-- Unavailable state: Wazuh Manager not reachable / not configured.
		     We DON'T render the table here — empty rows below an unhelpful
		     header look like a bug. Show the reason inline so the operator
		     knows it's a wiring problem, not a missing-data one. -->
		<n-alert v-if="!loading && !available" type="warning" :show-icon="true">
			<template #header>Wazuh Manager not available</template>
			{{ unavailableReason || "Could not reach the Wazuh Manager to load rules." }}
		</n-alert>

		<n-spin v-else :show="loading">
			<n-data-table
				:columns="columns"
				:data="filteredRules"
				:loading
				size="small"
				:row-props="rowProps"
				:pagination="pagination"
				class="wazuh-rules-table"
			/>
		</n-spin>

		<!-- Detail modal. Mounted at the index level (not inside the row click
		     handler) so swapping rules is one prop change instead of a
		     teardown+rebuild. -->
		<n-modal
			v-model:show="showDetailModal"
			preset="card"
			:style="{ maxWidth: 'min(820px, 92vw)', minHeight: 'min(540px, 90vh)' }"
			:title="modalTitle"
			:bordered="false"
			segmented
		>
			<WazuhRuleDetail v-if="modalRuleId !== null" :rule-id="modalRuleId" />
		</n-modal>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { CatalogWazuhRuleRow } from "@/types/detectionCatalog.d"
import { NAlert, NDataTable, NInput, NModal, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import WazuhLogTest from "./WazuhLogTest.vue"
import WazuhRuleDetail from "./WazuhRuleDetail.vue"

const message = useMessage()
const rules = ref<CatalogWazuhRuleRow[]>([])
const loading = ref(false)
const filter = ref("")

// Availability state from the envelope. When the Wazuh Manager is down we
// show an inline alert instead of an empty table.
const available = ref(true)
const unavailableReason = ref<string | null>(null)

// Firing-stats availability is separate — the indexer can be down even when
// the manager is up. When stats are unavailable we hide the Hits column AND
// the quick-filter chips (filtering "Top noisy" makes no sense if every
// row shows 0 hits).
const firingStatsAvailable = ref(true)

// Quick-filter chip state. "all" = no chip filter, "noisy" = top 50 by
// hits_30d desc, "dead" = hits_30d === 0.
type ChipKey = "all" | "noisy" | "dead"
const activeChip = ref<ChipKey>("all")

// Detail modal state. modalRuleId is the integer rule ID; modalTitle is
// computed off the row so we can show "Rule 31100 — sshd: brute force"
// without a second fetch.
const showDetailModal = ref(false)
const modalRuleId = ref<number | null>(null)
const modalTitle = ref("Wazuh Rule")

// Naive UI pagination — pageSize 50 is comfortable for the ~3–5k corpus.
// `showSizePicker` lets analysts bump it up when they're hunting for
// something specific.
const pagination = {
	pageSize: 50,
	pageSizes: [25, 50, 100, 200],
	showSizePicker: true
}

const filteredRules = computed<CatalogWazuhRuleRow[]>(() => {
	// Step 1: text filter (always applied)
	const q = filter.value.trim().toLowerCase()
	const textFiltered = !q
		? rules.value
		: rules.value.filter(r =>
				[
					String(r.id ?? ""),
					r.description,
					r.filename,
					r.relative_dirname,
					...(r.groups || []),
					...(r.mitre || [])
				]
					.join(" ")
					.toLowerCase()
					.includes(q)
			)

	// Step 2: chip filter (applied on top of text filter)
	if (activeChip.value === "noisy") {
		// Top 50 by hits_30d desc. We sort a copy so we don't mutate the
		// cached array reactively (would re-trigger this computed forever).
		return [...textFiltered]
			.sort((a, b) => b.hits_30d - a.hits_30d)
			.slice(0, 50)
	}
	if (activeChip.value === "dead") {
		return textFiltered.filter(r => r.hits_30d === 0)
	}
	return textFiltered
})

function openRuleDetail(row: CatalogWazuhRuleRow) {
	if (typeof row.id !== "number") return
	modalRuleId.value = row.id
	modalTitle.value = `Rule ${row.id}${row.description ? " — " + row.description : ""}`
	showDetailModal.value = true
}

// Open by ID — used when the logtest panel emits "View in catalog" on a
// matched rule. We look up the row in the cached list to get the description
// for the modal title; if the rule isn't in the cache (rare — usually a
// custom rule on the live Wazuh that isn't yet in our cache) we still open
// the modal which will fetch the detail by ID and show what it can.
function openRuleById(ruleId: number) {
	const row = rules.value.find(r => r.id === ruleId)
	modalRuleId.value = ruleId
	modalTitle.value = row
		? `Rule ${ruleId}${row.description ? " — " + row.description : ""}`
		: `Rule ${ruleId}`
	showDetailModal.value = true
}

// Row-click = open detail. Same pattern as the Stories table — the entire
// row is the affordance.
function rowProps(row: CatalogWazuhRuleRow) {
	return {
		style: "cursor: pointer;",
		onClick: () => openRuleDetail(row)
	}
}

// Level colour — Wazuh's severity scale runs 0-15. We bucket it into the
// three NTag colours we already use elsewhere for severity, so the visual
// matches the rest of the SOC analyst UI without inventing a new palette.
function levelTagType(level: number | null): "default" | "info" | "warning" | "error" {
	if (level === null || level === undefined) return "default"
	if (level >= 12) return "error"
	if (level >= 7) return "warning"
	if (level >= 3) return "info"
	return "default"
}

// Hits column — only included when the indexer is reachable. Rendering "0"
// for every row when stats are unavailable would mislead analysts into
// thinking nothing has fired. Hiding it makes the absence visible.
const hitsColumn = computed(() => ({
	title: "Hits 30d",
	key: "hits_30d",
	width: 110,
	sorter: (a: CatalogWazuhRuleRow, b: CatalogWazuhRuleRow) => a.hits_30d - b.hits_30d,
	defaultSortOrder: false as const,
	render: (row: CatalogWazuhRuleRow) => {
		if (row.hits_30d === 0) {
			return <span class="text-tertiary text-xs">0</span>
		}
		// Show 30d total + 7d sub-count so analysts can spot recent spikes.
		return (
			<div class="flex flex-col">
				<span class="font-mono text-xs">{row.hits_30d.toLocaleString()}</span>
				<span class="text-tertiary text-xs">{row.hits_7d.toLocaleString()} in 7d</span>
			</div>
		)
	}
}))

const columns = computed<DataTableColumns<CatalogWazuhRuleRow>>(() => {
	const cols: DataTableColumns<CatalogWazuhRuleRow> = [
		{
			title: "ID",
			key: "id",
			width: 90,
			sorter: (a, b) => (a.id ?? 0) - (b.id ?? 0),
			render: row => <span class="font-mono text-xs">{row.id ?? "—"}</span>
		},
		{
			title: "Level",
			key: "level",
			width: 90,
			sorter: (a, b) => (a.level ?? 0) - (b.level ?? 0),
			render: row => (
				<NTag size="small" bordered={false} type={levelTagType(row.level)}>
					{row.level ?? "—"}
				</NTag>
			)
		},
		{
			title: "Description",
			key: "description",
			render: row =>
				row.description
					? <span>{row.description}</span>
					: <em class="text-tertiary">(no description)</em>
		},
		{
			title: "Groups",
			key: "groups",
			render: row =>
				row.groups.length
					? (
						<div class="flex flex-wrap gap-1">
							{row.groups.slice(0, 3).map(g => (
								<NTag key={g} size="tiny" type="info" bordered={false}>{g}</NTag>
							))}
							{row.groups.length > 3 && (
								<NTag size="tiny" bordered={false}>+{row.groups.length - 3}</NTag>
							)}
						</div>
					)
					: <em class="text-tertiary">—</em>
		},
		{
			title: "MITRE",
			key: "mitre",
			width: 140,
			render: row =>
				row.mitre.length
					? (
						<div class="flex flex-wrap gap-1">
							{row.mitre.map(t => (
								<NTag key={t} size="tiny" bordered={false}>{t}</NTag>
							))}
						</div>
					)
					: <em class="text-tertiary">—</em>
		},
		{
			title: "File",
			key: "filename",
			width: 220,
			ellipsis: { tooltip: true },
			render: row => <span class="font-mono text-xs">{row.filename || "—"}</span>
		}
	]
	// Append the Hits column only when firing stats are available — see
	// hitsColumn definition above for why we hide it instead of zeroing.
	if (firingStatsAvailable.value) {
		cols.push(hitsColumn.value)
	}
	return cols
})

function load() {
	loading.value = true
	Api.detectionCatalog
		.listWazuhRules()
		.then(res => {
			if (res.data?.success) {
				rules.value = res.data.rules || []
				available.value = res.data.available
				unavailableReason.value = res.data.unavailable_reason
				firingStatsAvailable.value = res.data.firing_stats_available
			} else {
				message.warning(res.data?.message || "Failed to load Wazuh rules")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.detail || err.response?.data?.message || "Failed to load Wazuh rules")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(load)
</script>

<style scoped lang="scss">
.wazuh-rules-table :deep(.n-data-table-tr:hover) {
	background: rgba(var(--primary-color-rgb) / 0.04);
}
</style>
