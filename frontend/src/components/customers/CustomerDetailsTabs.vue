<template>
	<n-tabs type="line" animated :tabs-padding="24" class="h-full">
		<n-tab-pane name="Customer" tab="Customer" display-directive="show" class="pt-0!">
			<n-tabs
				type="line"
				animated
				:tabs-padding="24"
				class="[&_.n-tabs-nav]:bg-secondary z-20 h-full [&_.n-tabs-nav]:relative [&_.n-tabs-nav]:z-99"
				placement="left"
				:pane-style="{ minHeight: 'min(450px, 90vh)' }"
			>
				<n-tab-pane name="Info" tab="Info" display-directive="show:lazy" class="p-4!">
					<CustomerInfo
						v-if="customerInfo"
						v-model:loading="loadingDeleteModel"
						:customer="customerInfo"
						@delete="emit('delete')"
						@submitted="emit('update:customerInfo', $event)"
					/>
				</n-tab-pane>
				<n-tab-pane name="Provision" tab="Provision" display-directive="show:lazy" class="p-4!">
					<CustomerProvision
						:customer-meta
						:customer-code="customer.customer_code"
						:customer-name="customer.customer_name"
						@delete="emit('update:customerMeta', null)"
						@submitted="emit('update:customerMeta', $event)"
					/>
				</n-tab-pane>
				<n-tab-pane
					name="3rd Party Integrations"
					tab="3rd Party Integrations"
					display-directive="show:lazy"
					class="p-4!"
				>
					<CustomerIntegrations
						:customer-code="customer.customer_code"
						:customer-name="customer.customer_name"
					/>
				</n-tab-pane>
				<n-tab-pane
					name="Network Connectors"
					tab="Network Connectors"
					display-directive="show:lazy"
					class="p-4!"
				>
					<CustomerNetworkConnectors
						:customer-code="customer.customer_code"
						:customer-name="customer.customer_name"
					/>
				</n-tab-pane>
				<n-tab-pane
					name="Notification Workflows"
					tab="Notification Workflows"
					display-directive="show:lazy"
					class="p-4!"
				>
					<CustomerNotificationsWorkflows :customer-code="customer.customer_code" />
				</n-tab-pane>
				<n-tab-pane name="AI Triggers" tab="AI Triggers" display-directive="show:lazy" class="p-4!">
					<CustomerAITriggers :customer-code="customer.customer_code" />
				</n-tab-pane>
				<n-tab-pane
					name="AI Notifications"
					tab="AI Notifications"
					display-directive="show:lazy"
					class="overflow-hidden p-4!"
				>
					<CustomerAiNotifications :customer-code="customer.customer_code" />
				</n-tab-pane>
				<n-tab-pane name="Event Sources" tab="Event Sources" display-directive="show:lazy" class="p-4!">
					<CustomerEventSources :customer-code="customer.customer_code" />
				</n-tab-pane>

				<template #suffix><div class="h-4 w-full"></div></template>
			</n-tabs>
		</n-tab-pane>

		<n-tab-pane name="Agents" tab="Agents" display-directive="show" class="pt-0!">
			<n-tabs
				type="line"
				animated
				:tabs-padding="24"
				class="[&_.n-tabs-nav]:bg-secondary z-20 h-full [&_.n-tabs-nav]:relative [&_.n-tabs-nav]:z-99"
				placement="left"
				:pane-style="{ minHeight: 'min(450px, 90vh)' }"
			>
				<n-tab-pane name="Agents" tab="Agents" display-directive="show" class="p-4! pr-0!">
					<n-scrollbar trigger="none" :class="scrollbarClass">
						<CustomerAgents v-if="customerInfo" :customer="customerInfo" />
					</n-scrollbar>
				</n-tab-pane>
				<n-tab-pane
					name="Deploy Agent"
					tab="Deploy Agent"
					display-directive="show:lazy"
					class="overflow-hidden p-4!"
				>
					<CustomerEdrInstall :customer-code="customer.customer_code" />
				</n-tab-pane>
				<n-tab-pane
					name="Healthcheck Wazuh"
					tab="Healthcheck Wazuh"
					display-directive="show:lazy"
					class="p-4! pr-0!"
				>
					<n-scrollbar trigger="none" :class="scrollbarClass">
						<CustomerHealthcheckList
							v-model:filters="healthcheckFilters"
							source="wazuh"
							:customer-code="customer.customer_code"
						/>
					</n-scrollbar>
				</n-tab-pane>
				<n-tab-pane
					name="Healthcheck Velociraptor"
					tab="Healthcheck Velociraptor"
					display-directive="show:lazy"
					class="p-4! pr-0!"
				>
					<n-scrollbar trigger="none" :class="scrollbarClass">
						<CustomerHealthcheckList
							v-model:filters="healthcheckFilters"
							source="velociraptor"
							:customer-code="customer.customer_code"
						/>
					</n-scrollbar>
				</n-tab-pane>

				<template #suffix><div class="h-4 w-full"></div></template>
			</n-tabs>
		</n-tab-pane>

		<n-tab-pane
			v-if="customerPortainerStackId !== null"
			name="Wazuh Worker"
			tab="Wazuh Worker"
			display-directive="show"
			class="p-4!"
		>
			<CustomerWazuhWorker :stack-id="customerPortainerStackId" />
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { Customer, CustomerMeta } from "@/types/customers"
import { NScrollbar, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent } from "vue"
import { useCustomerHealthcheckFilters } from "@/composables/useCustomerHealthcheckFilters"

