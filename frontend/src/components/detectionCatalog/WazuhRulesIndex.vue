<template>
	<div class="wazuh-rules-index flex flex-col gap-4">
		<!-- Logtest panel — collapsible. Above the table so analysts find it
		     when they're looking at the rules; collapsed by default so it
		     doesn't push the table down for routine browsing. -->
		<WazuhLogTest @open-rule="openRuleById" />

		<!-- HEADER ROW: title/blurb + toolbar (filter chips + counts) -->
		<div class="flex flex-wrap items-end justify-between gap-3">
			<div class="flex flex-col gap-1">
				<h3 class="m-0 text-lg font-semibold">Wazuh Rules</h3>
				<p class="text-secondary m-0 text-sm">
					Every rule shipped by the Wazuh Manager. Sort by hits to spot noisy rules,
					switch to "Dead" to find rules that never fire, or filter by customer to
					see the picture for a specific tenant.
				</p>
			</div>
			<Badge type="splitted" color="primary">
				<template #label>Showing</template>
				<template #value>{{ filteredRules.length }} / {{ rules.length }}</template>
			</Badge>
		</div>

		<!-- TOOLBAR: search + customer scope -->
		<div class="flex flex-wrap items-center gap-2">
			<n-input
				v-model:value="filter"
				size="medium"
				placeholder="Filter by ID, description, group, MITRE ID, or filename…"
				clearable
				class="flex-1"
				style="min-width: 240px"
			>
				<template #prefix><Icon name="carbon:search" /></template>
			</n-input>

			<n-select
				v-if="firingStatsAvailable"
				v-model:value="customerScope"
				:options="customerOptions"
				:loading="loadingCustomers || refetchingForCustomer"
				size="medium"
				style="min-width: 220px"
				:consistent-menu-width="false"
				@update:value="onCustomerChange"
			/>
		</div>

		<!-- QUICK FILTER CHIPS - segmented style with hit-count summaries -->
		<div v-if="firingStatsAvailable" class="filter-bar">
			<button
				type="button"
				class="filter-chip"
				:class="{ active: activeChip === 'all' }"
				@click="activeChip = 'all'"
			>
				<Icon name="carbon:list" :size="13" />
				<span>All</span>
				<span class="chip-count">{{ rules.length }}</span>
			</button>
			<button
				type="button"
				class="filter-chip noisy"
				:class="{ active: activeChip === 'noisy' }"
				@click="activeChip = 'noisy'"
			>
				<Icon name="carbon:flash" :size="13" />
				<span>Top noisy</span>
				<span class="chip-count">50</span>
			</button>
			<button
				type="button"
				class="filter-chip dead"
				:class="{ active: activeChip === 'dead' }"
				@click="activeChip = 'dead'"
			>
				<Icon name="carbon:warning" :size="13" />
				<span>Dead (level ≥7)</span>
				<span class="chip-count">{{ deadCount }}</span>
			</button>
		</div>

		<!-- Unavailable state: Wazuh Manager not reachable / not configured. -->
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
				class="catalog-table wazuh-rules-table"
			/>
		</n-spin>

		<!-- Detail modal -->
		<n-modal
			v-model:show="showDetailModal"
			preset="card"
			:style="{ maxWidth: 'min(880px, 94vw)', minHeight: 'min(600px, 90vh)' }"
			:title="modalTitle"
			:bordered="false"
			segmented
		>
			<WazuhRuleDetail v-if="modalRuleId !== null" :rule-id="modalRuleId" />
		</n-modal>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns, SelectOption } from "naive-ui"
