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
				v-if="showCustomerSelect"
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
		<div v-if="showActivity" class="flex flex-wrap gap-2">
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

		<!-- Why the Activity column is missing: hit counts still loading, or the indexer could not count them. -->
		<n-alert
			v-if="!loading && available && activityNotice"
			:type="activityNotice.type"
			show-icon
			data-testid="activity-notice"
		>
			<template v-if="activityNotice.type === 'info'" #icon>
				<n-spin :size="16" />
			</template>
			<template #header>{{ activityNotice.title }}</template>
			<span class="whitespace-pre-wrap">{{ activityNotice.body }}</span>
		</n-alert>

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
			<template #header-extra>
				<ModalPageButton
					:route="modalRuleId !== null ? routeDetectionCatalogWazuhRule(modalRuleId) : null"
					label="Open the rule's page"
					@navigate="modalRuleId = null"
				/>
			</template>
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
import type { CatalogWazuhRuleRow, CatalogWazuhRulesResponse } from "@/types/detection-catalog"
import axios from "axios"
import {
	NAlert,
	NButton,
	NDataTable,
	NDrawer,
	NDrawerContent,
	NInput,
	NModal,
	NSelect,
	NSpin,
	NTag,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Dot, { hitsToDotVariant } from "@/components/common/Dot.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import ModalPageButton from "@/components/common/ModalPageButton.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter.ts"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"
import WazuhLogTest from "./WazuhLogTest.vue"
import WazuhRuleDetail from "./WazuhRuleDetail.vue"

const message = useMessage()
const { routeDetectionCatalogWazuhRule } = useNavigation()
const { globalCustomerCode, onGlobalCustomerFilterChange } = useGlobalCustomerFilter()
const rules = ref<CatalogWazuhRuleRow[]>([])
// True until the first answer: the customer list is read first, and the notices
// below would otherwise judge the hit counts before anything was asked.
const loading = ref(true)
const filter = ref("")

const available = ref(true)
const unavailableReason = ref<string | null>(null)
// Unknown until the first answer: starting at `true` showed the Activity
// column for a moment and then took it away (#1319).
const firingStatsAvailable = ref(false)
const firingStatsLoading = ref(false)
const firingStatsUnavailableReason = ref<string | null>(null)
const customerStatsStatus = ref<CatalogWazuhRulesResponse["customer_firing_stats_status"]>(null)
const customerStatsError = ref<string | null>(null)

type ChipKey = "all" | "noisy" | "dead"
const activeChip = ref<ChipKey>("all")

const customerScope = ref<string>("")
const customerOptions = ref<SelectOption[]>([{ label: "All customers", value: "" }])
const loadingCustomers = ref(false)
const refetchingForCustomer = ref(false)

// Hit counts are computed in the background: until they land the answer says
// so (`firing_stats_loading`, or a customer slice `loading`), and the tab asks
// again with `limit: 1` — the full ruleset is several MB — then reloads once.
// The ceiling covers FIRING_STATS_TIMEOUT_SECONDS at its 600s maximum plus a
// search queued behind another one.
const STATS_POLL_MS = 5000
const STATS_MAX_POLLS = 300

let abortController: AbortController | null = null
let pollTimer: ReturnType<typeof setTimeout> | null = null
let pollsLeft = STATS_MAX_POLLS

const showTestLogLineDrawer = ref(false)
const modalRuleId = ref<number | null>(null)
// The modal is open exactly when a rule is selected — closing it clears the selection.
const showDetailModal = computed({
	get: () => modalRuleId.value !== null,
	set: (open: boolean) => {
		if (!open) modalRuleId.value = null
	}
})
const modalTitle = computed(() => {
	if (modalRuleId.value === null) return "Wazuh Rule"

	const row = rules.value.find(r => r.id === modalRuleId.value)
	return `Rule ${modalRuleId.value}${row?.description ? ` — ${row.description}` : ""}`
})

const pagination = {
	pageSize: 50,
	pageSizes: [25, 50, 100, 200],
	showSizePicker: true
}

// Count of "dead" rules for the chip badge — keeps the analyst informed of
// how many candidates the filter would surface before clicking.
const deadCount = computed(() => rules.value.filter(r => r.hits_30d === 0 && (r.level ?? 0) >= 7).length)

// Hit counts mean something only when the global counts are loaded and, with a
// customer picked, that customer's slice has landed. Anything else would show
// "No hits 30d" for every rule.
const showActivity = computed(
	() => firingStatsAvailable.value && (!customerScope.value || customerStatsStatus.value === "ready")
)
// Kept while a customer is picked, so the scope can always be set back to all customers.
const showCustomerSelect = computed(() => firingStatsAvailable.value || !!customerScope.value)

const customerLabel = computed(() => {
	const option = customerOptions.value.find(o => o.value === customerScope.value)
	return (option?.label as string | undefined) || customerScope.value
})

const activityNotice = computed<{ type: "info" | "warning"; title: string; body: string } | null>(() => {
	if (firingStatsLoading.value) {
		return {
			type: "info",
			title: "Counting rule hits",
			body: "The Activity column appears once the indexer has counted the last 30 days of alerts."
		}
	}
	if (!firingStatsAvailable.value) {
		return {
			type: "warning",
			title: "Rule hit counts unavailable",
			body: firingStatsUnavailableReason.value || "The Wazuh indexer could not count rule hits."
		}
	}
	if (customerScope.value && customerStatsStatus.value === "loading") {
		return {
			type: "info",
			title: `Counting hits for ${customerLabel.value}`,
			body: "This can take a while on a large cluster. The Activity column appears once the count is done."
		}
	}
	if (customerScope.value && customerStatsStatus.value === "error") {
		return {
			type: "warning",
			title: `Hit counts for ${customerLabel.value} unavailable`,
			body: customerStatsError.value || "The Wazuh indexer could not count this customer's rule hits."
		}
	}
	return null
})

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

	// The chips sort and filter on hit counts: without them, every rule would be "dead".
	const chip = showActivity.value ? activeChip.value : "all"
	if (chip === "noisy") {
		return [...textFiltered].sort((a, b) => b.hits_30d - a.hits_30d).slice(0, 50)
	}
	if (chip === "dead") {
		return textFiltered.filter(r => r.hits_30d === 0 && (r.level ?? 0) >= 7)
	}
	return textFiltered
})

