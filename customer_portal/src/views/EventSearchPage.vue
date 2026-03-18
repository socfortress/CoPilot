<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Header -->
		<header class="border-b bg-white shadow-sm">
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div class="flex h-16 justify-between">
					<div class="flex items-center">
						<div class="mr-3 min-h-8">
							<img
								v-if="portalLogo && showLogo"
								class="h-8 w-auto"
								:src="portalLogo"
								:alt="portalTitle"
								@error="showLogo = false"
							/>
						</div>
						<h1 class="text-xl font-semibold text-gray-900">{{ portalTitle }}</h1>
						<nav class="ml-8 flex space-x-8">
							<router-link
								to="/"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Overview
							</router-link>
							<router-link
								to="/alerts"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Alerts
							</router-link>
							<router-link
								to="/cases"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Cases
							</router-link>
							<router-link
								to="/agents"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Agents
							</router-link>
							<router-link
								to="/event-search"
								class="rounded-md border-b-2 border-indigo-600 px-3 py-2 text-sm font-medium text-indigo-600"
							>
								Event Search
							</router-link>
							<router-link
								to="/dashboards"
								class="rounded-md px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-900"
							>
								Dashboards
							</router-link>
						</nav>
					</div>
					<div class="flex items-center space-x-4">
						<div class="text-sm text-gray-700">
							Welcome,
							<span class="font-medium">{{ username }}</span>
						</div>
						<button
							@click="logout"
							class="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
						>
							Logout
						</button>
					</div>
				</div>
			</div>
		</header>

		<!-- Main Content -->
		<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
			<!-- Search Controls -->
			<div class="mb-6 rounded-lg bg-white shadow">
				<div class="px-4 py-5 sm:p-6">
					<div class="mb-4 grid grid-cols-1 gap-4 md:grid-cols-4">
						<!-- Customer Code -->
						<div>
							<label for="customer-select" class="block text-sm font-medium text-gray-700">
								Customer
							</label>
							<select
								id="customer-select"
								v-model="selectedCustomerCode"
								@change="onCustomerChange"
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
							>
								<option value="">Select a customer</option>
								<option v-for="code in customerCodes" :key="code" :value="code">
									{{ code }}
								</option>
							</select>
						</div>

						<!-- Event Source -->
						<div>
							<label for="source-select" class="block text-sm font-medium text-gray-700">
								Event Source
							</label>
							<select
								id="source-select"
								v-model="selectedSourceName"
								@change="onSourceChange"
								:disabled="!selectedCustomerCode || loadingEventSources"
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:opacity-50 sm:text-sm"
							>
								<option value="">Select a source</option>
								<option v-for="src in enabledSources" :key="src.name" :value="src.name">
									{{ src.name }} ({{ src.event_type }})
								</option>
							</select>
						</div>

						<!-- Time Range -->
						<div>
							<label for="timerange-select" class="block text-sm font-medium text-gray-700">
								Time Range
							</label>
							<select
								id="timerange-select"
								v-model="timerange"
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
							>
								<option value="1h">Last 1 hour</option>
								<option value="6h">Last 6 hours</option>
								<option value="24h">Last 24 hours</option>
								<option value="2d">Last 2 days</option>
								<option value="7d">Last 7 days</option>
								<option value="14d">Last 14 days</option>
								<option value="30d">Last 30 days</option>
							</select>
						</div>

						<!-- Page Size -->
						<div>
							<label for="pagesize-select" class="block text-sm font-medium text-gray-700">
								Results per page
							</label>
							<select
								id="pagesize-select"
								v-model="pageSize"
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
							>
								<option :value="25">25</option>
								<option :value="50">50</option>
								<option :value="100">100</option>
								<option :value="250">250</option>
							</select>
						</div>
					</div>

					<!-- Query Bar -->
					<div class="relative">
						<label for="query-input" class="block text-sm font-medium text-gray-700">Lucene Query</label>
						<div class="relative mt-1">
							<input
								id="query-input"
								ref="queryInputRef"
								v-model="query"
								type="text"
								placeholder="e.g. agent_name:web-server AND rule_level:>=10"
								class="block w-full rounded-md border-gray-300 pr-24 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
								@input="onQueryInput"
								@keydown.enter="searchEvents"
								@keydown.tab.prevent="acceptSuggestion"
								@keydown.escape="showSuggestions = false"
							/>
							<button
								@click="searchEvents"
								:disabled="!selectedCustomerCode || !selectedSourceName || loadingEvents"
								class="absolute inset-y-0 right-0 inline-flex items-center rounded-r-md border border-transparent bg-indigo-600 px-4 text-sm font-medium text-white hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:opacity-50"
							>
								<svg
									v-if="loadingEvents"
									class="mr-1 h-4 w-4 animate-spin"
									fill="none"
									viewBox="0 0 24 24"
								>
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
								Search
							</button>
						</div>

						<!-- Autocomplete dropdown -->
						<ul
							v-if="showSuggestions && filteredSuggestions.length > 0"
							class="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-md border border-gray-200 bg-white shadow-lg"
						>
							<li
								v-for="(suggestion, idx) in filteredSuggestions"
								:key="suggestion.field"
								class="cursor-pointer px-3 py-2 text-sm hover:bg-indigo-50"
								:class="{ 'bg-indigo-50': idx === activeSuggestionIndex }"
								@mousedown.prevent="applySuggestion(suggestion.field)"
							>
								<span class="font-medium text-gray-900">{{ suggestion.field }}</span>
								<span class="ml-2 text-xs text-gray-400">{{ suggestion.type }}</span>
							</li>
						</ul>
					</div>
				</div>
			</div>

			<!-- No Event Sources Warning -->
			<div
				v-if="selectedCustomerCode && !loadingEventSources && eventSources.length === 0"
				class="mb-6 rounded-md border border-yellow-300 bg-yellow-50 p-4"
			>
				<div class="flex">
					<svg class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
						<path
							fill-rule="evenodd"
							d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
							clip-rule="evenodd"
						></path>
					</svg>
					<p class="ml-3 text-sm text-yellow-700">
						No event sources are configured for this customer. Contact your administrator to set up event
						sources.
					</p>
				</div>
			</div>

			<!-- Error -->
			<div v-if="error" class="mb-6 rounded-md border border-red-300 bg-red-50 p-4">
				<div class="flex">
					<svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
						<path
							fill-rule="evenodd"
							d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
							clip-rule="evenodd"
						></path>
					</svg>
					<p class="ml-3 text-sm text-red-700">{{ error }}</p>
				</div>
			</div>

			<!-- Loading -->
			<div v-if="loadingEvents" class="rounded-lg bg-white px-4 py-12 text-center shadow">
				<div class="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-indigo-600"></div>
				<p class="mt-2 text-sm text-gray-500">Searching events...</p>
			</div>

			<!-- Results -->
			<div v-else-if="hasSearched">
				<!-- Results Summary -->
				<div class="mb-4 flex items-center justify-between">
					<p class="text-sm text-gray-700">
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
						@click="loadMoreEvents"
						:disabled="loadingMore"
						class="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:opacity-50"
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
									@click="selectedEvent = null"
									class="rounded-md text-gray-400 hover:text-gray-500 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
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
									:key="key"
									class="group flex items-start justify-between py-3"
								>
									<dt class="min-w-0 flex-shrink-0 font-mono text-xs font-semibold text-gray-500">
										{{ key }}
									</dt>
									<dd class="ml-4 min-w-0 flex-1 text-right text-sm break-all text-gray-900">
										{{ formatValue(value) }}
									</dd>
									<div
										class="ml-2 flex shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100"
									>
										<button
											@click="addFilter(key, String(value))"
											title="Filter for this value"
											class="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600"
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
											@click="excludeFilter(key, String(value))"
											title="Exclude this value"
											class="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
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
import { ref, computed, onBeforeMount } from "vue"
import { useRouter, useRoute } from "vue-router"
import { usePortalSettingsStore } from "@/stores/portalSettings"
import { SiemAPI, type EventSource, type EventSearchResult, type FieldMapping } from "@/api/siem"