import type { CatalogWazuhRuleRow } from "@/types/detectionCatalog.d"
import { NAlert, NDataTable, NInput, NModal, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import WazuhLogTest from "./WazuhLogTest.vue"
import WazuhRuleDetail from "./WazuhRuleDetail.vue"

const message = useMessage()
const rules = ref<CatalogWazuhRuleRow[]>([])
const loading = ref(false)
const filter = ref("")

const available = ref(true)
const unavailableReason = ref<string | null>(null)
const firingStatsAvailable = ref(true)

type ChipKey = "all" | "noisy" | "dead"
const activeChip = ref<ChipKey>("all")

const customerScope = ref<string>("")
const customerOptions = ref<SelectOption[]>([{ label: "All customers", value: "" }])
const loadingCustomers = ref(false)
const refetchingForCustomer = ref(false)

const showDetailModal = ref(false)
const modalRuleId = ref<number | null>(null)
const modalTitle = ref("Wazuh Rule")

const pagination = {
	pageSize: 50,
	pageSizes: [25, 50, 100, 200],
	showSizePicker: true
}

// Count of "dead" rules for the chip badge — keeps the analyst informed of
// how many candidates the filter would surface before clicking.
const deadCount = computed(
	() => rules.value.filter(r => r.hits_30d === 0 && (r.level ?? 0) >= 7).length
)

const filteredRules = computed<CatalogWazuhRuleRow[]>(() => {
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

	if (activeChip.value === "noisy") {
		return [...textFiltered].sort((a, b) => b.hits_30d - a.hits_30d).slice(0, 50)
	}
	if (activeChip.value === "dead") {
		return textFiltered.filter(r => r.hits_30d === 0 && (r.level ?? 0) >= 7)
	}
	return textFiltered
})

function openRuleDetail(row: CatalogWazuhRuleRow) {
	if (typeof row.id !== "number") return
	modalRuleId.value = row.id
	modalTitle.value = `Rule ${row.id}${row.description ? " — " + row.description : ""}`
	showDetailModal.value = true
}

function openRuleById(ruleId: number) {
	const row = rules.value.find(r => r.id === ruleId)
	modalRuleId.value = ruleId
	modalTitle.value = row
		? `Rule ${ruleId}${row.description ? " — " + row.description : ""}`
		: `Rule ${ruleId}`
	showDetailModal.value = true
}

function rowProps(row: CatalogWazuhRuleRow) {
	return {
		style: "cursor: pointer;",
		onClick: () => openRuleDetail(row)
	}
}

function levelTagClass(level: number | null): string {
	if (level === null || level === undefined) return "level-pill level-none"
	if (level >= 12) return "level-pill level-critical"
	if (level >= 7) return "level-pill level-warning"
	if (level >= 3) return "level-pill level-info"
	return "level-pill level-low"
}

function loadCustomers() {
	loadingCustomers.value = true
	Api.customers
		.getCustomers()
		.then(res => {
			const list = res.data?.customers || []
			customerOptions.value = [
				{ label: "All customers", value: "" },
				...list.map(c => ({
					label: c.customer_name ? `${c.customer_name} (${c.customer_code})` : c.customer_code,
					value: c.customer_code
				}))
			]
		})
		.catch(() => {
			/* Non-fatal — keep just "All customers" option. */
		})
		.finally(() => {
			loadingCustomers.value = false
		})
}

function onCustomerChange(value: string) {
	customerScope.value = value
	refetchingForCustomer.value = true
	load(true)
}

// Hits column — only included when the indexer is reachable. Rendering "0"
// everywhere when stats are unavailable would mislead, so we hide the column
// entirely.
const hitsColumn = computed(() => ({
	title: "Activity",
	key: "hits_30d",
	width: 140,
	sorter: (a: CatalogWazuhRuleRow, b: CatalogWazuhRuleRow) => a.hits_30d - b.hits_30d,
	render: (row: CatalogWazuhRuleRow) => {
		if (row.hits_30d === 0) {
			return (
				<div class="flex items-center gap-1.5">
					<span class="dot dot-muted"></span>
					<span class="text-tertiary text-xs">No hits 30d</span>
				</div>
			)
		}
		// Color the indicator dot by intensity bucket so analysts can scan
		// the column without reading numbers.
		const dotClass =
			row.hits_30d >= 10000 ? "dot-danger" :
			row.hits_30d >= 1000 ? "dot-warning" :
			row.hits_30d >= 100 ? "dot-info" : "dot-success"
		return (
			<div class="flex items-center gap-2">
				<span class={`dot ${dotClass}`}></span>
				<div class="flex flex-col leading-tight">
					<span class="font-mono text-xs font-medium">{row.hits_30d.toLocaleString()}</span>
					<span class="text-tertiary text-xs">{row.hits_7d.toLocaleString()} in 7d</span>
				</div>
			</div>
		)
	}
}))

const columns = computed<DataTableColumns<CatalogWazuhRuleRow>>(() => {
	const cols: DataTableColumns<CatalogWazuhRuleRow> = [
		{
			title: "ID",
			key: "id",
			width: 100,
			sorter: (a, b) => (a.id ?? 0) - (b.id ?? 0),
			render: row => <span class="font-mono text-xs text-secondary">{row.id ?? "—"}</span>
		},
		{
			title: "Level",
			key: "level",
			width: 90,
			sorter: (a, b) => (a.level ?? 0) - (b.level ?? 0),
			render: row => (
				<span class={levelTagClass(row.level)}>{row.level ?? "—"}</span>
			)
		},
		{
			title: "Description",
			key: "description",
			render: row =>
				row.description
					? <span class="leading-snug">{row.description}</span>
					: <span class="text-tertiary text-xs">(no description)</span>
		},
		{
			title: "Groups",
			key: "groups",
			render: row =>
				row.groups.length
					? (
						<div class="flex flex-wrap gap-1">
							{row.groups.slice(0, 3).map(g => (
								<span key={g} class="chip chip-info">{g}</span>
							))}
							{row.groups.length > 3 && (
								<span class="chip chip-muted">+{row.groups.length - 3}</span>
							)}
						</div>
					)
					: <span class="text-tertiary text-xs">—</span>
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
								<span key={t} class="chip chip-mitre">{t}</span>
							))}
						</div>
					)
					: <span class="text-tertiary text-xs">—</span>
		},
		{
			title: "File",
			key: "filename",
			width: 200,
			ellipsis: { tooltip: true },
			render: row => <span class="font-mono text-xs text-tertiary">{row.filename || "—"}</span>
		}
	]
	if (firingStatsAvailable.value) cols.push(hitsColumn.value)
	return cols
})

