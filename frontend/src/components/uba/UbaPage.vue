<template>
	<div class="uba-page @container flex flex-col gap-5" data-testid="uba-page">
		<header class="flex flex-wrap items-end justify-between gap-4">
			<div class="flex min-w-0 flex-col gap-1">
				<h2 class="m-0 text-xl font-semibold">User Behavior Analytics</h2>
				<p class="text-secondary m-0 max-w-2xl text-sm">
					People and computers ranked by behavioral risk, the alerts it raises, and what is muted.
				</p>
			</div>
			<div v-if="available && customerOptions.length" class="flex flex-wrap items-center gap-2">
				<span v-if="version" class="version-chip font-mono text-[11px]" data-testid="uba-version">
					UBA {{ version }}
				</span>
				<n-button
					v-if="isAdmin && customerModel && !needsSetup"
					size="small"
					quaternary
					data-testid="uba-setup-toggle"
					@click="showSetup = !showSetup"
				>
					<template #icon><Icon name="carbon:settings-adjust" :size="15" /></template>
					Setup
				</n-button>
				<n-select
					v-model:value="customerModel"
					:options="customerOptions"
					filterable
					class="w-72!"
					aria-label="Customer"
					data-testid="uba-customer"
				>
					<template #arrow><Icon name="carbon:enterprise" :size="14" /></template>
				</n-select>
			</div>
		</header>

		<n-spin v-if="!availabilityLoaded" class="min-h-40" show />

		<div v-else-if="!available" class="flex flex-col gap-4">
			<n-empty description="SOCFortress UBA is not connected" class="py-6">
				<template #extra>
					<p class="text-secondary max-w-md text-sm">
						{{
							isAdmin
								? "Deploy UBA and connect it with the steps below."
								: "An admin can deploy SOCFortress UBA and connect it under Platform → Connectors."
						}}
					</p>
				</template>
			</n-empty>
			<n-card v-if="isAdmin" size="small" title="Deploy SOCFortress UBA">
				<UbaDeployGuide />
			</n-card>
		</div>

		<template v-else-if="customerModel">
			<UbaError v-if="statusError" :error="statusError" />
			<UbaStatusStrip v-else-if="status" :status />
			<!-- Not set up yet (no status row), or still learning from history: setup and progress. -->
			<UbaSetup
				v-if="needsSetup || showSetup"
				:key="`setup${customerModel}`"
				:customer-code="customerModel"
				:closable="!needsSetup"
				@live="onLive"
				@close="showSetup = false"
			/>
			<n-alert v-if="unhealthyFeeds.length" type="warning" :bordered="false">
				<div v-for="feed of unhealthyFeeds" :key="feed.source">
					<b>{{ feedLabel(feed.source) }}</b>
					is {{ feed.status }}: {{ feed.reasons.join("; ") }}.
				</div>
				<div class="text-secondary mt-1 text-xs">
					UBA's findings for this source may be missing or late until the feed recovers.
				</div>
			</n-alert>
			<n-alert v-if="status?.agents?.not_reporting" type="warning" :bordered="false">
				{{ status.agents.not_reporting }}
				{{ status.agents.not_reporting === 1 ? "computer has" : "computers have" }} stopped reporting:
				{{ silentText(status.agents) }}. UBA sees nothing from
				{{ status.agents.not_reporting === 1 ? "it" : "them" }} until the Wazuh agent checks in again.
			</n-alert>

			<UbaAbout :key="`about${customerModel}`" :customer-code="customerModel" />

			<n-tabs v-model:value="tabModel" type="line" animated>
				<n-tab-pane name="entities" display-directive="show:lazy">
					<template #tab>
						<span class="flex items-center gap-1.5">
							<Icon name="carbon:user-multiple" :size="15" />
							Entities
						</span>
					</template>
					<UbaEntities :key="`e${customerModel}`" :customer-code="customerModel" @open="openEntity" />
				</n-tab-pane>
				<n-tab-pane name="alerts" display-directive="show:lazy">
					<template #tab>
						<span class="flex items-center gap-1.5">
							<Icon name="carbon:warning-alt" :size="15" />
							Alerts
						</span>
					</template>
					<UbaAlerts
						:key="`a${customerModel}`"
						:customer-code="customerModel"
						:refresh-key
						@open="openAlert"
					/>
				</n-tab-pane>
				<n-tab-pane name="suppressions" display-directive="show:lazy">
					<template #tab>
						<span class="flex items-center gap-1.5">
							<Icon name="carbon:notification-off" :size="15" />
							Suppressions
						</span>
					</template>
					<UbaSuppressions
						:key="`s${customerModel}`"
						:customer-code="customerModel"
						:refresh-key
						@open-entity="openEntity"
					/>
				</n-tab-pane>
				<n-tab-pane name="rules" display-directive="show:lazy">
					<template #tab>
						<span class="flex items-center gap-1.5">
							<Icon name="carbon:rule" :size="15" />
							Rules
						</span>
					</template>
					<UbaRules :key="`r${customerModel}`" :customer-code="customerModel" />
				</n-tab-pane>
				<n-tab-pane name="directory" display-directive="show:lazy">
					<template #tab>
						<span class="flex items-center gap-1.5">
							<Icon name="carbon:catalog" :size="15" />
							Directory
						</span>
					</template>
					<UbaDirectory :key="`d${customerModel}`" :customer-code="customerModel" />
				</n-tab-pane>
			</n-tabs>

			<n-drawer
				:show="!!drawer"
				:width="760"
				class="max-w-[95vw]"
				data-testid="uba-drawer"
				@update:show="show => !show && closeDrawer()"
			>
				<n-drawer-content
					v-if="drawer"
					closable
					:native-scrollbar="false"
					header-class="uba-drawer-head"
					body-content-class="uba-drawer-body"
				>
					<template #header>
						<UbaDrawerHeader :meta="drawerMeta" :kind="drawer.kind === 'entity' ? 'Entity' : 'UBA alert'" />
					</template>
					<UbaEntityDetail
						v-if="drawer.kind === 'entity'"
						:key="`entity:${drawer.id}`"
						:customer-code="customerModel"
						:entity-key="drawer.id"
						@open-alert="openAlert"
						@changed="refreshKey++"
						@meta="m => (drawerMeta = m)"
					/>
					<UbaAlertDetail
						v-else
						:key="`alert:${drawer.id}`"
						:customer-code="customerModel"
						:alert-id="drawer.id"
						@open-entity="openEntity"
						@changed="refreshKey++"
						@meta="m => (drawerMeta = m)"
					/>
				</n-drawer-content>
			</n-drawer>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { UbaDrawerMeta } from "./ui/UbaDrawerHeader.vue"
