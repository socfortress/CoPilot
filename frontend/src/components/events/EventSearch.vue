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
			:event-source="selectedEventSource"
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
			:title="`Configure columns: ${selectedEventSource?.name ?? ''}`"
			:style="{ width: 'min(720px, 92vw)' }"
			:mask-closable="false"
		>
			<ColumnConfig
				ref="columnConfigRef"
				:open="showColumnConfig"
				:event-source="selectedEventSource"
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
import type { DisplayColumn } from "@/types/event-sources"
import type { EventSearchResult, FieldMapping } from "@/types/events"
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
const loadingEvents = ref(false)
const loadingMore = ref(false)
const hasSearched = ref(false)

const showColumnConfig = ref(false)
const showDetailDrawer = ref(false)
const selectedEvent = ref<EventSearchResult | null>(null)
const columnConfigRef = useTemplateRef("columnConfigRef")

const selectedEventSource = computed(() => {
	const sourceName = searchFormParams.value?.sourceName
	const sources = searchFormLoad.value?.eventSources
	if (!sourceName || !sources) return null
	return sources.find(s => s.name === sourceName) ?? null
})

function handleFiltersSearch(params: EventSearchFiltersParams) {
	searchFormParams.value = params
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
	hasSearched.value = false
}

function searchEvents() {
	const params = searchFormParams.value
	if (!params?.customerCode || !params.sourceName) return

	loadingEvents.value = true
	hasSearched.value = true
	resetResults()

	const apiParams: { timerange?: string; page_size: number; query?: string; time_from?: string; time_to?: string } = {
		page_size: params.pageSize,
		query: params.query || undefined
	}
	if (params.timeMode === "absolute" && params.timeFrom && params.timeTo) {
		apiParams.time_from = new Date(params.timeFrom).toISOString()
		apiParams.time_to = new Date(params.timeTo).toISOString()
	} else {
		apiParams.timerange = params.timerange
	}

	Api.siem
		.queryEvents(params.customerCode, params.sourceName, apiParams)
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingEvents.value = false
		})
}

function loadMoreEvents() {
	const params = searchFormParams.value
	if (!params?.customerCode || !params.sourceName || !scrollId.value) return

	loadingMore.value = true

	Api.siem
		.queryEvents(params.customerCode, params.sourceName, {
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
	const source = selectedEventSource.value
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