function load(isCustomerChange = false) {
	if (!isCustomerChange) loading.value = true
	Api.detectionCatalog
		.listWazuhRules(customerScope.value || undefined)
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
			refetchingForCustomer.value = false
		})
}

onBeforeMount(() => {
	loadCustomers()
	load()
})
</script>

<style scoped lang="scss">
/* Filter bar with chip-style toggle buttons. Mimics segmented controls
   without overcrowding — each chip has its own accent color so analysts
   know what flavor of filter they're picking. */
.filter-bar {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
}

.filter-chip {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	padding: 5px 12px;
	font-size: 0.78rem;
	font-weight: 500;
	color: var(--fg-secondary-color);
	background-color: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: 999px;
	cursor: pointer;
	transition: all 0.15s var(--bezier-ease);

	&:hover:not(.active) {
		border-color: rgba(var(--primary-color-rgb) / 0.3);
		color: var(--fg-default-color);
	}

	&.active {
		color: var(--primary-color);
		background-color: rgba(var(--primary-color-rgb) / 0.08);
		border-color: rgba(var(--primary-color-rgb) / 0.35);
	}

	&.noisy.active {
		color: var(--warning-color);
		background-color: rgba(var(--warning-color-rgb) / 0.1);
		border-color: rgba(var(--warning-color-rgb) / 0.35);
	}

	&.dead.active {
		color: var(--error-color);
		background-color: rgba(var(--error-color-rgb) / 0.08);
		border-color: rgba(var(--error-color-rgb) / 0.3);
	}

	.chip-count {
		font-family: var(--font-family-mono);
		font-size: 0.7rem;
		opacity: 0.7;
		margin-left: 2px;
	}
}

/* Level pill — small numeric badge with severity coloring. Replaces the
   plain NTag with a uniform-width, monospace circle-ish for easier eye
   scanning down the Level column. */
:deep(.level-pill) {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 28px;
	height: 22px;
	padding: 0 6px;
	font-size: 0.78rem;
	font-weight: 600;
	font-family: var(--font-family-mono);
	border-radius: 5px;
	border: 1px solid transparent;
}
:deep(.level-pill.level-none) {
	color: var(--fg-secondary-color);
	opacity: 0.6;
	background-color: var(--bg-secondary-color);
	border-color: var(--border-color);
}
:deep(.level-pill.level-low) {
	color: var(--fg-secondary-color);
	background-color: var(--bg-secondary-color);
	border-color: var(--border-color);
}
:deep(.level-pill.level-info) {
	color: var(--primary-color);
	background-color: rgba(var(--primary-color-rgb) / 0.1);
	border-color: rgba(var(--primary-color-rgb) / 0.25);
}
:deep(.level-pill.level-warning) {
	color: var(--warning-color);
	background-color: rgba(var(--warning-color-rgb) / 0.12);
	border-color: rgba(var(--warning-color-rgb) / 0.3);
}
:deep(.level-pill.level-critical) {
	color: var(--error-color);
	background-color: rgba(var(--error-color-rgb) / 0.1);
	border-color: rgba(var(--error-color-rgb) / 0.3);
}

/* Activity-column indicator dot — small color-coded dot left of the hit
   counts. Lets analysts spot hot/cold rules without reading numbers. */
:deep(.dot) {
	display: inline-block;
	width: 8px;
	height: 8px;
	border-radius: 50%;
	flex-shrink: 0;
}
:deep(.dot-muted)   { background-color: var(--border-color); }
:deep(.dot-success) { background-color: var(--success-color); }
:deep(.dot-info)    { background-color: var(--primary-color); }
:deep(.dot-warning) { background-color: var(--warning-color); }
:deep(.dot-danger)  { background-color: var(--error-color); }

/* Catalog table base — same rules as StoriesIndex. */
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
:deep(.chip-mitre) {
	color: var(--fg-default-color);
	background-color: var(--bg-secondary-color);
	border-color: var(--border-color);
	font-family: var(--font-family-mono);
}
:deep(.chip-muted) {
	color: var(--fg-secondary-color);
	background-color: rgba(var(--border-color-rgb) / 0.15);
	border-color: var(--border-color);
}
</style>