import type { ApiError } from "@/types/common"
import type { UbaAgentsSummary, UbaTenantStatus } from "@/types/uba"
import { NAlert, NButton, NCard, NDrawer, NDrawerContent, NEmpty, NSelect, NSpin, NTabPane, NTabs } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { useRouteQueryParam } from "@/composables/useNavigation"
import { useUbaAvailability } from "@/composables/useUbaAvailability"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import UbaAbout from "./UbaAbout.vue"
import UbaAlertDetail from "./UbaAlertDetail.vue"
import UbaAlerts from "./UbaAlerts.vue"
import UbaDeployGuide from "./UbaDeployGuide.vue"
import UbaDirectory from "./UbaDirectory.vue"
import UbaEntities from "./UbaEntities.vue"
import UbaEntityDetail from "./UbaEntityDetail.vue"
import UbaError from "./UbaError.vue"
import UbaRules from "./UbaRules.vue"
import UbaSetup from "./UbaSetup.vue"
import UbaSuppressions from "./UbaSuppressions.vue"
import UbaDrawerHeader from "./ui/UbaDrawerHeader.vue"
import UbaStatusStrip from "./ui/UbaStatusStrip.vue"
import { silentComputers } from "./utils"

const TABS = ["entities", "alerts", "suppressions", "rules", "directory"] as const

