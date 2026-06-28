<template>
	<div class="flex flex-col gap-4">
		<!-- Filters Bar -->
		<div class="flex flex-wrap items-end gap-3">
			<n-form-item label="Customer" :show-feedback="false" class="mb-0! min-w-60 grow">
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

			<n-button type="primary" :disabled="!selectedCustomerCode" @click="showAddTemplateDrawer = true">
				<template #icon>
					<Icon name="carbon:add" />
				</template>
				Add template
			</n-button>
		</div>

		<n-empty
			v-if="!selectedCustomerCode"
			description="Select a customer to browse dashboard templates and enable dashboards"
			class="h-48 justify-center"
		/>

		<template v-else>
			<!-- No Event Sources Warning -->
			<n-alert v-if="showNoSourcesWarning" title="No Event Sources Configured" type="warning">
				An Event Source needs to be defined for this customer before dashboards can be enabled. Go to the
				customer's
				<strong>Event Sources</strong>
				tab to configure one.
			</n-alert>

			<EnabledDashboardsSection
				ref="enabledDashboardsSectionRef"
				v-model:enabled-dashboards="enabledDashboards"
				:customer-code="selectedCustomerCode"
				:visible="!showNoSourcesWarning"
				:event-sources-list
			/>
		</template>

		<n-drawer
			v-model:show="showAddTemplateDrawer"
			display-directive="show"
			:width="960"
			class="max-w-[92vw]"
			:trap-focus="false"
		>
			<n-drawer-content title="Add template" closable :native-scrollbar="false">
				<DashboardCategoriesSection
					:selected-customer-code
					:event-sources-list
					:loading-event-sources
					:enabled-dashboards
					@refresh-enabled-dashboards="refreshEnabledDashboards"
				/>
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { EnabledDashboard } from "@/types/dashboards"
import type { EventSource } from "@/types/event-sources"
import { NAlert, NButton, NDrawer, NDrawerContent, NEmpty, NFormItem, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, useTemplateRef, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { globalCustomerSingleDefault } from "@/composables/useGlobalCustomerFilter"
import { getApiErrorMessage } from "@/utils"
import DashboardCategoriesSection from "./DashboardCategoriesSection.vue"
import EnabledDashboardsSection from "./EnabledDashboardsSection.vue"

const message = useMessage()

// ── Customer selection ──────────────────────────────────────────
const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])
const selectedCustomerCode = ref<string | null>(null)
const showAddTemplateDrawer = ref(false)

// ── Enabled dashboards (lista aggiornata da EnabledDashboardsSection via v-model) ──
const enabledDashboards = ref<EnabledDashboard[]>([])
const enabledDashboardsSectionRef =
	useTemplateRef<InstanceType<typeof EnabledDashboardsSection>>("enabledDashboardsSectionRef")

const customersOptions = computed(() =>
	customersList.value.map(c => ({ label: `#${c.customer_code} - ${c.customer_name}`, value: c.customer_code }))
)

function getCustomers() {
	loadingCustomers.value = true

	return Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
	showAddTemplateDrawer.value = false

	if (code) {
		getEventSources(code)
	}
})

onBeforeMount(() => {
	getCustomers().then(() => {
		const code = globalCustomerSingleDefault()
		if (code) {
			selectedCustomerCode.value = code
		}
	})
})
</script>
