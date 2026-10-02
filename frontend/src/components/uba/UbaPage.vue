<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-wrap items-end justify-between gap-4">
			<div class="flex flex-col gap-1">
				<h2 class="text-lg font-semibold">User Behavior Analytics</h2>
				<p class="text-secondary text-sm">
					Users and hosts ranked by behavioral risk from SOCFortress UBA, its alerts, and suppressions.
				</p>
			</div>
			<n-form-item v-if="available && customerOptions.length" label="Customer" :show-feedback="false" class="w-64">
				<n-select v-model:value="customerModel" :options="customerOptions" filterable />
			</n-form-item>
		</div>

		<n-spin v-if="!availabilityLoaded" class="min-h-40" show />

		<n-empty v-else-if="!available" description="SOCFortress UBA is not connected" class="py-10">
			<template #extra>
				<p class="text-secondary max-w-md text-sm">
					Configure the
					<b>SOCFortress UBA</b>
					connector under
					<b>Platform → Connectors</b>
					with the UBA API's URL and an API key (`uba-admin api-keys create --name copilot --scope admin --tenants
					'*'`; scope admin lets admins set customers up from this page), then verify it.
				</p>
			</template>
		</n-empty>

		<template v-else-if="customerModel">
			<UbaError v-if="statusError" :error="statusError" />
			<header v-else-if="status" class="flex flex-wrap items-center gap-2">
				<Badge type="splitted" size="small">
					<template #label>open alerts</template>
					<template #value>{{ status.open_alerts }}</template>
				</Badge>
				<Badge type="splitted" size="small">
					<template #label>alerts 24 h</template>
					<template #value>{{ status.alerts_24h }}</template>
				</Badge>
				<Badge type="splitted" size="small">
					<template #label>signals 24 h</template>
					<template #value>{{ status.signals_24h }}</template>
				</Badge>
				<Badge type="splitted" size="small" :color="(status.lag_seconds ?? 0) > 600 ? 'warning' : undefined">
					<template #label>processing lag</template>
					<template #value>{{ formatLag(status.lag_seconds) }}</template>
				</Badge>
				<Badge
					v-for="feed of status.feeds ?? []"
					:key="feed.source"
					type="splitted"
					size="small"
					:color="feed.status === 'ok' ? undefined : 'warning'"
					:title="feedTitle(feed)"
				>
					<template #label>{{ feedLabel(feed.source) }}</template>
					<template #value>{{ feed.status === "ok" ? formatLag(feed.lag_p50_s) : feed.status }}</template>
				</Badge>
				<span v-if="version" class="text-tertiary text-xs">UBA {{ version }}</span>
			</header>
			<!-- Not set up yet (no status row), or still learning from history: setup and progress. -->
			<UbaSetup
				v-if="needsSetup"
				:key="`setup${customerModel}`"
				:customer-code="customerModel"
				@live="loadStatus(customerModel)"
			/>
			<n-alert v-if="unhealthyFeeds.length" type="warning" :bordered="false">
				<p v-for="feed of unhealthyFeeds" :key="feed.source">
					<b>{{ feedLabel(feed.source) }}</b>
					is {{ feed.status }}: {{ feed.reasons.join("; ") }}.
				</p>
				<p class="text-secondary mt-1 text-xs">
					UBA's findings for this source may be missing or late until the feed recovers.
				</p>
			</n-alert>

			<UbaAbout :key="`about${customerModel}`" :customer-code="customerModel" />

			<n-tabs v-model:value="tabModel" type="line" animated>
				<n-tab-pane name="entities" tab="Entities" display-directive="show:lazy">
					<UbaEntities :key="`e${customerModel}`" :customer-code="customerModel" @open="openEntity" />
				</n-tab-pane>
				<n-tab-pane name="alerts" tab="Alerts" display-directive="show:lazy">
					<UbaAlerts :key="`a${customerModel}`" :customer-code="customerModel" :refresh-key @open="openAlert" />
				</n-tab-pane>
				<n-tab-pane name="suppressions" tab="Suppressions" display-directive="show:lazy">
					<UbaSuppressions
						:key="`s${customerModel}`"
						:customer-code="customerModel"
						:refresh-key
						@open-entity="openEntity"
					/>
				</n-tab-pane>
				<n-tab-pane name="rules" tab="Rules" display-directive="show:lazy">
					<UbaRules :key="`r${customerModel}`" :customer-code="customerModel" />
				</n-tab-pane>
				<n-tab-pane name="directory" tab="Directory" display-directive="show:lazy">
					<UbaDirectory :key="`d${customerModel}`" :customer-code="customerModel" />
				</n-tab-pane>
			</n-tabs>

			<n-drawer :show="!!drawer" :width="720" class="max-w-[95vw]" @update:show="show => !show && closeDrawer()">
				<n-drawer-content v-if="drawer" :title="drawer.kind === 'entity' ? 'Entity' : 'UBA alert'" closable>
					<UbaEntityDetail
						v-if="drawer.kind === 'entity'"
						:key="drawer.id"
						:customer-code="customerModel"
						:entity-key="drawer.id"
						@open-alert="openAlert"
						@changed="refreshKey++"
					/>
					<UbaAlertDetail
						v-else
						:key="drawer.id"
						:customer-code="customerModel"
						:alert-id="drawer.id"
						@open-entity="openEntity"
						@changed="refreshKey++"
					/>
				</n-drawer-content>
			</n-drawer>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { UbaFeedStatus, UbaTenantStatus } from "@/types/uba"
import { NAlert, NDrawer, NDrawerContent, NEmpty, NFormItem, NSelect, NSpin, NTabPane, NTabs } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { useRouteQueryParam } from "@/composables/useNavigation"
import { useUbaAvailability } from "@/composables/useUbaAvailability"
import UbaAbout from "./UbaAbout.vue"
import UbaAlertDetail from "./UbaAlertDetail.vue"
import UbaAlerts from "./UbaAlerts.vue"
import UbaDirectory from "./UbaDirectory.vue"
import UbaEntities from "./UbaEntities.vue"
import UbaEntityDetail from "./UbaEntityDetail.vue"
import UbaError from "./UbaError.vue"
import UbaRules from "./UbaRules.vue"
import UbaSetup from "./UbaSetup.vue"
import UbaSuppressions from "./UbaSuppressions.vue"
import { formatLag } from "./utils"

const TABS = ["entities", "alerts", "suppressions", "rules", "directory"] as const

const route = useRoute()
const router = useRouter()
const { available, loaded: availabilityLoaded } = useUbaAvailability()
const { getAvailableGlobalCustomerValue, onGlobalCustomerFilterChange } = useGlobalCustomerFilter()

const customers = ref<{ code: string; name: string }[]>([])
const status = ref<UbaTenantStatus | null>(null)
const version = ref("")
const statusLoaded = ref(false)
const statusError = ref<ApiError | null>(null)
const refreshKey = ref(0)

// Customer, tab and the open entity/alert live in the URL so a view can be linked and survives a
// reload. Picker changes replace; opening a drawer pushes (browser back closes it).
const customerQuery = useRouteQueryParam("customer")
const tabQuery = useRouteQueryParam("tab")
const entityQuery = useRouteQueryParam("entity")
const alertQuery = useRouteQueryParam("alert")

function setQuery(patch: Record<string, string | undefined>) {
	router.replace({ query: { ...route.query, ...patch } })
}

const customerCodes = computed(() => customers.value.map(c => c.code))
// No status row: UBA does not know the customer. A row that is not live: registered, history replaying.
const needsSetup = computed(
	() =>
		statusLoaded.value &&
		!statusError.value &&
		(!status.value || (!!status.value.onboarding && status.value.onboarding !== "live"))
)
const unhealthyFeeds = computed(() => (status.value?.feeds ?? []).filter(feed => feed.status !== "ok"))

const FEED_LABELS: Record<string, string> = { office365: "Microsoft 365", wazuh: "Wazuh" }

function feedLabel(source: string) {
	return FEED_LABELS[source] ?? source
}

function feedTitle(feed: UbaFeedStatus) {
	const lines = [
		`events arriving now: ${formatLag(feed.lag_p50_s)} old (median, last 15 min)`,
		`last hour: ${feed.received_1h} received, ${feed.repeated_1h} repeats`
	]
	return [...feed.reasons, ...lines].join("\n")
}
const customerOptions = computed(() => customers.value.map(c => ({ label: c.name ? `${c.name} (${c.code})` : c.code, value: c.code })))

const customerModel = computed<string | null>({
	get: () => (customerQuery.value && customerCodes.value.includes(customerQuery.value) ? customerQuery.value : null),
	set: code => setQuery({ customer: code ?? undefined, entity: undefined, alert: undefined })
})

const tabModel = computed<string>({
	get: () => ((TABS as readonly string[]).includes(tabQuery.value ?? "") ? (tabQuery.value as string) : "entities"),
	set: tab => setQuery({ tab })
})

const drawer = computed<{ kind: "entity" | "alert"; id: string } | null>(() => {
	if (entityQuery.value) return { kind: "entity", id: entityQuery.value }
	if (alertQuery.value) return { kind: "alert", id: alertQuery.value }
	return null
})

function openEntity(entityKey: string) {
	router.push({ query: { ...route.query, entity: entityKey, alert: undefined } })
}

function openAlert(alertId: string) {
	router.push({ query: { ...route.query, alert: alertId, entity: undefined } })
}

function closeDrawer() {
	setQuery({ entity: undefined, alert: undefined })
}

function loadStatus(code: string) {
	statusLoaded.value = false
	statusError.value = null
	status.value = null
	Api.uba
		.getStatus(code)
		.then(res => {
			status.value = res.data.status
			version.value = res.data.version
		})
		.catch((err: ApiError) => {
			statusError.value = err
		})
		.finally(() => {
			statusLoaded.value = true
		})
}

function loadCustomers() {
	Api.customers
		.getCustomers({})
		.then(res => {
			customers.value = (res.data.customers ?? []).map(c => ({ code: c.customer_code, name: c.customer_name }))
			if (!customerModel.value && customerCodes.value.length) {
				setQuery({ customer: getAvailableGlobalCustomerValue(customerCodes.value) ?? customerCodes.value[0] })
			}
		})
		.catch(() => {
			customers.value = []
		})
}

// The sidebar filter wins when it names a customer; an emptied selection keeps the current one
// (this page renders nothing without a customer).
onGlobalCustomerFilterChange(codes => {
	const match = codes.find(c => customerCodes.value.includes(c))
	if (match && match !== customerModel.value) setQuery({ customer: match, entity: undefined, alert: undefined })
})

watch(
	customerModel,
	code => {
		if (code && available.value) loadStatus(code)
	},
	{ immediate: true }
)
watch(available, ok => {
	if (ok && customerModel.value) loadStatus(customerModel.value)
})

onBeforeMount(loadCustomers)
</script>
