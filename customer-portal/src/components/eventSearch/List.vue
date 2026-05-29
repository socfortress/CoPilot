<template>
	<div class="flex flex-col gap-6">
		<SearchForm v-model:query="query" :loading-events="loading" @search="handleSearchFormSearch" @loaded="handleSearchFormLoaded" />

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
import type { DataTableColumn, DataTableColumns, TagProps } from "naive-ui"
import type { SearchFormLoad, SearchFormParams } from "@/components/eventSearch/SearchForm.vue"
import type { ApiError } from "@/types/common"
import type { DisplayColumn, EventSearchQueryParams, EventSearchResult, EventSourceItem } from "@/types/siem"
import { useElementSize } from "@vueuse/core"
import { NButton, NDataTable, NEmpty, useMessage } from "naive-ui"
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

const selectedEventSource = computed<EventSourceItem | null>(() => {
	const sourceName = searchFormParams.value?.sourceName
	const sources = searchFormLoad.value?.eventSources
	if (!sourceName || !sources) return null
	return sources.find(s => s.name === sourceName) ?? null
})

/** Walk a dotted path (e.g. "agent.name") through a nested object. */
function getNestedValue(obj: EventSearchResult, path: string): unknown {
	return path.split(".").reduce<unknown>((acc, segment) => {
		if (acc && typeof acc === "object") {
			return (acc as Record<string, unknown>)[segment]
		}
		return undefined
	}, obj)
}

function formatCellValue(val: unknown): string {
	if (val === undefined || val === null || val === "") return "-"
	if (Array.isArray(val)) return val.map(v => (v === null || v === undefined ? "" : String(v))).join(", ")
	if (typeof val === "object") return JSON.stringify(val)
	return String(val)
}

function buildColumnFromConfig(col: DisplayColumn): DataTableColumn<EventSearchResult> {
	return {
		title: col.label || col.key,
		key: col.key,
		width: col.width || undefined,
		ellipsis: { tooltip: true },
		render: row => <div>{formatCellValue(getNestedValue(row, col.key))}</div>
	}
}

// Defaults preserved from the original hardcoded layout so behaviour is unchanged
// for event sources that haven't been configured yet.
const defaultColumns = computed<DataTableColumn<EventSearchResult>[]>(() => [
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
	}
])

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

const columns = computed<DataTableColumns<EventSearchResult>>(() => {
	const configured = selectedEventSource.value?.displayed_columns
	const dataColumns =
		configured && configured.length > 0 ? configured.map(buildColumnFromConfig) : defaultColumns.value
	// Always keep the View Details action at the right edge — it's the only way
	// to open the event drawer from the table.
	return [...dataColumns, actionsColumn.value]
})

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