function openRuleDetail(row: CatalogWazuhRuleRow) {
	if (typeof row.id !== "number") return
	modalRuleId.value = row.id
}

function openRuleById(ruleId: number) {
	modalRuleId.value = ruleId
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
		.getCustomers({})
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
	pollsLeft = STATS_MAX_POLLS
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
			ellipsis: { tooltip: { to: "body", contentClass: "max-w-[70vw] text-sm!" } },
			render: row => <span class="text-secondary font-mono text-xs">{row.filename || "—"}</span>
		}
	]
	if (showActivity.value) cols.push(hitsColumn.value)
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
						route={routeDetectionCatalogWazuhRule(row.id)}
						onView={() => openRuleDetail(row)}
					/>
				</div>
			)
		}
	})
	return cols
})

function stopPolling() {
	if (pollTimer !== null) {
		clearTimeout(pollTimer)
		pollTimer = null
	}
}

function statsPending(data: CatalogWazuhRulesResponse) {
	return data.firing_stats_loading || data.customer_firing_stats_status === "loading"
}

function applyStats(data: CatalogWazuhRulesResponse) {
	firingStatsAvailable.value = data.firing_stats_available
	firingStatsLoading.value = data.firing_stats_loading
	firingStatsUnavailableReason.value = data.firing_stats_unavailable_reason
	customerStatsStatus.value = data.customer_firing_stats_status
	customerStatsError.value = data.customer_firing_stats_error
}

function schedulePoll() {
	if (pollsLeft <= 0) return
	pollsLeft -= 1
	pollTimer = setTimeout(pollStats, STATS_POLL_MS)
}

function pollStats() {
	pollTimer = null
	const signal = abortController?.signal
	Api.detectionCatalog
		.listWazuhRules({ customerCode: customerScope.value || undefined, limit: 1 }, signal)
		.then(res => {
			if (!res.data?.success) return
			if (statsPending(res.data)) {
				applyStats(res.data)
				schedulePoll()
				return
			}
			// The counts landed: one full read to put them on the rows.
			load(true)
		})
		.catch(err => {
			if (axios.isCancel(err)) return
			schedulePoll()
		})
}

function load(isCustomerChange = false) {
	abortController?.abort()
	abortController = new AbortController()
	stopPolling()
	if (!isCustomerChange) loading.value = true
	Api.detectionCatalog
		.listWazuhRules({ customerCode: customerScope.value || undefined }, abortController.signal)
		.then(res => {
			if (res.data?.success) {
				rules.value = res.data.rules || []
				available.value = res.data.available
				unavailableReason.value = res.data.unavailable_reason
				applyStats(res.data)
				if (statsPending(res.data)) schedulePoll()
			} else {
				message.warning(res.data?.message || "Failed to load Wazuh rules")
			}
			loading.value = false
			refetchingForCustomer.value = false
		})
		.catch(err => {
			if (axios.isCancel(err)) return
			message.error(getApiErrorMessage(err as ApiError) || "Failed to load Wazuh rules")
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

// An emptied global selection resets the scope to "all customers".
onGlobalCustomerFilterChange(codes => {
	const code = codes[0] || ""

	if (code !== customerScope.value) {
		onCustomerChange(code)
	}
})

onBeforeUnmount(() => {
	stopPolling()
	abortController?.abort()
})
</script>
