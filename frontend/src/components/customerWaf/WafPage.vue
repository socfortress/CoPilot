<template>
	<div class="flex flex-col gap-4">
		<!-- Level 1: the page — what it is, and which customer / WAF it shows. -->
		<header
			class="mt-4 flex flex-wrap items-end justify-between gap-4 lg:flex-nowrap"
			data-testid="waf-page-header"
		>
			<div class="flex min-w-0 grow basis-96 flex-col gap-1.5">
				<h2 class="m-0 text-xl leading-none font-semibold">WAF</h2>
				<p class="text-secondary m-0 max-w-2xl text-sm">
					Web attacks seen by customers' SOCFortress WAFs, the WAF's own threat intel, and IP blocks.
				</p>
			</div>
			<div v-if="customerOptions.length" class="flex shrink-0 flex-wrap items-center gap-2">
				<n-select
					v-model:value="customerModel"
					:options="customerOptions"
					filterable
					class="w-64!"
					aria-label="Customer"
					data-testid="waf-customer"
				>
					<template #arrow><Icon :name="CustomerIcon" :size="14" /></template>
				</n-select>
				<n-select
					v-if="wafsOfCustomer.length > 1"
					v-model:value="wafModel"
					:options="wafOptions"
					class="w-48!"
					aria-label="WAF"
					data-testid="waf-instance"
				>
					<template #arrow><Icon :name="ShieldIcon" :size="14" /></template>
				</n-select>
			</div>
		</header>

		<CustomerWafError v-if="error" :error />

		<n-spin :show="loading" class="min-h-40">
			<n-empty
				v-if="!loading && !error && !instances.length"
				description="No customer has a WAF configured yet"
				class="py-10"
			>
				<template #extra>
					<p class="text-secondary max-w-md text-sm">
						Add one under
						<b>Customers → a customer → WAF</b>
						with the WAF's URL and a service token.
					</p>
				</template>
			</n-empty>

			<template v-else-if="selected">
				<!--
					Level 2: the selected WAF — identity and state on the first line, then its facts in
					one hairline grid (the Overview's "Last hour" pattern), labels over values.
				-->
				<section
					class="border-default bg-default mb-4 overflow-hidden rounded-lg border"
					data-testid="waf-instance-panel"
				>
					<div class="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
						<span
							class="size-2 shrink-0 rounded-full ring-4"
							:class="statusDot.class"
							:title="statusDot.title"
							data-testid="waf-status-dot"
						/>
						<h3 class="text-default m-0 min-w-0 truncate text-base font-semibold">{{ selected.name }}</h3>
						<n-tag :type="wafCapabilityLabel(selected).type" size="small" round :bordered="false">
							<template #icon><Icon :name="CapabilityIcon" :size="12" /></template>
							{{ wafCapabilityLabel(selected).label }}
						</n-tag>
						<n-tag v-if="!selected.enabled" type="warning" size="small" round :bordered="false">
							disabled
						</n-tag>
						<!-- The wrapper takes the auto margin: Naive's button styles reset the button's own. -->
						<div class="ml-auto">
							<n-button
								size="small"
								secondary
								@click="routeCustomer({ code: selected.customer_code, tab: 'WAF' }).navigate()"
							>
								<template #icon>
									<Icon :name="SettingsIcon" />
								</template>
								{{ isAdmin ? "Configure" : "Connection details" }}
							</n-button>
						</div>
					</div>
					<dl class="bg-border border-default m-0 grid grid-cols-2 gap-px border-t" :class="FACT_COLUMNS">
						<div
							v-for="fact of facts"
							:key="fact.label"
							class="bg-default flex min-w-0 flex-col gap-1 px-4 py-2.5"
							:class="fact.wide ? 'col-span-2 lg:col-span-1' : ''"
							:data-testid="`waf-fact-${fact.key}`"
						>
							<dt class="text-tertiary text-2xs font-medium tracking-[0.12em] uppercase">
								{{ fact.label }}
							</dt>
							<dd class="m-0 flex min-w-0 flex-wrap items-baseline gap-x-2 text-sm">
								<span
									class="truncate"
									:class="fact.mono ? 'font-mono text-xs' : 'text-default'"
									:title="fact.value"
								>
									{{ fact.value }}
								</span>
								<span v-if="fact.hint" class="text-tertiary font-mono text-xs whitespace-nowrap">
									{{ fact.hint }}
								</span>
							</dd>
						</div>
					</dl>
				</section>

				<n-alert v-if="!selected.enabled" type="info" :bordered="false">
					This WAF is disabled in CoPilot. An administrator can enable it from the customer's WAF tab.
				</n-alert>

				<n-tabs v-else v-model:value="tabModel" type="line" animated>
					<n-tab-pane name="overview" tab="Overview" display-directive="show:lazy">
						<CustomerWafOverview
							:key="`o${selected.id}`"
							:customer-code="selected.customer_code"
							:instance="selected"
							@view-events="viewEventsFor"
							@blocked="blocksKey++"
						/>
					</n-tab-pane>
					<n-tab-pane name="events" tab="Events" display-directive="show:lazy">
						<CustomerWafEvents
							:key="`e${selected.id}-${ipQuery ?? ''}`"
							:customer-code="selected.customer_code"
							:instance="selected"
							:initial-client-ip="ipQuery"
						/>
					</n-tab-pane>
					<n-tab-pane name="threat-intel" tab="Threat intel" display-directive="show:lazy">
						<CustomerWafThreatIntel
							:key="`t${selected.id}`"
							:customer-code="selected.customer_code"
							:instance="selected"
							@blocked="blocksKey++"
						/>
					</n-tab-pane>
					<n-tab-pane name="blocks" tab="Blocks" display-directive="show:lazy">
						<CustomerWafBlocks
							:key="`b${selected.id}-${blocksKey}`"
							:customer-code="selected.customer_code"
							:instance="selected"
						/>
					</n-tab-pane>
					<n-tab-pane name="sites" tab="Sites" display-directive="show:lazy">
						<CustomerWafSites
							:key="`s${selected.id}`"
							:customer-code="selected.customer_code"
							:instance="selected"
						/>
					</n-tab-pane>
				</n-tabs>
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerWafInstance } from "@/types/customer-waf"
import { NAlert, NButton, NEmpty, NSelect, NSpin, NTabPane, NTabs, NTag } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { useNavigation, useRouteQueryParam } from "@/composables/useNavigation"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"
import CustomerWafBlocks from "./CustomerWafBlocks.vue"
import CustomerWafError from "./CustomerWafError.vue"
import CustomerWafEvents from "./CustomerWafEvents.vue"
import CustomerWafOverview from "./CustomerWafOverview.vue"
import CustomerWafSites from "./CustomerWafSites.vue"
import CustomerWafThreatIntel from "./CustomerWafThreatIntel.vue"
import { wafCapabilityLabel } from "./utils"

