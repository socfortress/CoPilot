<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div class="flex flex-col gap-1">
				<h2 class="text-lg font-semibold">WAF</h2>
				<p class="text-secondary text-sm">
					Web attacks seen by customers' SOCFortress WAFs, the WAF's own threat intel, and IP blocks.
				</p>
			</div>
			<div v-if="customerOptions.length" class="flex flex-wrap items-end gap-3">
				<n-form-item label="Customer" :show-feedback="false" class="w-64">
					<n-select v-model:value="customerModel" :options="customerOptions" filterable />
				</n-form-item>
				<n-form-item v-if="wafsOfCustomer.length > 1" label="WAF" :show-feedback="false" class="w-56">
					<n-select v-model:value="wafModel" :options="wafOptions" />
				</n-form-item>
			</div>
		</div>

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
				<!-- One uniform strip of facts about the selected WAF, like File Analysis's header. -->
				<header class="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2">
					<n-tag :type="wafCapabilityLabel(selected).type" size="medium" round :bordered="false">
						<template #icon><Icon :name="ShieldIcon" :size="14" /></template>
						{{ wafCapabilityLabel(selected).label }}
					</n-tag>
					<h3 class="text-default min-w-0 truncate text-base font-semibold">{{ selected.name }}</h3>
					<div class="flex flex-wrap items-center gap-2">
						<Badge type="splitted" size="small">
							<template #iconLeft><Icon :name="CustomerIcon" :size="12" /></template>
							<template #label>customer</template>
							<template #value>{{ selected.customer_code }}</template>
						</Badge>
						<Badge type="splitted" size="small">
							<template #iconLeft><Icon :name="LinkIcon" :size="12" /></template>
							<template #value><span class="font-mono">{{ selected.api_url }}</span></template>
						</Badge>
						<Badge v-if="selected.last_verified_at" type="splitted" size="small">
							<template #iconLeft><Icon :name="TimeIcon" :size="12" /></template>
							<template #label>verified</template>
							<template #value>{{ formatDate(selected.last_verified_at, dFormats.datetime) }}</template>
						</Badge>
						<Badge v-if="!selected.enabled" type="splitted" size="small" color="warning">
							<template #value>disabled</template>
						</Badge>
					</div>
					<n-button
						size="small"
						secondary
						class="ml-auto"
						@click="routeCustomer({ code: selected.customer_code, tab: 'WAF' }).navigate()"
					>
						<template #icon>
							<Icon :name="SettingsIcon" />
						</template>
						{{ isAdmin ? "Configure" : "Connection details" }}
					</n-button>
				</header>

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
						<CustomerWafSites :key="`s${selected.id}`" :customer-code="selected.customer_code" :instance="selected" />
					</n-tab-pane>
				</n-tabs>
			</template>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerWafInstance } from "@/types/customer-waf"
import { NAlert, NButton, NEmpty, NFormItem, NSelect, NSpin, NTabPane, NTabs, NTag } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { useNavigation, useRouteQueryParam } from "@/composables/useNavigation"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
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
const CustomerIcon = "carbon:user-multiple"
const LinkIcon = "carbon:link"
const TimeIcon = "carbon:time"
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
	get: () => (TABS as readonly string[]).includes(tabQuery.value ?? "") ? (tabQuery.value as string) : "overview",
	set: tab => setQuery({ tab, ip: tab === "events" ? ipQuery.value : undefined })
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