const props = defineProps<{
	customer: Customer
	customerInfo: Customer | null
	customerMeta: CustomerMeta | null
	customerPortainerStackId: number | null
	loadingDelete?: boolean
	useMaxHeight?: boolean
}>()

const emit = defineEmits<{
	(e: "delete"): void
	(e: "update:customerInfo", value: Customer): void
	(e: "update:customerMeta", value: CustomerMeta | null): void
	(e: "update:loadingDelete", value: boolean): void
}>()

const CustomerInfo = defineAsyncComponent(() => import("./CustomerInfo.vue"))
const CustomerAgents = defineAsyncComponent(() => import("./CustomerAgents.vue"))
const CustomerEdrInstall = defineAsyncComponent(() => import("./CustomerEdrInstall.vue"))
const CustomerProvision = defineAsyncComponent(() => import("./provision/CustomerProvision.vue"))
const CustomerHealthcheckList = defineAsyncComponent(() => import("./healthcheck/CustomerHealthcheckList.vue"))
const CustomerIntegrations = defineAsyncComponent(() => import("./integrations/CustomerIntegrations.vue"))
const CustomerNetworkConnectors = defineAsyncComponent(
	() => import("./networkConnectors/CustomerNetworkConnectors.vue")
)
const CustomerNotificationsWorkflows = defineAsyncComponent(
	() => import("./notifications/CustomerNotificationsWorkflows.vue")
)
const CustomerAITriggers = defineAsyncComponent(() => import("./aiTriggers/CustomerAITriggers.vue"))
const CustomerAiNotifications = defineAsyncComponent(() => import("./aiNotifications/CustomerAiNotifications.vue"))
const CustomerEventSources = defineAsyncComponent(() => import("./eventSources/CustomerEventSources.vue"))
const CustomerWazuhWorker = defineAsyncComponent(() => import("./CustomerWazuhWorker.vue"))

const { healthcheckFilters } = useCustomerHealthcheckFilters()

const loadingDeleteModel = computed({
	get: () => props.loadingDelete ?? false,
	set: value => emit("update:loadingDelete", value)
})

const scrollbarClass = computed(() => (props.useMaxHeight ? "max-h-117.5 pr-4" : undefined))
</script>
