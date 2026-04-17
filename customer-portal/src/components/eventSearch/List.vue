<template>
	<div class="flex flex-col gap-6">
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
			<div ref="headerRef" class="mb-4 flex w-full items-center justify-between">
				<p class="text-sm">
					Showing
					<span class="font-medium">{{ events.length }}</span>
					of
					<span class="font-medium">{{ totalEvents }}</span>
					events
				</p>
			</div>

			<n-data-table
				bordered
				size="small"
				:data="events"
				:columns
				:scroll-x="1500"
				class="[&_.n-data-table-th\_\_title]:whitespace-nowrap"
			>
				<template #empty>
					<n-empty description="No events found">
						<template #extra>Try adjusting your query or expanding the time range</template>
					</n-empty>
				</template>
			</n-data-table>

			<!-- Load More -->
			<div v-if="scrollId && events.length < totalEvents" class="mt-4 text-center">
				<n-button :loading @click="loadMoreEvents">
					{{ loading ? "Loading..." : "Load More" }}
				</n-button>
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

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { SearchFormLoad, SearchFormParams } from "@/components/eventSearch/SearchForm.vue"
import type { ApiError } from "@/types/common"
import type { EventSearchQueryParams, EventSearchResult } from "@/types/siem"
import { useElementSize } from "@vueuse/core"
import { NAlert, NButton, NDataTable, NEmpty, useMessage } from "naive-ui"
import { computed, ref, useTemplateRef } from "vue"
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

const { width: headerWidthRef } = useElementSize(useTemplateRef("headerRef"))
const simpleMode = computed(() => headerWidthRef.value < 600)

const columns = computed<DataTableColumns<EventSearchResult>>(() => [
	{
		title: "Timestamp",
		key: "Timestamp",
		fixed: simpleMode.value ? undefined : "left",
		width: 280,
		render: row => <div class="flex items-center gap-2">{formatTimestamp(row.timestamp || row["@timestamp"])}</div>
	},
	{
		title: "Source",
		key: "Source",
		width: 180,
		render: row => <div class="font-mono">{row.agent_name || row.agent?.name || "-"}</div>
	},
	{
		title: "Rule",
		key: "Rule",
		width: "100%",
		render: row => <div>{row.rule_description || row.rule?.description || "-"}</div>
	},
	{
		title: "Level",
		key: "Level",
		width: 200,
		render: row => (
			<div class="font-mono">
				<span
					class={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${levelClass(
						row.rule_level ?? row.rule?.level
					)}`}
				>
					{row.rule_level ?? row.rule?.level ?? "-"}
				</span>
			</div>
		)
	},
	{
		title: "Actions",
		key: "actions",
		minWidth: 180,
		render: row => {
			return <NButton onClick={() => selectEvent(row)}>View Details</NButton>
		}
	}
])

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
