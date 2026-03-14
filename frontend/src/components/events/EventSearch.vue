<template>
	<div class="flex flex-col gap-4">
		<!-- Filters Bar -->
		<n-card size="small">
			<div class="flex flex-col gap-3">
				<div class="flex flex-wrap items-end gap-3">
					<div class="flex flex-col gap-1">
						<span class="text-xs opacity-60">Customer</span>
						<n-select
							v-model:value="selectedCustomerCode"
							:options="customersOptions"
							placeholder="Select Customer"
							filterable
							:loading="loadingCustomers"
							style="width: 260px"
							@update:value="onCustomerChange"
						/>
					</div>
					<div class="flex flex-col gap-1">
						<span class="text-xs opacity-60">Event Source</span>
						<n-select
							v-model:value="selectedSourceName"
							:options="eventSourceOptions"
							placeholder="Select Source"
							filterable
							:loading="loadingEventSources"
							:disabled="!selectedCustomerCode"
							style="width: 220px"
							@update:value="onSourceChange"
						/>
					</div>
					<div class="flex flex-col gap-1">
						<span class="text-xs opacity-60">Time Range</span>
						<n-select v-model:value="timerange" :options="timerangeOptions" style="width: 140px" />
					</div>
					<div class="flex flex-col gap-1">
						<span class="text-xs opacity-60">Page Size</span>
						<n-select v-model:value="pageSize" :options="pageSizeOptions" style="width: 110px" />
					</div>
					<n-button
						type="primary"
						:disabled="!selectedCustomerCode || !selectedSourceName"
						:loading="loadingEvents"
						@click="searchEvents()"
					>
						<template #icon>
							<Icon :name="SearchIcon" :size="16" />
						</template>
						Search
					</n-button>
				</div>

				<!-- Query Bar with Autocomplete -->
				<div class="relative">
					<n-input
						ref="queryInputRef"
						v-model:value="query"
						placeholder="Lucene query (e.g. agent_name:server01 AND rule_level:>=10)"
						clearable
						@keydown.enter="searchEvents()"
						@keydown.tab.prevent="acceptSuggestion"
						@keydown.escape="showSuggestions = false"
						@input="onQueryInput"
					>
						<template #prefix>
							<Icon :name="CodeIcon" :size="16" class="opacity-50" />
						</template>
					</n-input>
					<!-- Autocomplete dropdown -->
					<div
						v-if="showSuggestions && filteredSuggestions.length"
						class="suggestions-dropdown bg-default absolute top-full right-0 left-0 z-50 mt-1 max-h-48 overflow-y-auto rounded-lg border shadow-lg"
					>
						<div
							v-for="(suggestion, index) in filteredSuggestions"
							:key="suggestion.field"
							class="suggestion-item flex cursor-pointer items-center justify-between px-3 py-1.5 text-sm hover:bg-[var(--hover-005-color)]"
							:class="{ 'bg-[var(--hover-005-color)]': index === activeSuggestionIndex }"
							@mousedown.prevent="applySuggestion(suggestion.field)"
						>
							<span class="font-mono">{{ suggestion.field }}</span>
							<span class="text-xs opacity-50">{{ suggestion.type }}</span>
						</div>
					</div>
				</div>
			</div>
		</n-card>

		<!-- Results -->
		<n-spin :show="loadingEvents">
			<n-card v-if="events.length || loadingEvents" size="small">
				<div class="mb-2 flex items-center justify-between">
					<span class="text-sm opacity-60">
						{{ totalEvents }} event{{ totalEvents !== 1 ? "s" : "" }} found
					</span>
				</div>
				<n-data-table
					:columns="columns"
					:data="events"
					:bordered="false"
					:single-line="false"
					size="small"
					:row-key="(row: EventSearchResult) => row._id || JSON.stringify(row)"
					:row-props="rowProps"
					max-height="calc(100vh - 360px)"
					virtual-scroll
				/>
				<div v-if="scrollId && events.length < totalEvents" class="mt-3 flex justify-center">
					<n-button :loading="loadingMore" @click="loadMoreEvents">Load More</n-button>
				</div>
			</n-card>
			<n-empty
				v-else-if="!loadingEvents && hasSearched"
				description="No events found"
				class="h-48 justify-center"
			/>
		</n-spin>

		<!-- Event Detail Drawer -->
		<EventDetailDrawer
			v-model:show="showDetailDrawer"
			:event="selectedEvent"
			@filter-add="addFilterFromDetail"
			@filter-exclude="excludeFilterFromDetail"
		/>
	</div>
</template>

