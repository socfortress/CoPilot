<template>
	<div class="compliance-index flex flex-col gap-4">
		<!-- Title row + framing copy -->
		<div class="flex flex-wrap items-end justify-between gap-3">
			<div class="flex flex-col gap-1">
				<h3 class="m-0 text-lg font-semibold">Compliance Coverage</h3>
				<p class="text-secondary m-0 max-w-3xl text-sm">
					Wazuh rules grouped by control ID for the selected compliance framework. Each
					row shows how many rules cover that control and how active they've been —
					useful for auditor questions like "what coverage do we have for PCI DSS 10.2.4?".
				</p>
			</div>
			<Badge v-if="pivot" type="splitted" color="primary">
				<template #label>Showing</template>
				<template #value>{{ filteredGroups.length }} / {{ pivot.groups.length }}</template>
			</Badge>
		</div>

		<!-- HERO STATS for the selected framework -->
		<div v-if="!loading && pivot" class="compliance-stats-grid">
			<CatalogStatTile
				:label="`${pivot.framework_label} controls`"
				:value="pivot.control_count"
				:icon="ControlIcon"
				accent="primary"
				sub="Distinct control IDs"
			/>
			<CatalogStatTile
				label="Rules tagged"
				:value="pivot.rules_with_compliance"
				:icon="RulesIcon"
				:sub="`of ${pivot.total_rules} total Wazuh rules`"
			/>
			<CatalogStatTile
				label="Rules without tag"
				:value="pivot.total_rules - pivot.rules_with_compliance"
				:icon="UntaggedIcon"
				accent="warning"
				sub="Not classified for this framework"
			/>
		</div>

		<!-- Framework selector + control search -->
		<div class="flex flex-wrap items-center gap-2">
			<n-select
				v-model:value="selectedFramework"
				:options="frameworkOptions"
				:loading="loadingFrameworks"
				size="medium"
				style="min-width: 240px"
				@update:value="load"
			/>
			<n-input
				v-model:value="filter"
				size="medium"
				placeholder="Filter by control ID…"
				clearable
				class="flex-1"
				style="min-width: 240px"
			>
				<template #prefix><Icon name="carbon:search" /></template>
			</n-input>
		</div>

		<n-spin :show="loading">
			<n-data-table
				:columns
				:data="filteredGroups"
				:loading
				size="small"
				:pagination
				:row-props
				class="catalog-table"
			/>
		</n-spin>

		<!-- Control drill-down modal -->
		<n-modal
			v-model:show="showGroupModal"
			preset="card"
			:style="{ maxWidth: 'min(720px, 92vw)' }"
			:title="modalTitle"
			:bordered="false"
			segmented
		>
			<div v-if="modalGroup" class="flex flex-col gap-4">
				<div class="flex flex-wrap gap-2">
					<Badge type="splitted" color="primary">
						<template #label>Rules</template>
						<template #value>{{ modalGroup.rule_count }}</template>
					</Badge>
					<Badge type="splitted" :color="modalGroup.total_hits_30d > 0 ? 'warning' : undefined">
						<template #label>Hits 30d</template>
						<template #value>{{ modalGroup.total_hits_30d.toLocaleString() }}</template>
					</Badge>
					<Badge type="splitted">
						<template #label>Hits 7d</template>
						<template #value>{{ modalGroup.total_hits_7d.toLocaleString() }}</template>
					</Badge>
				</div>

				<CardEntity size="small">
					<template #headerMain>
						<div class="flex items-center gap-2">
							<Icon name="carbon:list" :size="14" />
							<span class="text-sm font-semibold uppercase tracking-wide">Rule IDs</span>
						</div>
					</template>
					<template #default>
						<div class="flex flex-wrap gap-1.5">
							<span v-for="rid of modalGroup.rule_ids" :key="rid" class="rule-id-pill">
								{{ rid }}
							</span>
						</div>
					</template>
				</CardEntity>

				<p class="text-tertiary m-0 text-xs">
					Switch to the Wazuh Rules tab and search by ID for full rule details.
				</p>
			</div>
		</n-modal>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns, SelectOption } from "naive-ui"
