<template>
	<div class="page @container flex flex-col gap-6">
		<SearchForm v-model:query="query" :loading @search="handleSearchFormSearch" @loaded="handleSearchFormLoaded" />

		<!-- No Event Sources Warning -->
		<n-alert
			v-if="searchFormLoad?.customerCode && !loading && searchFormLoad?.eventSources.length === 0"
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
					:disabled="loading"
					class="inline-flex items-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none disabled:opacity-50"
					@click="loadMoreEvents"
				>
					<svg v-if="loading" class="mr-2 -ml-1 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
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
					{{ loading ? "Loading..." : "Load More" }}
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
import type { SearchFormLoad, SearchFormParams } from "@/components/eventSearch/SearchForm.vue"
import type { ApiError } from "@/types/common"
import type { EventSearchQueryParams, EventSearchResult } from "@/types/siem"
import { NAlert, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import SearchForm from "@/components/eventSearch/SearchForm.vue"
import { getApiErrorMessage } from "@/utils"

const message = useMessage()

const searchFormParams = ref<SearchFormParams | null>(null)
const searchFormLoad = ref<SearchFormLoad | null>(null)
const query = ref<string | undefined>(undefined)

const events = ref<EventSearchResult[]>([])
const totalEvents = ref(0)
const scrollId = ref<string | null>(null)
const loading = ref(false)
const hasSearched = ref(false)

function handleSearchFormSearch(params: SearchFormParams) {
	searchFormParams.value = params
	searchEvents()
}

function handleSearchFormLoaded(load: SearchFormLoad) {
	searchFormLoad.value = load
}

function resetResults() {
	events.value = []
	totalEvents.value = 0
	scrollId.value = null
	hasSearched.value = false
}

async function searchEvents() {
	if (!searchFormParams.value) return
	const payload = searchFormParams.value

	if (!payload.customerCode || !payload.sourceName) return

	loading.value = true
	resetResults()

	try {
		const params: EventSearchQueryParams = {
			page_size: payload.pageSize,
			query: payload.query || undefined
		}
		if (payload.timeMode === "absolute" && payload.timeFrom && payload.timeTo) {
			params.time_from = new Date(payload.timeFrom).toISOString()
			params.time_to = new Date(payload.timeTo).toISOString()
		} else {
			params.timerange = payload.timerange
		}

		const response = await Api.siem.queryEvents(payload.customerCode, payload.sourceName, params)

		events.value = response.data.events
		totalEvents.value = response.data.total
		scrollId.value = response.data.scroll_id
		hasSearched.value = true
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to search events")
	} finally {
		loading.value = false
	}
}

async function loadMoreEvents() {
	if (!scrollId.value) return

	loading.value = true

	try {
		const response = await Api.siem.queryEvents(
			searchFormParams.value?.customerCode || "",
			searchFormParams.value?.sourceName || "",
			{
				scroll_id: scrollId.value
			}
		)

		events.value.push(...response.data.events)
		scrollId.value = response.data.scroll_id
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load more events")
	} finally {
		loading.value = false
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
</script>