const TABS = ["overview", "events", "threat-intel", "blocks", "sites"] as const
const SettingsIcon = "carbon:settings"
const ShieldIcon = "carbon:security"
const CapabilityIcon = "carbon:locked"
const CustomerIcon = "carbon:enterprise"
// The facts' columns on a wide screen, sized to what each holds; narrow, two per row with
// customer, endpoint and forwarding taking a whole row each, so no cell is left empty.
const FACT_COLUMNS = "lg:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)_minmax(0,1.4fr)_minmax(0,0.9fr)_minmax(0,1fr)]"
const dFormats = useSettingsStore().dateFormat

const route = useRoute()
const router = useRouter()
const { routeCustomer } = useNavigation()
const { getAvailableGlobalCustomerValue, onGlobalCustomerFilterChange } = useGlobalCustomerFilter()
const isAdmin = computed(() => useAuthStore().isAdmin)

const loading = ref(false)
const error = ref<ApiError | null>(null)
const instances = ref<CustomerWafInstance[]>([])
const customerNames = ref<Record<string, string>>({})
const blocksKey = ref(0)

// Customer, WAF and tab live in the URL so a view can be linked and survives a reload.
// Picker changes use replace: they refine this page, they aren't a new place to go back to.
const customerQuery = useRouteQueryParam("customer")
const wafQuery = useRouteQueryParam("waf")
const tabQuery = useRouteQueryParam("tab")
const ipQuery = useRouteQueryParam("ip")

function setQuery(patch: Record<string, string | undefined>) {
	router.replace({ query: { ...route.query, ...patch } })
}

const customerCodes = computed(() => [...new Set(instances.value.map(i => i.customer_code))])
const customerOptions = computed(() =>
	customerCodes.value.map(code => ({
		label: customerNames.value[code] ? `${customerNames.value[code]} (${code})` : code,
		value: code
	}))
)

