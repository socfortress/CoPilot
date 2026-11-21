<template>
	<div class="flex flex-col gap-4">
		<EventSearchFilters
			v-model:query="query"
			:loading-events
			@search="handleFiltersSearch"
			@loaded="handleFiltersLoaded"
			@field-mappings="fieldMappings = $event"
			@field-mappings-loading="fieldMappingsLoading = $event"
		/>

		<EventSearchResults
			:events
			:total-events
			:loading-events
			:loading-more
			:has-searched
			:scroll-id
			:warnings
			:event-sources="searchedEventSources"
			:customer-code="searchFormParams?.customerCode ?? null"
			@load-more="loadMoreEvents"
			@configure-columns="showColumnConfig = true"
			@row-select="openEventDetail"
		/>

		<n-drawer
			v-model:show="showDetailDrawer"
			display-directive="show"
			:trap-focus="false"
			:style="{ width: 'min(600px, 90vw)' }"
		>
			<n-drawer-content title="Event Details" closable :native-scrollbar="false">
				<EventDetail
					:event="selectedEvent"
					@filter-add="addFilterFromDetail"
					@filter-exclude="excludeFilterFromDetail"
				/>
			</n-drawer-content>
		</n-drawer>

		<n-modal
			v-model:show="showColumnConfig"
			preset="card"
			display-directive="show"
			:title="`Configure columns: ${columnsEventSource?.name ?? ''}`"
			:style="{ width: 'min(720px, 92vw)' }"
			:mask-closable="false"
		>
			<ColumnConfig
				ref="columnConfigRef"
				:open="showColumnConfig"
				:event-source="columnsEventSource"
				:field-mappings
				:loading-field-mappings="fieldMappingsLoading"
				@close="showColumnConfig = false"
				@saved="onColumnsSaved"
			/>

			<template #footer>
				<div class="flex items-center justify-between gap-2">
					<n-button text @click="columnConfigRef?.resetToDefaults()">Reset to defaults</n-button>
					<div class="flex gap-2">
						<n-button @click="showColumnConfig = false">Cancel</n-button>
						<n-button type="primary" :loading="columnConfigRef?.saving" @click="columnConfigRef?.onSave()">
							Save
						</n-button>
					</div>
				</div>
			</template>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { EventSearchFiltersLoad, EventSearchFiltersParams } from "./EventSearchFilters.vue"
import type { ApiError } from "@/types/common"
import type { DisplayColumn, EventSource } from "@/types/event-sources"
import type { EventSearchResult, EventsPage, EventsQueryParams, FieldMapping } from "@/types/events"
import { NButton, NDrawer, NDrawerContent, NModal, useMessage } from "naive-ui"
import { computed, ref, useTemplateRef } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import ColumnConfig from "./ColumnConfig.vue"
import EventDetail from "./EventDetail.vue"
import EventSearchFilters from "./EventSearchFilters.vue"
import EventSearchResults from "./EventSearchResults.vue"

const message = useMessage()

const searchFormParams = ref<EventSearchFiltersParams | null>(null)
const searchFormLoad = ref<EventSearchFiltersLoad | null>(null)
const query = ref("")
const fieldMappings = ref<FieldMapping[]>([])
const fieldMappingsLoading = ref(false)

const events = ref<EventSearchResult[]>([])
const totalEvents = ref(0)
const scrollId = ref<string | null>(null)
const warnings = ref<string[]>([])
const loadingEvents = ref(false)
const loadingMore = ref(false)
const hasSearched = ref(false)

const showColumnConfig = ref(false)
const showDetailDrawer = ref(false)
const selectedEvent = ref<EventSearchResult | null>(null)
const columnConfigRef = useTemplateRef("columnConfigRef")

/**
 * The sources of the last search, in the order they were picked, kept as they were when it ran:
 * the filter bar reloads its list when the customer changes, and the results on screen are still
 * the last search's.
 */