<script setup lang="ts">
import type { DataTableColumns } from "naive-ui"
import type { EventSearchResult, FieldMapping } from "@/types/events.d"
import type { EventSource } from "@/types/eventSources.d"
import type { Customer } from "@/types/customers.d"
import { NButton, NCard, NDataTable, NEmpty, NInput, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, h, nextTick, onBeforeMount, ref } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import EventDetailDrawer from "./EventDetailDrawer.vue"

const route = useRoute()

const SearchIcon = "carbon:search"
const CodeIcon = "carbon:code"

const message = useMessage()

// -- Customer selection --
const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])
const selectedCustomerCode = ref<string | null>(null)

const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCustomers.value = false
		})
}

// -- Event Source selection --
const loadingEventSources = ref(false)
const eventSourcesList = ref<EventSource[]>([])
const selectedSourceName = ref<string | null>(null)

const eventSourceOptions = computed(() =>
	eventSourcesList.value.filter(s => s.enabled).map(s => ({ label: `${s.name} (${s.event_type})`, value: s.name }))
)

function getEventSources(customerCode: string) {
	loadingEventSources.value = true
	eventSourcesList.value = []
	selectedSourceName.value = null
	fieldMappings.value = []

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
	resetResults()
	if (code) {
		getEventSources(code)
	}
}

function onSourceChange() {
	resetResults()
	if (selectedCustomerCode.value && selectedSourceName.value) {
		loadFieldMappings()
	}
}

// -- Search parameters --
const timerange = ref("24h")
const timerangeOptions = [
	{ label: "1 hour", value: "1h" },
	{ label: "6 hours", value: "6h" },
	{ label: "24 hours", value: "24h" },
	{ label: "3 days", value: "3d" },
	{ label: "7 days", value: "7d" },
	{ label: "14 days", value: "14d" },
	{ label: "30 days", value: "30d" }
]

const pageSize = ref(50)
const pageSizeOptions = [
	{ label: "25", value: 25 },
	{ label: "50", value: 50 },
	{ label: "100", value: 100 },
	{ label: "250", value: 250 }
]

const query = ref("")

// -- Field mappings / autocomplete --
const fieldMappings = ref<FieldMapping[]>([])
const showSuggestions = ref(false)
const activeSuggestionIndex = ref(0)

function loadFieldMappings() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return

	Api.siem
		.getFieldMappings(selectedCustomerCode.value, selectedSourceName.value)
		.then(res => {
			if (res.data.success) {
				fieldMappings.value = res.data.fields || []
			}
		})
		.catch(() => {
			// Silent fail - autocomplete is optional
		})
}

