<template>
	<div class="page @container flex flex-col gap-6">
		<div class="grid grid-cols-1 gap-6 @3xl:grid-cols-2">
			<n-form-item label="Customer" :show-feedback="false">
				<n-input v-model:value="selectedCustomerCode" disabled />
			</n-form-item>

			<n-form-item label="Event Source" :show-feedback="false">
				<n-select
					v-model:value="selectedSourceName"
					placeholder="Select Source"
					filterable
					:options="eventSourceOptions"
					:disabled="!selectedCustomerCode"
					:loading="loadingEventSources"
				/>
			</n-form-item>

			<n-form-item label="Time Range" :show-feedback="false">
				<n-input-group class="w-full">
					<n-input-number
						v-if="timerangeMode === 'relative'"
						v-model:value="filterTimeRange.time"
						:min="1"
						placeholder="Time"
						class="grow text-right [&_input]:pr-3!"
					/>
					<n-select
						v-if="timerangeMode === 'relative'"
						v-model:value="filterTimeRange.unit"
						:options="unitOptions"
						placeholder="Time unit"
						class="w-40!"
					/>
					<n-date-picker
						v-if="timerangeMode === 'absolute'"
						v-model:value="daterange"
						type="datetimerange"
						clearable
						class="grow"
					/>
					<n-button v-if="timerangeMode === 'relative'" secondary @click="timerangeMode = 'absolute'">
						<template #icon>
							<Icon name="carbon:calendar" />
						</template>
					</n-button>
					<n-button v-if="timerangeMode === 'absolute'" secondary @click="timerangeMode = 'relative'">
						<template #icon>
							<Icon name="carbon:reset" />
						</template>
					</n-button>
				</n-input-group>
			</n-form-item>

			<n-form-item label="Results per page" :show-feedback="false">
				<n-select v-model:value="pageSize" :options="pageSizeOptions" />
			</n-form-item>

			<n-form-item label="Lucene Query" :show-feedback="false" class="col-span-full">
				<n-input-group class="w-full">
					<n-mention
						v-model:value="query"
						placeholder="e.g. agent_name:web-server AND rule_level:>=10"
						:options="suggestionOptions"
						:prefix="['#']"
						@select="onMentionSelect"
					/>

					<n-button
						secondary
						:loading="loadingEvents"
						:disabled="!selectedCustomerCode || !selectedSourceName"
						@click="searchEvents"
					>
						<template #icon>
							<Icon name="carbon:search" />
						</template>
						Search
					</n-button>
				</n-input-group>
			</n-form-item>
		</div>

		<!-- No Event Sources Warning -->
		<n-alert
			v-if="selectedCustomerCode && !loadingEventSources && eventSources.length === 0"
			type="warning"
			title="No Event Sources Configured"
		>
			No event sources are configured for this customer. Contact your administrator to set up event sources.
		</n-alert>

		<!-- Results -->
		<div v-if="hasSearched">
			<!-- Results Summary -->
			<div class="mb-4 flex items-center justify-between">
				<p class="text-sm">
					Showing
					<span class="font-medium">{{ events.length }}</span>
					of
					<span class="font-medium">{{ totalEvents }}</span>
					events
				</p>
			</div>

			<!-- Events Table -->
			<div v-if="events.length > 0" class="overflow-hidden rounded-lg bg-white shadow">
				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-gray-200">
						<thead class="bg-gray-50">
							<tr>
								<th
									class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								>
									Timestamp
								</th>
								<th
									class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								>
									Source
								</th>
								<th
									class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								>
									Rule
								</th>
								<th
									class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								>
									Level
								</th>
								<th
									class="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								>
									Summary
								</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 bg-white">
							<tr
								v-for="(event, idx) in events"
								:key="idx"
								class="cursor-pointer hover:bg-gray-50"
								@click="selectEvent(event)"
							>
								<td class="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
									{{ formatTimestamp(event.timestamp || event["@timestamp"]) }}
								</td>
								<td class="px-6 py-4 text-sm whitespace-nowrap text-gray-900">
									{{ event.agent_name || event.agent?.name || "-" }}
								</td>
								<td class="max-w-xs truncate px-6 py-4 text-sm text-gray-900">
									{{ event.rule_description || event.rule?.description || "-" }}
								</td>
								<td class="px-6 py-4 text-sm whitespace-nowrap">
									<span
										class="inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium"
										:class="levelClass(event.rule_level ?? event.rule?.level)"
									>
										{{ event.rule_level ?? event.rule?.level ?? "-" }}
									</span>
								</td>
								<td class="max-w-sm truncate px-6 py-4 text-sm text-gray-500">
									{{ event.full_log || event.data || "-" }}
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</div>

			<!-- Empty State -->
			<div v-else class="rounded-lg bg-white px-4 py-12 text-center shadow">
				<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
					></path>
				</svg>
				<h3 class="mt-2 text-sm font-medium text-gray-900">No events found</h3>
				<p class="mt-1 text-sm text-gray-500">Try adjusting your query or expanding the time range.</p>
			</div>

			<!-- Load More -->
			<div v-if="scrollId && events.length < totalEvents" class="mt-4 text-center">
				<button
					:disabled="loadingMore"
					class="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:opacity-50"
					@click="loadMoreEvents"
				>
					<svg v-if="loadingMore" class="mr-2 -ml-1 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle
							class="opacity-25"
							cx="12"
							cy="12"
							r="10"
							stroke="currentColor"
							stroke-width="4"
						></circle>
						<path
							class="opacity-75"
							fill="currentColor"
							d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
						></path>
					</svg>
					{{ loadingMore ? "Loading..." : "Load More" }}
				</button>
			</div>
		</div>

		<!-- Event Detail Slide-over -->
		<div v-if="selectedEvent" class="fixed inset-0 z-50 overflow-hidden" @click="selectedEvent = null">
			<div class="absolute inset-0 bg-gray-500/50 transition-opacity"></div>
			<div class="fixed inset-y-0 right-0 flex max-w-full pl-10" @click.stop>
				<div class="w-screen max-w-lg">
					<div class="flex h-full flex-col overflow-y-scroll bg-white shadow-xl">
						<!-- Header -->
						<div class="border-b border-gray-200 bg-gray-50 px-4 py-6 sm:px-6">
							<div class="flex items-start justify-between">
								<h2 class="text-lg font-medium text-gray-900">Event Details</h2>
								<button
									class="rounded-md text-gray-400 hover:text-gray-500 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
									@click="selectedEvent = null"
								>
									<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M6 18L18 6M6 6l12 12"
										></path>
									</svg>
								</button>
							</div>
						</div>

						<!-- Fields -->
						<div class="flex-1 px-4 py-4 sm:px-6">
							<dl class="divide-y divide-gray-200">
								<div
									v-for="[key, value] in sortedEventFields"
									:key
									class="group flex items-start justify-between py-3"
								>
									<dt class="min-w-0 shrink-0 font-mono text-xs font-semibold text-gray-500">
										{{ key }}
									</dt>
									<dd class="ml-4 min-w-0 flex-1 text-right text-sm break-all text-gray-900">
										{{ formatValue(value) }}
									</dd>
									<div
										class="ml-2 flex shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100"
									>
										<button
											title="Filter for this value"
											class="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600"
											@click="addFilter(key, String(value))"
										>
											<svg
												class="h-3.5 w-3.5"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M12 4v16m8-8H4"
												></path>
											</svg>
										</button>
										<button
											title="Exclude this value"
											class="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
											@click="excludeFilter(key, String(value))"
										>
											<svg
												class="h-3.5 w-3.5"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M20 12H4"
												></path>
											</svg>
										</button>
									</div>
								</div>
							</dl>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { MentionOption } from "naive-ui"
