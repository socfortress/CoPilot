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
			<div ref="headerRef" class="mb-1 flex w-full items-center">
				<p class="text-sm">
					Showing
					<span class="font-semibold">{{ events.length }}</span>
					of
					<span class="font-semibold">{{ totalEvents }}</span>
					events
				</p>
			</div>

			<n-data-table
				bordered
				size="small"
				:data="events"
				:columns
				:scroll-x="1200"
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
					{{ loading ? "Loading..." : `Showing ${events.length} of ${totalEvents} events • Load More` }}
				</n-button>
			</div>
		</div>

		<EventDetails
			:event="selectedEvent"
			@filter-add="addFilter"
			@filter-exclude="excludeFilter"
			@close="selectedEvent = null"
		/>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns, TagProps } from "naive-ui"
import type { SearchFormLoad, SearchFormParams } from "@/components/eventSearch/SearchForm.vue"
import type { ApiError } from "@/types/common"
import type { EventSearchQueryParams, EventSearchResult } from "@/types/siem"
import { useElementSize } from "@vueuse/core"
import { NAlert, NButton, NDataTable, NEmpty, useMessage } from "naive-ui"
import { computed, ref, useTemplateRef } from "vue"
import Api from "@/api"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import EventDetails from "@/components/eventSearch/EventDetails.vue"
import SearchForm from "@/components/eventSearch/SearchForm.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const searchFormParams = ref<SearchFormParams | null>(null)
const searchFormLoad = ref<SearchFormLoad | null>(null)
const query = ref<string | undefined>(undefined)

const events = ref<EventSearchResult[]>([])
const totalEvents = ref(0)
const scrollId = ref<string | null>(null)
const loading = ref(false)
const hasSearched = ref(false)

const selectedEvent = ref<EventSearchResult | null>(null)

function selectEvent(event: EventSearchResult) {
	selectedEvent.value = event
}

const { width: headerWidthRef } = useElementSize(useTemplateRef("headerRef"))
const simpleMode = computed(() => headerWidthRef.value < 600)

const columns = computed<DataTableColumns<EventSearchResult>>(() => [
	{
		title: "Timestamp",
		key: "Timestamp",
		fixed: simpleMode.value ? undefined : "left",
		width: 160,
		render: row => <div class="font-mono">{formatDate(row.timestamp || row["@timestamp"], dFormats.datetime)}</div>
	},
	{
		title: "Level",
		key: "Level",
		width: 60,
		render: row => (
			<Chip
				type={levelClass(row.rule_level ?? row.rule?.level)}
				value={row.rule_level ?? row.rule?.level ?? "-"}
				round
			/>
		)
	},
	{
		title: "Source",
		key: "Source",
		render: row => <div>{row.agent_name || row.agent?.name || "-"}</div>
	},
	{
		title: "Rule",
		key: "Rule",
		render: row => <div>{row.rule_description || row.rule?.description || "-"}</div>
	},
	{
		title: "Actions",
		key: "actions",
		width: 150,
		fixed: simpleMode.value ? undefined : "right",
		render: row => {
			return (
				<NButton
					onClick={() => selectEvent(row)}
					v-slots={{
						icon: () => <Icon name="carbon:view" />
					}}
				>
					View Details
				</NButton>
			)
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

function addFilter(field: string, value: string) {
	const clause = `${field}:"${value}"`
	query.value = query.value ? `${query.value} AND ${clause}` : clause
}

function excludeFilter(field: string, value: string) {
	const clause = `NOT ${field}:"${value}"`
	query.value = query.value ? `${query.value} AND ${clause}` : clause
}

function levelClass(level: number | undefined): TagProps["type"] | undefined {
	if (level === undefined || level === null) return undefined
	if (level >= 12) return "error"
	if (level >= 8) return "warning"
	if (level >= 4) return "info"
	return "default"
}
</script>
