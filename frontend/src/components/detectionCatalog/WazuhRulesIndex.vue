<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-wrap items-end justify-between gap-3">
			<div class="flex min-w-110 flex-1 flex-col gap-1">
				<h3 class="text-lg font-semibold">Wazuh Rules</h3>
				<p class="text-secondary text-sm">
					Every rule shipped by the Wazuh Manager. Sort by hits to spot noisy rules, switch to "Dead" to find
					rules that never fire, or filter by customer to see the picture for a specific tenant.
				</p>
			</div>
			<n-button secondary type="primary" size="small" @click="showTestLogLineDrawer = true">
				<template #icon><Icon name="carbon:test-tool" /></template>
				Test a log line
			</n-button>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			<n-input
				v-model:value="filter"
				size="small"
				placeholder="Filter by ID, description, group, MITRE ID, or filename…"
				clearable
				class="min-w-80 flex-1"
			>
				<template #prefix><Icon name="carbon:search" /></template>
			</n-input>

			<n-select
				v-if="firingStatsAvailable"
				v-model:value="customerScope"
				clearable
				:options="customerOptions"
				:loading="loadingCustomers || refetchingForCustomer"
				size="small"
				class="min-w-80 flex-1"
				:consistent-menu-width="false"
				@update:value="onCustomerChange"
			/>

			<Badge type="splitted" color="primary" class="shrink-0">
				<template #label>Showing</template>
				<template #value>{{ filteredRules.length }} / {{ rules.length }}</template>
			</Badge>
		</div>

		<!-- QUICK FILTER CHIPS - segmented style with hit-count summaries -->
		<div v-if="firingStatsAvailable" class="flex flex-wrap gap-2">
			<n-tag
				:type="activeChip === 'all' ? 'primary' : 'default'"
				round
				:bordered="activeChip !== 'all'"
				class="cursor-pointer!"
				@click="activeChip = 'all'"
			>
				<div class="flex items-center gap-2 text-xs">
					<Icon name="carbon:list" :size="13" />
					<span>All</span>
					<span
						class="text-secondary text-2xs font-mono font-semibold"
						:class="{ 'text-primary!': activeChip === 'all' }"
					>
						{{ rules.length }}
					</span>
				</div>
			</n-tag>
			<n-tag
				:type="activeChip === 'noisy' ? 'warning' : 'default'"
				round
				:bordered="activeChip !== 'noisy'"
				class="cursor-pointer!"
				@click="activeChip = 'noisy'"
			>
				<div class="flex items-center gap-2 text-xs">
					<Icon name="carbon:flash" :size="13" />
					<span>Top noisy</span>
					<span
						class="text-secondary text-2xs font-mono font-semibold"
						:class="{ 'text-warning!': activeChip === 'noisy' }"
					>
						50
					</span>
				</div>
			</n-tag>
			<n-tag
				:type="activeChip === 'dead' ? 'error' : 'default'"
				round
				:bordered="activeChip !== 'dead'"
				class="cursor-pointer!"
				@click="activeChip = 'dead'"
			>
				<div class="flex items-center gap-2 text-xs">
					<Icon name="carbon:warning" :size="13" />
					<span>Dead (level ≥7)</span>
					<span
						class="text-secondary text-2xs font-mono font-semibold"
						:class="{ 'text-error!': activeChip === 'dead' }"
					>
						{{ deadCount }}
					</span>
				</div>
			</n-tag>
		</div>

		<!-- Unavailable state: Wazuh Manager not reachable / not configured. -->
		<n-alert v-if="!loading && !available" type="warning" show-icon>
			<template #header>Wazuh Manager not available</template>
			{{ unavailableReason || "Could not reach the Wazuh Manager to load rules." }}
		</n-alert>

		<n-data-table
			v-else
			:columns
			:data="filteredRules"
			:loading
			size="small"
			:scroll-x="1510"
			:pagination
			class="catalog-table wazuh-rules-table"
		/>

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

		<n-drawer
			v-model:show="showTestLogLineDrawer"
			:width="700"
			class="max-w-[95vw]"
			placement="right"
			display-directive="show"
		>
			<n-drawer-content closable :native-scrollbar="false">
				<template #header>Test a log line</template>
				<WazuhLogTest @open-rule="openRuleById" />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns, SelectOption, TagProps } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { CatalogWazuhRuleRow } from "@/types/detection-catalog"