import type { ApiError } from "@/types/common"
import type {
	EventSearchQueryParams,
	EventSearchQueryTimerange,
	EventSearchResult,
	EventSourceItem,
	FieldMapping
} from "@/types/siem"
import {
	NAlert,
	NButton,
	NDatePicker,
	NFormItem,
	NInput,
	NInputGroup,
	NInputNumber,
	NMention,
	NSelect,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"

const TRAILING_WHITESPACE_RE = /\s$/

const route = useRoute()
const authStore = useAuthStore()
const message = useMessage()

const customerCode = computed(() => authStore.userCustomerCode)
const selectedCustomerCode = ref(customerCode.value || "")

const eventSources = ref<EventSourceItem[]>([])
const loadingEventSources = ref(false)
const selectedSourceName = ref<string | null>(null)
const enabledSources = computed(() => eventSources.value.filter(s => s.enabled))
const eventSourceOptions = computed(() =>
	enabledSources.value.map(s => ({ label: `${s.name} (${s.event_type})`, value: s.name }))
)

const filterTimeRange = ref<{ unit: "h" | "d" | "w"; time: number }>({
	unit: "h",
	time: 24
})
const unitOptions: { label: string; value: "h" | "d" | "w" }[] = [
	{ label: "Hours", value: "h" },
	{ label: "Days", value: "d" },
	{ label: "Weeks", value: "w" }
]
const timerange = computed<EventSearchQueryTimerange>(
	() => `${filterTimeRange.value.time}${filterTimeRange.value.unit}`
)
const daterange = ref<[number, number]>([1183135260000, Date.now()])
const timerangeMode = ref<"relative" | "absolute">("relative")

const pageSizeOptions = [
	{ label: "25", value: 25 },
	{ label: "50", value: 50 },
	{ label: "100", value: 100 },
	{ label: "250", value: 250 }
]
const pageSize = ref(pageSizeOptions[1].value)
const query = ref<string | undefined>(undefined)

const fieldMappings = ref<FieldMapping[]>([])

async function loadEventSources(customerCode: string) {
	loadingEventSources.value = true
	eventSources.value = []
	selectedSourceName.value = null
	fieldMappings.value = []
	try {
		const response = await Api.siem.getEventSources(customerCode)
		eventSources.value = response.data.event_sources
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load event sources")
	} finally {
		loadingEventSources.value = false
	}
}

function onSourceChange() {
	resetResults()

	if (selectedSourceName.value) {
		loadFieldMappings()
	}
}

async function loadFieldMappings() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return
	try {
		const response = await Api.siem.getFieldMappings(selectedCustomerCode.value, selectedSourceName.value)
		fieldMappings.value = response.data.fields
	} catch {
		// Non-critical, autocomplete just won't work
	}
}