const currentFieldToken = computed(() => {
	if (!query.value) return ""
	const cursorPos = query.value.length
	const before = query.value.substring(0, cursorPos)
	// Match the last word being typed (field name token before a colon or standalone)
	const match = before.match(/(?:^|[\s(])([a-zA-Z_][\w.]*)$/)
	return match ? match[1] : ""
})

const filteredSuggestions = computed(() => {
	const token = currentFieldToken.value.toLowerCase()
	if (!token || token.length < 2) return []
	return fieldMappings.value.filter(f => f.field.toLowerCase().includes(token)).slice(0, 20)
})

function onQueryInput() {
	showSuggestions.value = currentFieldToken.value.length >= 2 && filteredSuggestions.value.length > 0
	activeSuggestionIndex.value = 0
}

function applySuggestion(fieldName: string) {
	const token = currentFieldToken.value
	if (token) {
		const lastIndex = query.value.lastIndexOf(token)
		query.value = query.value.substring(0, lastIndex) + fieldName + ":"
	}
	showSuggestions.value = false
}

function acceptSuggestion() {
	if (showSuggestions.value && filteredSuggestions.value.length > 0) {
		applySuggestion(filteredSuggestions.value[activeSuggestionIndex.value].field)
	}
}

// -- Events data --
const events = ref<EventSearchResult[]>([])
const totalEvents = ref(0)
const scrollId = ref<string | null>(null)
const loadingEvents = ref(false)
const loadingMore = ref(false)
const hasSearched = ref(false)

function resetResults() {
	events.value = []
	totalEvents.value = 0
	scrollId.value = null
	hasSearched.value = false
}

function searchEvents() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return

	loadingEvents.value = true
	hasSearched.value = true
	resetResults()

	Api.siem
		.queryEvents(selectedCustomerCode.value, selectedSourceName.value, {
			timerange: timerange.value,
			page_size: pageSize.value,
			query: query.value || undefined
		})
		.then(res => {
			if (res.data.success) {
				events.value = res.data.events || []
				totalEvents.value = res.data.total
				scrollId.value = res.data.scroll_id
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingEvents.value = false
		})
}

function loadMoreEvents() {
	if (!selectedCustomerCode.value || !selectedSourceName.value || !scrollId.value) return

	loadingMore.value = true

	Api.siem
		.queryEvents(selectedCustomerCode.value, selectedSourceName.value, {
			scroll_id: scrollId.value
		})
		.then(res => {
			if (res.data.success) {
				events.value.push(...(res.data.events || []))
				scrollId.value = res.data.scroll_id
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingMore.value = false
		})
}

// -- Table columns --
const columns = computed<DataTableColumns<EventSearchResult>>(() => {
	const baseColumns: DataTableColumns<EventSearchResult> = [
		{
			title: "Timestamp",
			key: "timestamp",
			width: 180,
			sorter: (a, b) => {
				const timeA = a.timestamp || a["@timestamp"] || ""
				const timeB = b.timestamp || b["@timestamp"] || ""
				return new Date(timeA).getTime() - new Date(timeB).getTime()
			},
			render(row) {
				const ts = row.timestamp || row["@timestamp"]
				if (!ts) return "-"
				return new Date(ts).toLocaleString()
			}
		},
		{
			title: "Source",
			key: "agent_name",
			width: 140,
			ellipsis: { tooltip: true },
			render(row) {
				return row.agent_name || row.source || "-"
			}
		},
		{
			title: "Rule",
			key: "rule_description",
			ellipsis: { tooltip: true },
			render(row) {
				return row.rule_description || row.rule_id || "-"
			}
		},
		{
			title: "Level",
			key: "rule_level",
			width: 80,
			sorter: (a, b) => (Number(a.rule_level) || 0) - (Number(b.rule_level) || 0),
			render(row) {
				if (row.rule_level === undefined || row.rule_level === null) return "-"
				const level = Number(row.rule_level)
				let type: "default" | "warning" | "error" | "success" | "info" = "default"
				if (level >= 12) type = "error"
				else if (level >= 8) type = "warning"
				else if (level >= 4) type = "info"
				return h("span", { class: `level-${type}` }, String(row.rule_level))
			}
		},
		{
			title: "Summary",
			key: "full_log",
			ellipsis: { tooltip: true },
			render(row) {
				return row.full_log || row.data || row.message || "-"
			}
		}
	]

	return baseColumns
})

// -- Event detail --
const showDetailDrawer = ref(false)
const selectedEvent = ref<EventSearchResult | null>(null)

function rowProps(row: EventSearchResult) {
	return {
		style: "cursor: pointer",
		onClick: () => {
			selectedEvent.value = row
			showDetailDrawer.value = true
		}
	}
}

function addFilterFromDetail(field: string, value: string) {
	const filterExpr = `${field}:"${value}"`
	if (query.value) {
		query.value += ` AND ${filterExpr}`
	} else {
		query.value = filterExpr
	}
	showDetailDrawer.value = false
	searchEvents()
}

function excludeFilterFromDetail(field: string, value: string) {
	const filterExpr = `NOT ${field}:"${value}"`
	if (query.value) {
		query.value += ` AND ${filterExpr}`
	} else {
		query.value = filterExpr
	}
	showDetailDrawer.value = false
	searchEvents()
}

// -- Lifecycle --
function applyRouteParams() {
	const qp = route.query
	if (qp.customer_code) {
		const code = String(qp.customer_code)
		selectedCustomerCode.value = code

		if (qp.query) {
			query.value = String(qp.query)
		}

		// Load event sources then auto-select source_name if provided
		loadingEventSources.value = true
		Api.siem
			.getEventSources(code)
			.then(res => {
				if (res.data.success) {
					eventSourcesList.value = res.data?.event_sources || []

					const targetSource = qp.source_name ? String(qp.source_name) : null
					if (targetSource) {
						// Try exact match first
						const match = eventSourcesList.value.find(s => s.name === targetSource && s.enabled)
						if (match) {
							selectedSourceName.value = match.name
						}
					} else {
						// Default to first EDR source if no source_name specified
						const edr = eventSourcesList.value.find(s => s.event_type === "EDR" && s.enabled)
						if (edr) {
							selectedSourceName.value = edr.name
						}
					}

					if (selectedSourceName.value) {
						loadFieldMappings()
						nextTick(() => searchEvents())
					}
				}
			})
			.finally(() => {
				loadingEventSources.value = false
			})
	}
}

onBeforeMount(() => {
	getCustomers().then(() => {
		applyRouteParams()
	})
})
</script>

<style scoped>
.suggestions-dropdown {
	border-color: var(--border-color);
}

.level-error {
	color: var(--error-color, #e88080);
	font-weight: 600;
}

.level-warning {
	color: var(--warning-color, #f0a020);
	font-weight: 600;
}

.level-info {
	color: var(--info-color, #70c0e8);
}
</style>