import type {
	CatalogComplianceFramework,
	CatalogComplianceGroupRow,
	CatalogComplianceResponse
} from "@/types/detectionCatalog.d"
import { NDataTable, NInput, NModal, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import CatalogStatTile from "./CatalogStatTile.vue"

const message = useMessage()

const frameworks = ref<CatalogComplianceFramework[]>([])
const selectedFramework = ref<string>("pci_dss")
const pivot = ref<CatalogComplianceResponse | null>(null)
const loadingFrameworks = ref(false)
const loading = ref(false)
const filter = ref("")

const showGroupModal = ref(false)
const modalGroup = ref<CatalogComplianceGroupRow | null>(null)
const modalTitle = ref("Compliance Control")

const ControlIcon = "carbon:certificate-check"
const RulesIcon = "carbon:document-security"
const UntaggedIcon = "carbon:document-blank"

const pagination = {
	pageSize: 25,
	pageSizes: [10, 25, 50, 100],
	showSizePicker: true
}

const frameworkOptions = computed<SelectOption[]>(() =>
	frameworks.value.map(f => ({ label: f.label, value: f.key }))
)

const filteredGroups = computed<CatalogComplianceGroupRow[]>(() => {
	const groups = pivot.value?.groups || []
	const q = filter.value.trim().toLowerCase()
	if (!q) return groups
	return groups.filter(g => g.control.toLowerCase().includes(q))
})

function openGroup(group: CatalogComplianceGroupRow) {
	modalGroup.value = group
	modalTitle.value = `${pivot.value?.framework_label ?? ""} ${group.control}`
	showGroupModal.value = true
}

function rowProps(row: CatalogComplianceGroupRow) {
	return {
		style: "cursor: pointer;",
		onClick: () => openGroup(row)
	}
}

const columns: DataTableColumns<CatalogComplianceGroupRow> = [
	{
		title: "Control",
		key: "control",
		width: 200,
		sorter: (a, b) => a.control.localeCompare(b.control),
		render: row => <span class="font-mono text-sm font-medium">{row.control}</span>
	},
	{
		title: "Rules",
		key: "rule_count",
		width: 100,
		sorter: (a, b) => a.rule_count - b.rule_count,
		render: row => <span class="rules-count-pill">{row.rule_count}</span>
	},
	{
		title: "Activity",
		key: "total_hits_30d",
		width: 150,
		defaultSortOrder: "descend",
		sorter: (a, b) => a.total_hits_30d - b.total_hits_30d,
		render: row => {
			if (row.total_hits_30d === 0) {
				return (
					<div class="flex items-center gap-1.5">
						<span class="dot dot-muted"></span>
						<span class="text-tertiary text-xs">No hits 30d</span>
					</div>
				)
			}
			const dotClass =
				row.total_hits_30d >= 10000
? "dot-danger" :
				row.total_hits_30d >= 1000
? "dot-warning" :
				row.total_hits_30d >= 100 ? "dot-info" : "dot-success"
			return (
				<div class="flex items-center gap-2">
					<span class={`dot ${dotClass}`}></span>
					<div class="flex flex-col leading-tight">
						<span class="font-mono text-xs font-medium">{row.total_hits_30d.toLocaleString()}</span>
						<span class="text-tertiary text-xs">
{row.total_hits_7d.toLocaleString()}
{' '}
in 7d
      </span>
					</div>
				</div>
			)
		}
	},
	{
		title: "Rule IDs (preview)",
		key: "rule_ids",
		render: row => (
			<div class="flex flex-wrap gap-1">
				{row.rule_ids.slice(0, 10).map(rid => (
					<span key={rid} class="chip chip-mitre">{rid}</span>
				))}
				{row.rule_ids.length > 10 && (
					<span class="chip chip-muted">
+
{row.rule_ids.length - 10}
     </span>
				)}
			</div>
		)
	}
]

function loadFrameworks() {
	loadingFrameworks.value = true
	Api.detectionCatalog
		.listComplianceFrameworks()
		.then(res => {
			if (res.data?.success) {
				frameworks.value = res.data.frameworks || []
				if (frameworks.value.length && !frameworks.value.some(f => f.key === selectedFramework.value)) {
					selectedFramework.value = frameworks.value[0].key
				}
			}
		})
		.catch(() => {
			/* Non-fatal — analyst can retry. */
		})
		.finally(() => {
			loadingFrameworks.value = false
			load()
		})
}

function load() {
	if (!selectedFramework.value) return
	loading.value = true
	Api.detectionCatalog
		.getCompliancePivot(selectedFramework.value)
		.then(res => {
			if (res.data?.success) pivot.value = res.data
			else message.warning(res.data?.message || "Failed to load compliance pivot")
		})
		.catch(err => {
			message.error(err.response?.data?.detail || err.response?.data?.message || "Failed to load compliance pivot")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(loadFrameworks)
</script>

<style scoped lang="scss">
.compliance-stats-grid {
	display: grid;
	gap: 12px;
	grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.rule-id-pill {
	display: inline-flex;
	align-items: center;
	padding: 3px 10px;
	font-size: 0.72rem;
	font-family: var(--font-family-mono);
	font-weight: 500;
	border-radius: 6px;
	color: var(--fg-default-color);
	background-color: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
}

/* Rule-count pill used in the "Rules" column of the compliance pivot. Small
   monospace count in a neutral pill so the eye doesn't have to parse it as
   a CTA. */
:deep(.rules-count-pill) {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 32px;
	height: 22px;
	padding: 0 8px;
	font-size: 0.78rem;
	font-weight: 600;
	font-family: var(--font-family-mono);
	color: var(--primary-color);
	background-color: rgba(var(--primary-color-rgb) / 0.08);
	border: 1px solid rgba(var(--primary-color-rgb) / 0.2);
	border-radius: 6px;
}

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