const route = useRoute()
const router = useRouter()
const dFormats = useSettingsStore().dateFormat
const { available, loaded: availabilityLoaded } = useUbaAvailability()
const { getAvailableGlobalCustomerValue, onGlobalCustomerFilterChange } = useGlobalCustomerFilter()

const customers = ref<{ code: string; name: string }[]>([])
const status = ref<UbaTenantStatus | null>(null)
const version = ref("")
const statusLoaded = ref(false)
const statusError = ref<ApiError | null>(null)
const refreshKey = ref(0)
// Admins reopen setup for a live customer, e.g. to add Microsoft 365 provisioned after UBA.
const showSetup = ref(false)
const isAdmin = computed(() => useAuthStore().isAdmin)

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

function silentText(agents: UbaAgentsSummary) {
	return silentComputers(agents, t => String(formatDate(t, dFormats.datetime)))
}

function feedLabel(source: string) {
	return FEED_LABELS[source] ?? source
}

const customerOptions = computed(() =>
	customers.value.map(c => ({ label: c.name ? `${c.name} (${c.code})` : c.code, value: c.code }))
)

const customerModel = computed<string | null>({
	get: () => (customerQuery.value && customerCodes.value.includes(customerQuery.value) ? customerQuery.value : null),
	set: code => setQuery({ customer: code ?? undefined, entity: undefined, alert: undefined })
})

const tabModel = computed<string>({
	get: () => ((TABS as readonly string[]).includes(tabQuery.value ?? "") ? (tabQuery.value as string) : "entities"),
	set: tab => setQuery({ tab })
})

/** The open drawer's header, sent up by the entity or alert it shows; cleared when it changes. */
const drawerMeta = ref<UbaDrawerMeta | null>(null)

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

function onLive() {
	// Just went live (refresh the header); when reopened by an admin, the card stays open.
	if (!showSetup.value && customerModel.value) loadStatus(customerModel.value)
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
		showSetup.value = false
		if (code && available.value) loadStatus(code)
	},
	{ immediate: true }
)
watch(
	() => (drawer.value ? `${drawer.value.kind}:${drawer.value.id}` : ""),
	() => {
		drawerMeta.value = null
	}
)
watch(available, ok => {
	if (ok && customerModel.value) loadStatus(customerModel.value)
})

onBeforeMount(loadCustomers)
</script>

<style>
/* Shared by the UBA tabs' table cells (JSX renders, so not scoped): the entity type tile, and table
   headers in the page's section-label voice. */
.uba-page .entity-icon,
.n-drawer .entity-icon {
	display: grid;
	place-items: center;
	flex-shrink: 0;
	width: 26px;
	height: 26px;
	border-radius: 6px;
	color: var(--fg-secondary-color);
	background-color: var(--hover-color);
}

.uba-page .rule-chip {
	padding: 1px 6px;
	border-radius: 4px;
	background-color: var(--hover-color);
}

/* The UBA drawers: a header tall enough for the entity's name and risk, a calmer body. */
.uba-drawer-head {
	align-items: flex-start !important;
	padding-top: 18px !important;
	padding-bottom: 16px !important;
}

.uba-drawer-head .n-drawer-header__main {
	min-width: 0;
	flex: 1;
	/* Room for the close button beside the risk figure. */
	padding-right: 36px;
}

.uba-drawer-body {
	padding-top: 20px !important;
	padding-bottom: 32px !important;
}
</style>

<style scoped>
.version-chip {
	padding: 2px 8px;
	border: 1px solid var(--border-color);
	border-radius: 999px;
	color: var(--fg-secondary-color);
}
</style>