const router = useRouter()
const route = useRoute()
const portalSettingsStore = usePortalSettingsStore()

const showLogo = ref(true)
const error = ref("")

// Portal info
const username = computed(() => {
	try {
		const user = JSON.parse(localStorage.getItem("customer-portal-user") || "{}")
		return user.username || "User"
	} catch {
		return "User"
	}
})
const portalTitle = computed(() => portalSettingsStore.portalTitle || "Customer Portal")
const portalLogo = computed(() => portalSettingsStore.portalLogo)

function logout() {
	localStorage.removeItem("customer-portal-auth-token")
	localStorage.removeItem("customer-portal-user")
	router.push("/login")
}

// -- Customer selection --
const customerCodes = ref<string[]>([])
const selectedCustomerCode = ref("")

// -- Event Source selection --
const eventSources = ref<EventSource[]>([])
const loadingEventSources = ref(false)
const selectedSourceName = ref("")

const enabledSources = computed(() => eventSources.value.filter(s => s.enabled))

async function loadCustomerCodes() {
	try {
		const response = await SiemAPI.getCustomerCodes()
		customerCodes.value = response.customer_codes.filter(c => c !== "*")
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to load customer codes"
	}
}

async function loadEventSources(customerCode: string) {
	loadingEventSources.value = true
	eventSources.value = []
	selectedSourceName.value = ""
	fieldMappings.value = []
	try {
		const response = await SiemAPI.getEventSources(customerCode)
		eventSources.value = response.event_sources
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to load event sources"
	} finally {
		loadingEventSources.value = false
	}
}