const suggestionOptions = computed(() => {
	return fieldMappings.value.map(f => ({ label: `${f.field}  [${f.type}]`, value: f.field }))
})

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

async function searchEvents() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return

	loadingEvents.value = true
	resetResults()

	try {
		const params: EventSearchQueryParams = {
			page_size: pageSize.value,
			query: query.value || undefined
		}
		if (timerangeMode.value === "absolute") {
			params.time_from = new Date(daterange.value[0]).toISOString()
			params.time_to = new Date(daterange.value[1]).toISOString()
		} else {
			params.timerange = timerange.value
		}

		const response = await Api.siem.queryEvents(selectedCustomerCode.value, selectedSourceName.value, params)
		events.value = response.data.events
		totalEvents.value = response.data.total
		scrollId.value = response.data.scroll_id
		hasSearched.value = true
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to search events")
	} finally {
		loadingEvents.value = false
	}
}

async function loadMoreEvents() {
	if (!scrollId.value) return

	loadingMore.value = true
	try {
		const response = await Api.siem.queryEvents(selectedCustomerCode.value, selectedSourceName.value || "", {
			scroll_id: scrollId.value
		})
		events.value.push(...response.data.events)
		scrollId.value = response.data.scroll_id
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load more events")
	} finally {
		loadingMore.value = false
	}
}

// -- Event detail --
const selectedEvent = ref<EventSearchResult | null>(null)

function selectEvent(event: EventSearchResult) {
	selectedEvent.value = event
}

const sortedEventFields = computed(() => {
	if (!selectedEvent.value) return []
	return Object.entries(selectedEvent.value)
		.filter(([key]) => !key.startsWith("_"))
		.sort(([a], [b]) => a.localeCompare(b))
})

function addFilter(field: string, value: string) {
	const clause = `${field}:"${value}"`
	query.value = query.value ? `${query.value} AND ${clause}` : clause
	selectedEvent.value = null
	searchEvents()
}

function excludeFilter(field: string, value: string) {
	const clause = `NOT ${field}:"${value}"`
	query.value = query.value ? `${query.value} AND ${clause}` : clause
	selectedEvent.value = null
	searchEvents()
}

// -- Formatting helpers --
function formatTimestamp(ts: string | undefined): string {
	if (!ts) return "-"
	try {
		return new Date(ts).toLocaleString()
	} catch {
		return ts
	}
}

function formatValue(value: unknown): string {
	if (value === null || value === undefined) return "-"
	if (typeof value === "object") return JSON.stringify(value)
	return String(value)
}

function levelClass(level: number | undefined): string {
	if (level === undefined || level === null) return "bg-gray-100 text-gray-800"
	if (level >= 12) return "bg-red-100 text-red-800"
	if (level >= 8) return "bg-yellow-100 text-yellow-800"
	if (level >= 4) return "bg-blue-100 text-blue-800"
	return "bg-gray-100 text-gray-800"
}

function onMentionSelect(option: MentionOption, prefix: string) {
	// Current query text and the raw token as typed in the mention (e.g. "#field")
	const currentQuery = query.value || ""
	const target = `${prefix}${option.value}`

	// Find the last occurrence of the typed token to replace it
	const lastIndex = currentQuery.lastIndexOf(target)

	if (lastIndex === -1) {
		// If the token is not found, append the field followed by ":" at the end of the query
		const needsSpace = currentQuery.length > 0 && !TRAILING_WHITESPACE_RE.test(currentQuery)
		query.value = `${currentQuery}${needsSpace ? " " : ""}${option.value}:`
		return
	}

	// Split query around the matched token
	const before = currentQuery.slice(0, lastIndex)
	const after = currentQuery.slice(lastIndex + target.length)

	// Rebuild query replacing the token with the plain field name followed by ":"
	const needsSpace = before.length > 0 && !TRAILING_WHITESPACE_RE.test(before)
	const replacement = `${needsSpace ? " " : ""}${option.value}:`

	query.value = `${before}${replacement}${after}`
}

// -- Lifecycle --
async function applyRouteParams() {
	const qCustomer = (route.query.customer_code || customerCode.value) as string
	const qSource = route.query.source_name as string | undefined
	const qQuery = route.query.query as string | undefined

	if (!qCustomer) return

	selectedCustomerCode.value = qCustomer
	await loadEventSources(qCustomer)

	if (qSource) {
		const match = enabledSources.value.find(s => s.name === qSource)
		if (match) {
			selectedSourceName.value = match.name
			loadFieldMappings()
		}
	}

	if (qQuery) {
		query.value = qQuery
	}

	if (selectedCustomerCode.value && selectedSourceName.value) {
		searchEvents()
	}
}

watch(selectedSourceName, onSourceChange)

onBeforeMount(() => {
	applyRouteParams()
})
</script>