import {
	NAlert,
	NButton,
	NDataTable,
	NDrawer,
	NDrawerContent,
	NInput,
	NModal,
	NSelect,
	NTag,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Dot, { hitsToDotVariant } from "@/components/common/Dot.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter.ts"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"
import WazuhLogTest from "./WazuhLogTest.vue"
import WazuhRuleDetail from "./WazuhRuleDetail.vue"

const message = useMessage()
const { routeDetectionCatalogWazuhRule } = useNavigation()
const { globalCustomerCode } = useGlobalCustomerFilter()
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

const showTestLogLineDrawer = ref(false)
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
const deadCount = computed(() => rules.value.filter(r => r.hits_30d === 0 && (r.level ?? 0) >= 7).length)

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
	modalTitle.value = `Rule ${row.id}`
	showDetailModal.value = true
}

function openRuleById(ruleId: number) {
	const row = rules.value.find(r => r.id === ruleId)
	modalRuleId.value = ruleId
	modalTitle.value = row ? `Rule ${ruleId}${row.description ? ` — ${row.description}` : ""}` : `Rule ${ruleId}`
	showDetailModal.value = true
}

function levelTagType(level: number | null): TagProps["type"] {
	if (level === null || level === undefined) return "default"
	if (level >= 12) return "error"
	if (level >= 7) return "warning"
	if (level >= 3) return "info"
	return "default"
}

function renderRuleDescription(row: CatalogWazuhRuleRow) {
	if (!row.description) {
		return <span class="text-tertiary text-xs">(no description)</span>
	}
	return <span class="leading-snug">{row.description}</span>
}

function renderRuleGroups(row: CatalogWazuhRuleRow) {
	if (!row.groups.length) {
		return <span class="text-tertiary text-xs">—</span>
	}
	return (
		<div class="flex flex-wrap gap-1">
			{row.groups.slice(0, 3).map(g => (
				<NTag key={g} type="primary" size="small">
					{g}
				</NTag>
			))}
			{row.groups.length > 3 && <NTag size="small">{`+${row.groups.length - 3}`}</NTag>}
		</div>
	)
}

function renderRuleMitre(row: CatalogWazuhRuleRow) {
	if (!row.mitre.length) {
		return <span class="text-tertiary text-xs">—</span>
	}
	return (
		<div class="flex flex-wrap gap-1">
			{row.mitre.map(t => (
				<NTag key={t} size="small">
					{t}
				</NTag>
			))}
		</div>
	)
}

function loadCustomers() {
	loadingCustomers.value = true
	return Api.customers
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
					<Dot variant="muted" />
					<span class="text-secondary text-xs">No hits 30d</span>
				</div>
			)
		}
		return (
			<div class="flex items-center gap-2">
				<Dot variant={hitsToDotVariant(row.hits_30d)} />
				<div class="flex flex-col leading-tight">
					<span class="font-mono text-xs font-medium">{row.hits_30d.toLocaleString()}</span>
					<span class="text-secondary text-xs">{`${row.hits_7d.toLocaleString()} in 7d`}</span>
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
			fixed: "left",
			width: 100,
			sorter: (a, b) => (a.id ?? 0) - (b.id ?? 0),
			render: row => <span class="text-secondary font-mono text-xs">{row.id ?? "—"}</span>
		},
		{
			title: "Level",
			key: "level",
			width: 90,
			sorter: (a, b) => (a.level ?? 0) - (b.level ?? 0),
			render: row => (
				<NTag size="small" type={levelTagType(row.level)} bordered={false} class="font-mono font-bold">
					{row.level ?? "—"}
				</NTag>
			)
		},
		{
			title: "Description",
			key: "description",
			width: 400,
			render: renderRuleDescription
		},
		{
			title: "Groups",
			key: "groups",
			minWidth: 100,
			render: renderRuleGroups
		},
		{
			title: "MITRE",
			key: "mitre",
			width: 140,
			render: renderRuleMitre
		},
		{
			title: "File",
			key: "filename",
			width: 200,
			ellipsis: { tooltip: true },
			render: row => <span class="text-secondary font-mono text-xs">{row.filename || "—"}</span>
		}
	]
	if (firingStatsAvailable.value) cols.push(hitsColumn.value)
	cols.push({
		title: "",
		key: "actions",
		width: 110,
		fixed: "right",
		render: row => {
			if (typeof row.id !== "number") {
				return <span class="text-tertiary text-xs">—</span>
			}

			return (
				<div onClick={e => e.stopPropagation()}>
					<EntityDetailsButton
						size="tiny"
						url={routeDetectionCatalogWazuhRule(row.id).fullUrl()}
						onView={() => openRuleDetail(row)}
					/>
				</div>
			)
		}
	})
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
			message.error(getApiErrorMessage(err as ApiError) || "Failed to load Wazuh rules")
		})
		.finally(() => {
			loading.value = false
			refetchingForCustomer.value = false
		})
}

onBeforeMount(() => {
	loadCustomers().then(() => {
		const code = globalCustomerCode.value
		if (code) {
			customerScope.value = code
		}
		load()
	})
})
</script>