const searchedEventSources = ref<EventSource[]>([])

/** Columns are configured per source, so only while one source is searched. */
const columnsEventSource = computed(() =>
	searchedEventSources.value.length === 1 ? searchedEventSources.value[0] : null
)

function handleFiltersSearch(params: EventSearchFiltersParams) {
	searchFormParams.value = params
	const load = searchFormLoad.value
	const sources = load?.customerCode === params.customerCode ? load.eventSources : []
	searchedEventSources.value = params.sourceNames
		.map(name => sources.find(s => s.name === name))
		.filter((s): s is EventSource => s !== undefined)
	fieldMappings.value = params.fieldMappings
	searchEvents()
}

function handleFiltersLoaded(load: EventSearchFiltersLoad) {
	searchFormLoad.value = load
}

function resetResults() {
	events.value = []
	totalEvents.value = 0
	scrollId.value = null
	warnings.value = []
	hasSearched.value = false
}

/** One source keeps its own route (the Customer Portal's too); several go to the route that searches them together. */
function fetchEvents(params: EventSearchFiltersParams, apiParams: EventsQueryParams) {
	const [first, ...rest] = params.sourceNames
	if (!rest.length) {
		return Api.siem.queryEvents({ customerCode: params.customerCode, sourceName: first, params: apiParams })
	}
	return Api.siem.queryEventsMulti(params.customerCode, { ...apiParams, sources: params.sourceNames })
}

function addWarnings(page: EventsPage) {
	warnings.value = [...new Set([...warnings.value, ...(page.warnings ?? [])])]
}

function searchEvents() {
	const params = searchFormParams.value
	if (!params?.customerCode || !params.sourceNames.length) return

	loadingEvents.value = true
	hasSearched.value = true
	resetResults()

	const apiParams: EventsQueryParams = {
		page_size: params.pageSize,
		query: params.query || undefined
	}
	if (params.timeMode === "absolute" && params.timeFrom && params.timeTo) {
		apiParams.time_from = new Date(params.timeFrom).toISOString()
		apiParams.time_to = new Date(params.timeTo).toISOString()
	} else {
		apiParams.timerange = params.timerange
	}

	fetchEvents(params, apiParams)
		.then(res => {
			if (res.data.success) {
				events.value = res.data.events || []
				totalEvents.value = res.data.total
				scrollId.value = res.data.scroll_id
				addWarnings(res.data)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingEvents.value = false
		})
}

function loadMoreEvents() {
	const params = searchFormParams.value
	if (!params?.customerCode || !params.sourceNames.length || !scrollId.value) return

	loadingMore.value = true

	fetchEvents(params, { scroll_id: scrollId.value })
		.then(res => {
			if (res.data.success) {
				events.value.push(...(res.data.events || []))
				scrollId.value = res.data.scroll_id
				addWarnings(res.data)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingMore.value = false
		})
}

function openEventDetail(event: EventSearchResult) {
	selectedEvent.value = event
	showDetailDrawer.value = true
}

function onColumnsSaved(saved: DisplayColumn[] | null) {
	const source = columnsEventSource.value
	if (source) {
		source.displayed_columns = saved
	}
}

function addFilterFromDetail(field: string, value: string) {
	const filterExpr = `${field}:"${value}"`
	query.value = query.value ? `${query.value} AND ${filterExpr}` : filterExpr
	if (searchFormParams.value) {
		searchFormParams.value = { ...searchFormParams.value, query: query.value }
	}
	showDetailDrawer.value = false
	searchEvents()
}

function excludeFilterFromDetail(field: string, value: string) {
	const filterExpr = `NOT ${field}:"${value}"`
	query.value = query.value ? `${query.value} AND ${filterExpr}` : filterExpr
	if (searchFormParams.value) {
		searchFormParams.value = { ...searchFormParams.value, query: query.value }
	}
	showDetailDrawer.value = false
	searchEvents()
}
</script>