const customerModel = computed<string | null>({
	get: () => (customerQuery.value && customerCodes.value.includes(customerQuery.value) ? customerQuery.value : null),
	set: code => setQuery({ customer: code ?? undefined, waf: undefined, ip: undefined })
})

const wafsOfCustomer = computed(() => instances.value.filter(i => i.customer_code === customerModel.value))
const wafOptions = computed(() => wafsOfCustomer.value.map(i => ({ label: i.name, value: i.id })))

const selected = computed<CustomerWafInstance | null>(() => {
	const list = wafsOfCustomer.value
	const fromQuery = list.find(i => String(i.id) === wafQuery.value)
	return fromQuery ?? list.find(i => i.enabled) ?? list[0] ?? null
})

const wafModel = computed<number | null>({
	get: () => selected.value?.id ?? null,
	set: id => setQuery({ waf: id != null ? String(id) : undefined, ip: undefined })
})

const tabModel = computed<string>({
	get: () => ((TABS as readonly string[]).includes(tabQuery.value ?? "") ? (tabQuery.value as string) : "overview"),
	set: tab => setQuery({ tab, ip: tab === "events" ? ipQuery.value : undefined })
})

/** The selected WAF's facts, in reading order: whose it is, where it is, how CoPilot reaches it. */
const facts = computed(() => {
	const waf = selected.value
	if (!waf) return []
	const name = customerNames.value[waf.customer_code]
	return [
		{
			key: "customer",
			label: "Customer",
			value: name ?? waf.customer_code,
			hint: name ? waf.customer_code : null,
			mono: false,
			wide: true
		},
		{ key: "endpoint", label: "Endpoint", value: waf.api_url, hint: null, mono: true, wide: true },
		{
			key: "verified",
			label: "Last verified",
			value: waf.last_verified_at ? String(formatDate(waf.last_verified_at, dFormats.datetime)) : "never",
			hint: waf.last_verified_at ? dayjs(waf.last_verified_at).fromNow() : null,
			mono: true,
			wide: false
		},
		{ key: "token", label: "Service token", value: `${waf.token_prefix}…`, hint: null, mono: true, wide: false },
		{
			key: "forwarding",
			label: "SIEM forwarding",
			value: waf.syslog_host ? `${waf.syslog_host}:${waf.syslog_port ?? "—"}` : "not set up",
			hint: null,
			mono: Boolean(waf.syslog_host),
			wide: true
		}
	]
})

/** Online (enabled and verified), waiting for a first check, or switched off — never colour alone: it has a title. */
const statusDot = computed(() => {
	const waf = selected.value
	if (!waf?.enabled) return { class: "bg-warning ring-warning/15", title: "Disabled in CoPilot" }
	if (!waf.last_verified_at) return { class: "bg-tertiary ring-border", title: "Never verified" }
	return { class: "bg-success ring-success/15", title: "Enabled and verified" }
})

/** Overview → "Events from this IP": opens Events pre-filtered. push, not replace: it's a new place to go back from. */
function viewEventsFor(clientIp: string) {
	router.push({ query: { ...route.query, tab: "events", ip: clientIp } })
}

/** The customer to show when the URL doesn't name one we have: the global filter's, else the first. */
function defaultCustomer(): string | undefined {
	return getAvailableGlobalCustomerValue(customerCodes.value) ?? customerCodes.value[0]
}

// The sidebar filter wins when it names a customer with a WAF. An emptied or WAF-less
// selection keeps the current customer: this page renders nothing without one.
onGlobalCustomerFilterChange(codes => {
	const match = codes.find(c => customerCodes.value.includes(c))
	if (match && match !== customerModel.value) setQuery({ customer: match, waf: undefined })
})

function load() {
	loading.value = true
	error.value = null
	Promise.all([
		Api.customerWaf.getAllInstances(),
		Api.customers.getCustomers({}).catch(() => null) // names are a nicety; codes still work without them
	])
		.then(([wafs, customers]) => {
			instances.value = wafs.data.instances
			customerNames.value = Object.fromEntries(
				(customers?.data.customers ?? []).map(c => [c.customer_code, c.customer_name])
			)
			if (!customerModel.value && customerCodes.value.length) {
				setQuery({ customer: defaultCustomer(), waf: undefined })
			}
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(load)
</script>
