<template>
	<div class="flex flex-col gap-4">
		<!-- Filters Bar -->
		<n-form-item label="Customer" :show-feedback="false">
			<n-select
				v-model:value="selectedCustomerCode"
				:options="customersOptions"
				placeholder="Select Customer"
				filterable
				:loading="loadingCustomers"
				:consistent-menu-width="false"
				clearable
			/>
		</n-form-item>

		<!-- No Event Sources Warning -->
		<n-alert v-if="showNoSourcesWarning" title="No Event Sources Configured" type="warning">
			An Event Source needs to be defined for this customer before dashboards can be enabled. Go to the customer's
			<strong>Event Sources</strong>
			tab to configure one.
		</n-alert>

		<EnabledDashboardsSection
			ref="enabledDashboardsSectionRef"
			v-model:enabled-dashboards="enabledDashboards"
			:customer-code="selectedCustomerCode"
			:visible="!!selectedCustomerCode && !showNoSourcesWarning"
			:event-sources-list
		/>

		<DashboardCategoriesSection
			:selected-customer-code
			:event-sources-list
			:loading-event-sources
			:enabled-dashboards
			@refresh-enabled-dashboards="refreshEnabledDashboards"
		/>
	</div>
</template>

<script setup lang="ts">
import type { Customer } from "@/types/customers.d"
import type { EnabledDashboard } from "@/types/dashboards.d"
import type { EventSource } from "@/types/eventSources.d"
import { NAlert, NFormItem, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, useTemplateRef, watch } from "vue"
import Api from "@/api"
import DashboardCategoriesSection from "./DashboardCategoriesSection.vue"
import EnabledDashboardsSection from "./EnabledDashboardsSection.vue"

const message = useMessage()

// ── Customer selection ──────────────────────────────────────────
const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])
const selectedCustomerCode = ref<string | null>(null)

// ── Enabled dashboards (lista aggiornata da EnabledDashboardsSection via v-model) ──
const enabledDashboards = ref<EnabledDashboard[]>([])
const enabledDashboardsSectionRef = useTemplateRef<InstanceType<typeof EnabledDashboardsSection>>(
	"enabledDashboardsSectionRef"
)

const customersOptions = computed(() =>
	customersList.value.map(c => ({ label: `#${c.customer_code} - ${c.customer_name}`, value: c.customer_code }))
)

function getCustomers() {
	loadingCustomers.value = true

	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCustomers.value = false
		})
}

// ── Event Source selection ───────────────────────────────────────
const loadingEventSources = ref(false)
const eventSourcesList = ref<EventSource[]>([])

const showNoSourcesWarning = computed(
	() => selectedCustomerCode.value && !loadingEventSources.value && !eventSourcesList.value.length
)

function getEventSources(customerCode: string) {
	loadingEventSources.value = true
	eventSourcesList.value = []

	Api.siem
		.getEventSources(customerCode)
		.then(res => {
			if (res.data.success) {
				eventSourcesList.value = res.data?.event_sources || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingEventSources.value = false
		})
}

function refreshEnabledDashboards() {
	enabledDashboardsSectionRef.value?.refreshEnabledDashboards()
}

watch(selectedCustomerCode, code => {
	eventSourcesList.value = []

	if (code) {
		getEventSources(code)
	}
})

onBeforeMount(() => {
	getCustomers()
})
</script>
