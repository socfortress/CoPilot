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
				@update:value="onCustomerChange"
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

		<!-- Categories -->
		<n-card size="small">
			<template #header>
				<div class="flex items-center justify-between">
					<span>Dashboard Categories</span>
					<span class="text-sm font-normal opacity-60">{{ categories.length }} available</span>
				</div>
			</template>

			<n-spin :show="loadingCategories">
				<div v-if="categories.length" class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
					<DashboardCategoryCard
						v-for="cat in categories"
						:key="cat.id"
						:category="cat"
						:selected="selectedCategoryId === cat.id"
						@select="selectCategory(cat.id)"
					/>
				</div>
				<n-empty v-else-if="!loadingCategories" description="No dashboard categories found" />
			</n-spin>
		</n-card>

		<!-- Templates for selected category -->
		<n-card v-if="selectedCategory" size="small">
			<template #header>
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<div class="flex h-full items-center justify-center" :style="{ color: selectedCategory.color }">
							<Icon :name="getDashboardIcon(selectedCategory.icon)" :size="19" />
						</div>
						<span>{{ selectedCategory.title }}</span>
					</div>
					<span class="text-sm font-normal opacity-60">
						{{ selectedCategory.templates.length }} template{{
							selectedCategory.templates.length !== 1 ? "s" : ""
						}}
					</span>
				</div>
			</template>
			<template #header-extra>
				<n-select
					v-model:value="selectedEventSourceId"
					:options="eventSourceOptions"
					placeholder="Select Event Source"
					filterable
					:loading="loadingEventSources"
					:disabled="!selectedCustomerCode"
					clearable
					:consistent-menu-width="false"
					class="w-48!"
				/>
			</template>

			<n-spin :show="loadingTemplates">
				<div
					v-if="selectedCategory.templates.length"
					class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3"
				>
					<DashboardTemplateCard
						v-for="tpl in selectedCategory.templates"
						:key="tpl.id"
						:template="tpl"
						:is-enabled="isTemplateEnabled(selectedCategoryId!, tpl.id)"
						:can-enable="!!selectedCustomerCode && !!selectedEventSourceId"
						disabled-tooltip-text="Select an event source first"
						@enable="onEnableTemplate"
						@disable="onDisableTemplate"
					/>
				</div>
				<n-empty v-else-if="!loadingTemplates" description="No templates in this category" />
			</n-spin>
		</n-card>
	</div>
</template>

<script setup lang="ts">
import type { DataTableColumns } from "naive-ui"
import type { Customer } from "@/types/customers.d"
import type {
	DashboardCategory,
	DashboardCategoryWithTemplates,
	DashboardTemplate,
	EnabledDashboard
} from "@/types/dashboards.d"
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
import { computed, h, onBeforeMount, ref } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import DashboardCategoryCard from "./DashboardCategoryCard.vue"
import DashboardTemplateCard from "./DashboardTemplateCard.vue"
import { getDashboardIcon } from "./utils"

const DashboardIcon = "carbon:dashboard"

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
const selectedEventSourceId = ref<number | null>(null)

const eventSourceOptions = computed(() =>
	eventSourcesList.value.filter(s => s.enabled).map(s => ({ label: `${s.name} (${s.event_type})`, value: s.id }))
)

const showNoSourcesWarning = computed(
	() => selectedCustomerCode.value && !loadingEventSources.value && !eventSourcesList.value.length
)

function getEventSources(customerCode: string) {
	loadingEventSources.value = true
	eventSourcesList.value = []
	selectedEventSourceId.value = null

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

function onCustomerChange(code: string) {
	enabledDashboards.value = []

	if (code) {
		getEventSources(code)
		getEnabledDashboards(code)
	}
}

// ── Dashboard categories ────────────────────────────────────────
const loadingCategories = ref(false)
const categories = ref<DashboardCategory[]>([])

function getCategories() {
	loadingCategories.value = true
	Api.siem
		.getDashboardCategories()
		.then(res => {
			if (res.data.success) {
				categories.value = res.data?.categories || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCategories.value = false
		})
}

// ── Category detail (templates) ─────────────────────────────────
const selectedCategoryId = ref<string | null>(null)
const selectedCategory = ref<DashboardCategoryWithTemplates | null>(null)
const loadingTemplates = ref(false)

function selectCategory(categoryId: string) {
	if (selectedCategoryId.value === categoryId) {
		selectedCategoryId.value = null
		selectedCategory.value = null
		return
	}
	selectedCategoryId.value = categoryId
	loadingTemplates.value = true

	Api.siem
		.getDashboardCategory(categoryId)
		.then(res => {
			if (res.data.success) {
				selectedCategory.value = res.data.category
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingTemplates.value = false
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

function isTemplateEnabled(libraryCard: string, templateId: string): boolean {
	return enabledDashboards.value.some(
		d =>
			d.library_card === libraryCard &&
			d.template_id === templateId &&
			d.event_source_id === selectedEventSourceId.value
	)
}

// ── Enable / Disable actions ────────────────────────────────────
function onEnableTemplate(template: DashboardTemplate) {
	if (!selectedCustomerCode.value || !selectedEventSourceId.value || !selectedCategoryId.value) {
		message.warning("Please select a customer and event source first")
		return
	}

	Api.siem
		.enableDashboard({
			customer_code: selectedCustomerCode.value,
			event_source_id: selectedEventSourceId.value,
			library_card: selectedCategoryId.value,
			template_id: template.id,
			display_name: template.title
		})
		.then(res => {
			if (res.data.success) {
				message.success("Dashboard enabled successfully")
				if (selectedCustomerCode.value) {
					getEnabledDashboards(selectedCustomerCode.value)
				}
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
}

function onDisableTemplate(template: DashboardTemplate) {
	const match = enabledDashboards.value.find(
		d =>
			d.library_card === selectedCategoryId.value &&
			d.template_id === template.id &&
			d.event_source_id === selectedEventSourceId.value
	)
	if (!match) return

	dialog.warning({
		title: "Disable Dashboard",
		content: `Are you sure you want to disable "${template.title}"?`,
		positiveText: "Disable",
		negativeText: "Cancel",
		onPositiveClick: () => {
			Api.siem
				.disableDashboard(match.id)
				.then(res => {
					if (res.data.success) {
						message.success("Dashboard disabled successfully")
						if (selectedCustomerCode.value) {
							getEnabledDashboards(selectedCustomerCode.value)
						}
					} else {
						message.warning(res.data?.message || "An error occurred. Please try again later.")
					}
				})
				.catch(err => {
					message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				})
		}
	})
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

// ── Lifecycle ───────────────────────────────────────────────────
onBeforeMount(() => {
	getCustomers()
	getCategories()
})
</script>
