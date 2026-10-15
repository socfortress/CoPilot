<template>
	<div class="flex flex-col gap-6">
		<SearchForm
			v-model:query="query"
			:loading-events="loading"
			@search="handleSearchFormSearch"
			@loaded="handleSearchFormLoaded"
			@fields="fields = $event"
		/>

		<!-- Results -->
		<div v-if="hasSearched" class="flex flex-col gap-2">
			<!-- What is loaded, then the tools for it: the columns, and the export of what is loaded. -->
			<div ref="headerRef" class="flex w-full flex-wrap items-center gap-2" data-testid="event-results-toolbar">
				<p class="m-0 text-sm" data-testid="event-results-count">
					<span class="font-semibold tabular-nums">{{ events.length.toLocaleString() }}</span>
					of
					<span class="font-semibold tabular-nums">{{ totalEvents.toLocaleString() }}</span>
					events loaded
				</p>
				<div class="ml-auto flex items-center gap-2">
					<n-button size="small" secondary data-testid="event-columns-toggle" @click="showColumns = true">
						<template #icon><Icon name="carbon:column" /></template>
						Columns
						<span v-if="userColumns" class="bg-primary ml-1.5 size-1.5 rounded-full" title="Your own columns" />
					</n-button>
					<n-button
						size="small"
						secondary
						:disabled="!events.length"
						data-testid="event-export"
						@click="exportCsv"
					>
						<template #icon><Icon name="carbon:download" /></template>
						Export CSV
					</n-button>
				</div>
			</div>

			<n-data-table
				bordered
				size="small"
				:data="events"
				:columns
				:scroll-x="1200"
				class="[&_.n-data-table-th\_\_title]:whitespace-nowrap"
				data-testid="event-results"
			>
				<template #empty>
					<n-empty description="No events found">
						<template #extra>Try adjusting your query or expanding the time range</template>
					</n-empty>
				</template>
			</n-data-table>

			<!-- Load More -->
			<div v-if="scrollId && events.length < totalEvents" class="mt-2 text-center">
				<n-button :loading @click="loadMoreEvents">
					{{ loading ? "Loading..." : `Showing ${events.length} of ${totalEvents} events • Load More` }}
				</n-button>
			</div>
		</div>

		<n-modal
			v-model:show="showColumns"
			preset="card"
			:title="`Columns · ${selectedEventSource?.name ?? ''}`"
			:style="{ maxWidth: 'min(640px, 94vw)' }"
			segmented
		>
			<EventColumnPicker
				v-if="showColumns"
				:current="pickerStart"
				:personal="!!userColumns"
				:source-columns="selectedEventSource?.displayed_columns"
				:fields
				:saving="savingColumns"
				@save="applyColumns"
				@cancel="showColumns = false"
			/>
		</n-modal>

		<EventDetails
			:event="selectedEvent"
			:time-field="selectedEventSource?.time_field"
			@filter-add="addFilter"
			@filter-exclude="excludeFilter"
			@close="selectedEvent = null"
		/>
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumn, DataTableColumns, TagProps } from "naive-ui"
import type { EventColumn } from "./eventColumns"
import type { SearchFormLoad, SearchFormParams } from "@/components/eventSearch/SearchForm.vue"
import type { ApiError } from "@/types/common"
import type {
	DisplayColumn,
	EventSearchQueryParams,
	EventSearchResult,
	EventSourceItem,
	FieldMapping
} from "@/types/siem"
import { useElementSize } from "@vueuse/core"
import { NButton, NDataTable, NEmpty, NModal, useMessage } from "naive-ui"
import { computed, ref, useTemplateRef } from "vue"
import Api from "@/api"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import EventDetails from "@/components/eventSearch/EventDetails.vue"
import SearchForm from "@/components/eventSearch/SearchForm.vue"
import { useSettingsStore } from "@/stores/settings"
import { downloadCsv, getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import EventColumnPicker from "./EventColumnPicker.vue"
import {
	cellText,
	columnValue,
	eventLevel,
	eventsFilename,
	eventsToCsv,
	parseEventTime,
	resolveColumns
} from "./eventColumns"
import { useEventSearchMemory } from "./useEventSearchMemory"

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

const showColumns = ref(false)
const fields = ref<FieldMapping[]>([])
const memory = useEventSearchMemory(() => searchFormLoad.value?.customerCode ?? searchFormParams.value?.customerCode)

const selectedEventSource = computed<EventSourceItem | null>(() => {
	const sourceName = searchFormParams.value?.sourceName
	const sources = searchFormLoad.value?.eventSources
	if (!sourceName || !sources) return null
	return sources.find(s => s.name === sourceName) ?? null
})
const timeField = computed(() => selectedEventSource.value?.time_field)

/**
 * Renders an event time in the viewer's local timezone. `tz: true` is what makes offset-less
 * timestamps — which several sources emit — be read as UTC instead of as local time; without it
 * they render as the raw UTC clock and appear shifted by the viewer's offset.
 */
function formatEventTime(value: unknown): string {
	return String(formatDate(typeof value === "number" ? value : `${value}`, dFormats.datetime, { tz: true }))
}

function present(value: unknown): boolean {
	return value !== undefined && value !== null && value !== ""
}

// The columns in force (#1258): the user's own for this source, else the SOC's, else the
// default layout. The table renders them and the CSV export writes the same ones.
const userColumns = computed(() => memory.columnsFor(selectedEventSource.value?.name))
const eventColumns = computed<EventColumn[]>(() =>
	resolveColumns(userColumns.value, selectedEventSource.value?.displayed_columns, timeField.value)
)
/** What the column picker starts from: the columns shown, when they are fields. */
const pickerStart = computed(() => userColumns.value ?? selectedEventSource.value?.displayed_columns ?? [])

function tableColumn(column: EventColumn): DataTableColumn<EventSearchResult> {
	const value = (row: EventSearchResult) => columnValue(column, row, timeField.value)
	if (column.key === "Level" && column.field === null) {
		return {
			title: column.label,
			key: column.key,
			width: column.width ?? undefined,
			render: row => <Chip type={levelClass(eventLevel(row))} value={eventLevel(row) ?? "-"} round />
		}
	}
	return {
		title: column.label,
		key: column.key,
		width: column.width ?? undefined,
		fixed: column.field === null && column.key === "Timestamp" && !simpleMode.value ? "left" : undefined,
		ellipsis: column.field === null ? undefined : { tooltip: true },
		sorter: column.time
			? (a, b) => {
					const timeA = parseEventTime(value(a))
					const timeB = parseEventTime(value(b))
					if (Number.isNaN(timeA) && Number.isNaN(timeB)) return 0
					if (Number.isNaN(timeA)) return -1
					if (Number.isNaN(timeB)) return 1
					return timeA - timeB
				}
			: undefined,
		render: row => {
			const raw = value(row)
			if (column.time && present(raw)) return <div class="font-mono">{formatEventTime(raw)}</div>
			return <div>{present(raw) ? cellText(raw) : "-"}</div>
		}
	}
}

const actionsColumn = computed<DataTableColumn<EventSearchResult>>(() => ({
	title: "Actions",
	key: "actions",
	width: 150,
	fixed: simpleMode.value ? undefined : "right",
	render: row => (
		<NButton
			onClick={() => selectEvent(row)}
			v-slots={{
				icon: () => <Icon name="carbon:view" />
			}}
		>
			View Details
		</NButton>
	)
}))

// Always keep the View Details action at the right edge — it's the only way to open the
// event drawer from the table.
const columns = computed<DataTableColumns<EventSearchResult>>(() => [
	...eventColumns.value.map(tableColumn),
	actionsColumn.value
])

const savingColumns = ref(false)

/** Keeps the picked columns on the server; the dialog stays open if they could not be kept. */
async function applyColumns(picked: DisplayColumn[] | null) {
	const source = selectedEventSource.value?.name
	if (!source) return
	savingColumns.value = true
	try {
		await memory.setColumns(source, picked)
		showColumns.value = false
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to save the columns")
	} finally {
		savingColumns.value = false
	}
}

/** The loaded events, in the columns on screen. */
function exportCsv() {
	const source = selectedEventSource.value?.name ?? "events"
	const { headers, rows } = eventsToCsv(eventColumns.value, events.value, timeField.value)
	downloadCsv(eventsFilename(source), headers, rows)
	const more = totalEvents.value - events.value.length
	message.success(
		more > 0
			? `Exported ${events.value.length.toLocaleString()} of ${totalEvents.value.toLocaleString()} events: load more to include the rest`
			: `Exported ${events.value.length.toLocaleString()} events`
	)
}

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
