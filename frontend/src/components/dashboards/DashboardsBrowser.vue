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

		<!-- Enabled Dashboards for customer -->
		<n-card v-if="selectedCustomerCode && !showNoSourcesWarning" size="small">
			<template #header>
				<div class="flex items-center justify-between">
					<span>Enabled Dashboards</span>
					<span class="text-sm font-normal opacity-60">{{ enabledDashboards.length }} enabled</span>
				</div>
			</template>

			<n-scrollbar x-scrollable class="max-w-full">
				<n-spin :show="loadingEnabled">
					<n-data-table
						v-if="enabledDashboards.length"
						:columns="enabledColumns"
						:data="enabledDashboards"
						:bordered="false"
						:single-line="false"
						size="small"
					/>
					<n-empty
						v-else-if="!loadingEnabled"
						description="No dashboards enabled for this customer yet"
						class="h-32 justify-center"
					/>
				</n-spin>
			</n-scrollbar>
		</n-card>

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
import type { DataTableColumns } from "naive-ui"
import type { Customer } from "@/types/customers.d"
import type { EnabledDashboard } from "@/types/dashboards.d"
import type { EventSource } from "@/types/eventSources.d"
import {
	NAlert,
	NButton,
	NCard,
	NDataTable,
	NEmpty,
	NFormItem,
	NScrollbar,
	NSelect,
	NSpin,
	useDialog,
	useMessage
} from "naive-ui"
import { computed, h, onBeforeMount, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import DashboardCategoriesSection from "./DashboardCategoriesSection.vue"

const message = useMessage()
const dialog = useDialog()
const router = useRouter()

// ── Customer selection ──────────────────────────────────────────
const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])
const selectedCustomerCode = ref<string | null>(null)

// ── Enabled dashboards ─────────────────────────────────────────
const loadingEnabled = ref(false)
const enabledDashboards = ref<EnabledDashboard[]>([])

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

function getEnabledDashboards(customerCode: string) {
	loadingEnabled.value = true

	Api.siem
		.getEnabledDashboards(customerCode)
		.then(res => {
			if (res.data.success) {
				enabledDashboards.value = res.data?.enabled_dashboards || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingEnabled.value = false
		})
}

function refreshEnabledDashboards() {
	if (selectedCustomerCode.value) {
		getEnabledDashboards(selectedCustomerCode.value)
	}
}

// ── Enabled dashboards table ────────────────────────────────────
const enabledColumns: DataTableColumns<EnabledDashboard> = [
	{ title: "Display Name", key: "display_name", minWidth: 180 },
	{ title: "Category", key: "library_card", width: 150 },
	{ title: "Template", key: "template_id", width: 180 },
	{
		title: "Event Source",
		key: "event_source_id",
		width: 180,
		render(row) {
			const source = eventSourcesList.value.find(s => s.id === row.event_source_id)
			return source ? `${source.name} (${source.event_type})` : `#${row.event_source_id}`
		}
	},
	{
		title: "Created",
		key: "created_at",
		width: 180,
		render(row) {
			return new Date(row.created_at).toLocaleString()
		}
	},
	{
		title: "",
		key: "actions",
		width: 160,
		render(row) {
			return h("div", { class: "flex gap-2" }, [
				h(
					NButton,
					{
						size: "small",
						type: "primary",
						quaternary: true,
						onClick: () => {
							// TODO-FE: use route by name instead of hardcoding the path
							router.push(`/dashboards/view/${row.id}`)
						}
					},
					{ default: () => "View" }
				),
				h(
					NButton,
					{
						size: "small",
						type: "error",
						quaternary: true,
						onClick: () => {
							dialog.warning({
								title: "Disable Dashboard",
								content: `Are you sure you want to disable "${row.display_name}"?`,
								positiveText: "Disable",
								negativeText: "Cancel",
								onPositiveClick: () => {
									Api.siem
										.disableDashboard(row.id)
										.then(res => {
											if (res.data.success) {
												message.success("Dashboard disabled successfully")
												if (selectedCustomerCode.value) {
													getEnabledDashboards(selectedCustomerCode.value)
												}
											} else {
												message.warning(
													res.data?.message || "An error occurred. Please try again later."
												)
											}
										})
										.catch(err => {
											message.error(
												err.response?.data?.message ||
													"An error occurred. Please try again later."
											)
										})
								}
							})
						}
					},
					{ default: () => "Disable" }
				)
			])
		}
	}
]

watch(selectedCustomerCode, code => {
	enabledDashboards.value = []
	eventSourcesList.value = []

	if (code) {
		getEventSources(code)
		getEnabledDashboards(code)
	}
})

onBeforeMount(() => {
	getCustomers()
})
</script>