function onCustomerChange() {
	resetResults()
	error.value = ""
	if (selectedCustomerCode.value) {
		loadEventSources(selectedCustomerCode.value)
	} else {
		eventSources.value = []
		selectedSourceName.value = ""
	}
}

function onSourceChange() {
	resetResults()
	if (selectedSourceName.value) {
		loadFieldMappings()
	}
}

// -- Search parameters --
const timerange = ref("24h")
const pageSize = ref(50)
const query = ref("")

// -- Field mappings / autocomplete --
const fieldMappings = ref<FieldMapping[]>([])
const showSuggestions = ref(false)
const activeSuggestionIndex = ref(0)
const queryInputRef = ref<HTMLInputElement | null>(null)

async function loadFieldMappings() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return
	try {
		const response = await SiemAPI.getFieldMappings(selectedCustomerCode.value, selectedSourceName.value)
		fieldMappings.value = response.fields
	} catch {
		// Non-critical, autocomplete just won't work
	}
}

const currentFieldToken = computed(() => {
	const text = query.value
	const match = text.match(/(?:^|[\s(])(\w[\w.]*)$/)
	return match ? match[1] : ""
})

const filteredSuggestions = computed(() => {
	const token = currentFieldToken.value.toLowerCase()
	if (!token || token.length < 2) return []
	return fieldMappings.value.filter(f => f.field.toLowerCase().includes(token)).slice(0, 15)
})

function onQueryInput() {
	showSuggestions.value = currentFieldToken.value.length >= 2
	activeSuggestionIndex.value = 0
}

function applySuggestion(fieldName: string) {
	const token = currentFieldToken.value
	if (token) {
		const lastIndex = query.value.lastIndexOf(token)
		query.value = query.value.substring(0, lastIndex) + fieldName + ":"
	}
	showSuggestions.value = false
	queryInputRef.value?.focus()
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

async function searchEvents() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return

	loadingEvents.value = true
	error.value = ""
	resetResults()

	try {
		const response = await SiemAPI.queryEvents(selectedCustomerCode.value, selectedSourceName.value, {
			timerange: timerange.value,
			page_size: pageSize.value,
			query: query.value || undefined
		})
		events.value = response.events
		totalEvents.value = response.total
		scrollId.value = response.scroll_id
		hasSearched.value = true
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to search events"
	} finally {
		loadingEvents.value = false
	}
}

async function loadMoreEvents() {
	if (!scrollId.value) return

	loadingMore.value = true
	try {
		const response = await SiemAPI.queryEvents(selectedCustomerCode.value, selectedSourceName.value, {
			scroll_id: scrollId.value
		})
		events.value.push(...response.events)
		scrollId.value = response.scroll_id
	} catch (err: any) {
		error.value = err.response?.data?.detail || err.message || "Failed to load more events"
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

// -- Lifecycle --
async function applyRouteParams() {
	const qCustomer = route.query.customer_code as string | undefined
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

onBeforeMount(async () => {
	await loadCustomerCodes()
	applyRouteParams()
})
</script>

<style scoped>
/* Tailwind handles all styles */
</style>
