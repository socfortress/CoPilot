<template>
	<div class="soc-management flex flex-col gap-4" data-testid="soc-management">
		<header class="flex flex-wrap items-end justify-between gap-4">
			<div class="flex min-w-0 flex-col gap-1">
				<h2 class="m-0 text-xl font-semibold">Service performance</h2>
				<p class="text-secondary m-0 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
					<span>{{ periodLabel }}</span>
					<span class="text-tertiary">·</span>
					<span>{{ scopeLabel }}</span>
					<template v-if="dashboard">
						<span class="text-tertiary">·</span>
						<span
							class="live-stamp inline-flex items-center gap-1.5 font-mono text-xs"
							:title="`Computed at ${generatedAt}`"
						>
							<span class="live-dot" :class="{ 'is-loading': loading }" />
							{{ loading ? "refreshing" : `computed ${generatedAt}` }}
						</span>
					</template>
				</p>
			</div>
			<div class="flex items-center gap-2">
				<n-button size="small" :disabled="loading" data-testid="soc-refresh" @click="refresh">
					<template #icon><Icon name="carbon:renew" /></template>
					Refresh
				</n-button>
				<n-button
					size="small"
					secondary
					:loading="exporting"
					:disabled="!dashboard"
					data-testid="soc-export"
					@click="exportReport"
				>
					<template #icon><Icon name="carbon:document-pdf" /></template>
					Report
				</n-button>
			</div>
		</header>

		<SocFilterBar
			v-model:preset="filters.preset.value"
			v-model:customer-codes="filters.customerCodes.value"
			v-model:severities="filters.severities.value"
			v-model:sources="filters.sources.value"
			:custom-range="filters.customRange.value"
			:range="filters.range.value"
			:customer-options
			:customers-loading
			:source-options
			@custom-range="filters.setCustomRange"
		/>

		<n-alert v-if="trackingNotice" type="info" :bordered="false" data-testid="tracking-notice">
			<template #icon><Icon name="carbon:time" /></template>
			{{ trackingNotice }}
		</n-alert>

		<n-alert v-if="error" type="error" :bordered="false" data-testid="soc-error">
			Could not load the dashboard: {{ errorText }}
		</n-alert>

		<n-tabs v-model:value="filters.tab.value" type="line" animated :tabs-padding="4" data-testid="soc-tabs">
			<n-tab-pane v-for="tab of TAB_DEFS" :key="tab.name" :name="tab.name" display-directive="show:lazy">
				<template #tab>
					<span class="inline-flex items-center gap-1.5" :data-testid="`soc-tab-${tab.name}`">
						<Icon :name="tab.icon" :size="15" />
						{{ tab.label }}
						<n-badge
							v-if="tab.name === 'workload' && dashboard?.workload.breached"
							:value="dashboard.workload.breached"
							:max="99"
							type="error"
						/>
					</span>
				</template>

				<PoliciesTab v-if="tab.name === 'policies'" @saved="reload" />
				<template v-else>
					<div v-if="!dashboard && loading" class="flex flex-col gap-4">
						<n-skeleton :height="240" :sharp="false" class="rounded-lg" />
						<div class="grid gap-4 xl:grid-cols-3">
							<n-skeleton :height="280" :sharp="false" class="rounded-lg xl:col-span-2" />
							<n-skeleton :height="280" :sharp="false" class="rounded-lg" />
						</div>
					</div>
					<div v-else-if="dashboard" class="tab-body" :class="{ 'is-stale': loading }" :aria-busy="loading">
						<OverviewTab v-if="tab.name === 'overview'" :dashboard @open-tab="filters.tab.value = $event" />
						<SlaTab v-else-if="tab.name === 'sla'" :dashboard />
						<AnalystsTab v-else-if="tab.name === 'analysts'" :dashboard />
						<RulesTab v-else-if="tab.name === 'rules'" :dashboard />
						<CustomersTab v-else-if="tab.name === 'customers'" :dashboard @focus-customer="focusCustomer" />
						<WorkloadTab v-else-if="tab.name === 'workload'" :dashboard :scope />
					</div>
				</template>
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
// SOC Management (#1187): one page, one snapshot. The filters live in the URL
// (useSocFilters); the dashboard is loaded once per change of filters
// (useSocDashboard) and every tab reads that same snapshot.
import type { SocScopeQuery } from "@/api/endpoints/soc-management"
import { saveAs } from "file-saver"
import { NAlert, NBadge, NButton, NSkeleton, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, onBeforeMount, shallowRef, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { dashboardKey, useSocDashboard } from "./composables/useSocDashboard"
import { useSocFilters } from "./composables/useSocFilters"
import SocFilterBar from "./SocFilterBar.vue"
import AnalystsTab from "./tabs/AnalystsTab.vue"
import CustomersTab from "./tabs/CustomersTab.vue"
import OverviewTab from "./tabs/OverviewTab.vue"
import PoliciesTab from "./tabs/PoliciesTab.vue"
import RulesTab from "./tabs/RulesTab.vue"
import SlaTab from "./tabs/SlaTab.vue"
import WorkloadTab from "./tabs/WorkloadTab.vue"
import { formatCount, parseUtc } from "./utils"

const TAB_DEFS = [
	{ name: "overview", label: "Overview", icon: "carbon:dashboard" },
	{ name: "sla", label: "SLA", icon: "carbon:timer" },
	{ name: "analysts", label: "Analysts", icon: "carbon:user-multiple" },
	{ name: "rules", label: "Detection rules", icon: "carbon:rule" },
	{ name: "customers", label: "Customers", icon: "carbon:enterprise" },
	{ name: "workload", label: "Workload", icon: "carbon:task" },
	{ name: "policies", label: "SLA policies", icon: "carbon:settings-adjust" }
] as const

const message = useMessage()
const filters = useSocFilters()
const { dashboard, loading, error, reload } = useSocDashboard(filters.query)
const { options: customerOptions, loading: customersLoading, load: loadCustomers } = useCustomerOptions()
const { globalCustomerCodes, onGlobalCustomerFilterChange } = useGlobalCustomerFilter()

const sourceOptions = shallowRef<{ label: string; value: string }[]>([])
const exporting = shallowRef(false)

const scope = computed<SocScopeQuery>(() => ({
	customerCodes: filters.customerCodes.value,
	severities: filters.severities.value,
	sources: filters.sources.value
}))

const periodLabel = computed(() => {
	const { from, to } = filters.range.value
	const format = to.getTime() - from.getTime() <= 2 * 86_400_000 ? "D MMM HH:mm" : "D MMM YYYY"
	return `${parseUtc(from.toISOString())?.local().format(format)} → ${parseUtc(to.toISOString())?.local().format(format)}`
})

/** What the figures cover: the server's answer, since a scoped analyst asking for "all" gets theirs. */
const scopeLabel = computed(() => {
	const codes = filters.customerCodes.value.length ? filters.customerCodes.value : dashboard.value?.customer_codes
	if (!codes) return "all customers"
	if (!codes.length) return "no customer"
	return codes.length <= 2 ? codes.join(", ") : `${codes.length} customers`
})

const generatedAt = computed(() => parseUtc(dashboard.value?.generated_at)?.local().format("HH:mm:ss") ?? "")

const trackingNotice = computed(() => {
	const since = parseUtc(dashboard.value?.tracking_since)
	if (!dashboard.value) return null
	if (!since) return "SLA tracking starts with the next alert or case: earlier items count in volumes only."
	if (since.valueOf() <= filters.range.value.from.getTime()) return null
	return `SLA tracking began ${since.local().format("D MMM YYYY, HH:mm")}. Items opened before then count in volumes and the backlog, but in no time or SLA figure.`
})

const errorText = computed(() => {
	const err = error.value as { response?: { data?: { detail?: string } }; message?: string } | null
	return err?.response?.data?.detail ?? err?.message ?? "unknown error"
})

/** A rolling window ends "now": move it, and reload even when it lands on the same minute. */
function refresh() {
	const before = dashboardKey(filters.query.value)
	filters.refresh()
	if (dashboardKey(filters.query.value) === before) reload()
}

function focusCustomer(code: string) {
	filters.customerCodes.value = [code]
	filters.tab.value = "overview"
}

async function exportReport() {
	exporting.value = true
	try {
		const response = await Api.socManagement.downloadReport(filters.query.value)
		const { from, to } = filters.range.value
		saveAs(response.data, `soc_report_${from.toISOString().slice(0, 10)}_${to.toISOString().slice(0, 10)}.pdf`)
	} catch {
		message.error("Could not generate the report")
	} finally {
		exporting.value = false
	}
}

/**
 * The source filter offers the sources the alerts in view actually come from — not the
 * configured ingest sources, which miss manual / threshold / UBA alerts and ignore the
 * caller's scope — reloaded when the customers in view change.
 */
let sourcesController: AbortController | null = null
async function loadSources(customerCodes: string[]) {
	sourcesController?.abort()
	const controller = new AbortController()
	sourcesController = controller
	try {
		const sources = (await Api.socManagement.getSources(customerCodes, controller.signal)).data.sources ?? []
		sourceOptions.value = sources.map(({ source, alerts }) => ({ label: `${source} · ${formatCount(alerts)}`, value: source }))
	} catch {
		if (controller.signal.aborted) return
		sourceOptions.value = [] // the filter is optional; the page works without it
	}
}

watch(
	() => [...filters.customerCodes.value],
	codes => loadSources(codes)
)

// The sidebar's customer filter seeds the page when the URL names none, and — with live
// sync on — wins over the local one. An emptied selection means "all customers" here.
onGlobalCustomerFilterChange(codes => {
	filters.customerCodes.value = codes
})

onBeforeMount(() => {
	if (!filters.hasCustomerInUrl.value && globalCustomerCodes.value.length) {
		filters.customerCodes.value = [...globalCustomerCodes.value]
	}
	loadCustomers()
	loadSources(filters.customerCodes.value)
})
</script>

<style scoped>
.live-dot {
	width: 7px;
	height: 7px;
	border-radius: 50%;
	background-color: var(--success-color);
	box-shadow: 0 0 0 0 rgb(var(--success-color-rgb) / 0.6);
	animation: soc-pulse 2.4s infinite;
}

.live-dot.is-loading {
	background-color: var(--primary-color);
	animation-duration: 0.9s;
}

.tab-body {
	transition: opacity 0.2s ease;
}

.tab-body.is-stale {
	opacity: 0.55;
	pointer-events: none;
}

@keyframes soc-pulse {
	0% {
		box-shadow: 0 0 0 0 rgb(var(--success-color-rgb) / 0.55);
	}
	70% {
		box-shadow: 0 0 0 6px rgb(var(--success-color-rgb) / 0);
	}
	100% {
		box-shadow: 0 0 0 0 rgb(var(--success-color-rgb) / 0);
	}
}

@media (prefers-reduced-motion: reduce) {
	.live-dot {
		animation: none;
	}
}
</style>
