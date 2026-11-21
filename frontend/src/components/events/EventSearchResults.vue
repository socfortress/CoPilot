<template>
	<div class="flex flex-col gap-1">
		<div class="flex items-end justify-between gap-3">
			<p class="py-1 text-sm">
				Showing
				<span class="font-semibold">{{ events.length }}</span>
				of
				<span class="font-semibold">{{ totalEvents }}</span>
				events
				<template v-if="multiSource">
					from
					<span class="font-semibold">{{ eventSources.length }}</span>
					sources
				</template>
			</p>

			<div class="flex flex-wrap items-center gap-3">
				<n-button
					text
					:disabled="!singleSource"
					:title="
						multiSource
							? 'Columns are set per event source: search one source to change its columns'
							: 'Configure which columns to display for this event source'
					"
					@click="emit('configure-columns')"
				>
					<template #icon>
						<Icon :name="SettingsIcon" :size="15" />
					</template>
					Columns
				</n-button>
			</div>
		</div>

		<n-alert v-if="warnings.length" type="warning" :bordered="false" class="mb-2 text-sm">
			<p v-for="warning of warnings" :key="warning">{{ warning }}</p>
		</n-alert>

		<n-data-table
			:columns
			:loading="loadingEvents"
			:data="events"
			size="small"
			:scroll-x
			:row-key="(row: EventSearchResult) => String(row._id ?? JSON.stringify(row))"
			class="[&_.n-data-table-th\_\_title]:whitespace-nowrap"
		>
			<template #empty>
				<n-empty description="No events found">
					<template #extra>Try adjusting your query or expanding the time range</template>
				</n-empty>
			</template>
		</n-data-table>

		<div v-if="scrollId && events.length < totalEvents" class="mt-3 flex justify-center">
			<n-button :loading="loadingMore" @click="emit('load-more')">Load More</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { DataTableColumns } from "naive-ui"
import type { EntityRoute } from "@/composables/useNavigation"
import type { SafeAny } from "@/types/common"
import type { DisplayColumn, EventSource } from "@/types/event-sources"
import type { EventSearchResult } from "@/types/events"
import { NAlert, NButton, NDataTable, NEmpty, NTag } from "naive-ui"
import { computed, h } from "vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import ExpandableText from "@/components/common/ExpandableText.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"

const props = withDefaults(
	defineProps<{
		events: EventSearchResult[]
		totalEvents: number
		loadingEvents: boolean
		loadingMore: boolean
		hasSearched: boolean
		scrollId: string | null
		/** The sources searched: one, or several searched together. */
		eventSources: EventSource[]
		customerCode: string | null
		/** What the indexer reported about the results, e.g. shards that could not answer. */
		warnings?: string[]
	}>(),
	{ warnings: () => [] }
)

const emit = defineEmits<{
	"load-more": []
	"configure-columns": []
	"row-select": [event: EventSearchResult]
}>()

const MIN_COLUMN_WIDTH = 120
const SettingsIcon = "carbon:settings"

const { routeEventSearchEvent } = useNavigation()
const dFormats = useSettingsStore().dateFormat

const singleSource = computed(() => (props.eventSources.length === 1 ? props.eventSources[0] : null))
const multiSource = computed(() => props.eventSources.length > 1)

/** The time field of the search; sources searched together share one (the backend refuses others). */
const timeField = computed(() => props.eventSources[0]?.time_field)

function resolveColumnWidth(width?: number | null): number {
	if (width == null || width < MIN_COLUMN_WIDTH) return MIN_COLUMN_WIDTH
	return width
}

function normalizeColumns(cols: DataTableColumns<EventSearchResult>): DataTableColumns<EventSearchResult> {
	return cols.map(col => ({
		...col,
		width: resolveColumnWidth(typeof col.width === "number" ? col.width : undefined)
	}))
}

/** Source `time_field`, or any key whose name contains `timestamp` (case-insensitive). */
function isTimeField(key: string): boolean {
	return key === timeField.value || key.toLowerCase().includes("timestamp")
}

function getEventTime(row: EventSearchResult): SafeAny | undefined {
	const preferred = timeField.value
	const keys = [
		...(preferred ? [preferred] : []),
		...Object.keys(row).filter(k => k !== preferred && k.toLowerCase().includes("timestamp"))
	]
	for (const key of keys) {
		const value = getNestedValue(row, key)
		if (value !== undefined && value !== null && value !== "") return value
	}
	return undefined
}

/**
 * Renders an event time in the viewer's local timezone. `tz: true` is what makes offset-less
 * timestamps — which several sources emit — be read as UTC instead of as local time; without it
 * they render as the raw UTC clock and appear shifted by the viewer's offset.
 */
function formatEventTime(value: SafeAny): string {
	return String(formatDate(typeof value === "number" ? value : `${value}`, dFormats.datetime, { tz: true }))
}

/** Parses on the same UTC assumption as `formatEventTime`, so sorting matches what is displayed. */
function parseEventTime(value: SafeAny | undefined): number {
	if (value === undefined || value === null || value === "") return Number.NaN
	const parsed = typeof value === "number" ? dayjs(value) : dayjs.utc(`${value}`)
	return parsed.isValid() ? parsed.valueOf() : Number.NaN
}

function buildDefaultColumns(): DataTableColumns<EventSearchResult> {
	return [
		{
			title: "Timestamp",
			key: "timestamp",
			width: 180,
			sorter: (a, b) => {
				const timeA = parseEventTime(getEventTime(a))
				const timeB = parseEventTime(getEventTime(b))
				if (Number.isNaN(timeA) && Number.isNaN(timeB)) return 0
				if (Number.isNaN(timeA)) return -1
				if (Number.isNaN(timeB)) return 1
				return timeA - timeB
			},
			render(row) {
				const ts = getEventTime(row)
				if (ts === undefined) return "-"
				return formatEventTime(ts)
			}
		},
		{
			// The agent's name, else the syslog sender: the host. Not "Source", which reads like the event source.
			title: "Host",
			key: "agent_name",
			width: 140,
			ellipsis: { tooltip: { to: "body", contentClass: "max-w-[70vw] text-sm!" } },
			render(row) {
				return formatCellValue(row.agent_name || row.source)
			}
		},
		{
			title: "Rule",
			key: "rule_description",
			width: 200,
			ellipsis: { tooltip: { to: "body", contentClass: "max-w-[70vw] text-sm!" } },
			render(row) {
				return formatCellValue(row.rule_description || row.rule_id)
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
			width: 320,
			render(row) {
				return h(ExpandableText, {
					text: formatCellValue(row.full_log || row.data || row.message),
					maxLength: 100
				})
			}
		}
	]
}

function getNestedValue(obj: EventSearchResult, path: string): SafeAny | undefined {
	return path.split(".").reduce<SafeAny | undefined>((acc, segment) => {
		if (acc != null && typeof acc === "object") {
			return (acc as Record<string, SafeAny>)[segment]
		}
		return undefined
	}, obj)
}

function formatCellValue(val: SafeAny | undefined): string {
	if (val === undefined || val === null || val === "") return "-"
	if (Array.isArray(val)) return val.map(v => (v === null || v === undefined ? "" : String(v))).join(", ")
	if (typeof val === "object") return JSON.stringify(val)
	return String(val)
}

function buildColumnFromConfig(col: DisplayColumn): DataTableColumns<EventSearchResult>[number] {
	// A configured column pointing at the source's time field gets the same local-timezone
	// treatment as the default Timestamp column, instead of being dumped as a raw UTC string.
	const timeColumn = isTimeField(col.key)

	return {
		title: col.label || col.key,
		key: col.key,
		width: resolveColumnWidth(col.width),
		ellipsis: { tooltip: { to: "body", contentClass: "max-w-[70vw] text-sm!" } },
		render(row: EventSearchResult) {
			const value = getNestedValue(row, col.key)
			if (timeColumn && value !== undefined && value !== null && value !== "") {
				return formatEventTime(value)
			}
			return formatCellValue(value)
		}
	}
}

/** One source's columns: the ones configured for it, else the default layout. */
function sourceColumns(source: EventSource | null): DataTableColumns<EventSearchResult> {
	const configured = source?.displayed_columns
	return configured && configured.length > 0 ? configured.map(buildColumnFromConfig) : buildDefaultColumns()
}

function eventSourceColumn(): DataTableColumns<EventSearchResult>[number] {
	return {
		title: "Event source",
		key: "_source_name",
		width: 160,
		render(row) {
			const name = row._source_name
			if (!name) return "-"
			return h(NTag, { size: "small", bordered: false, title: name, class: "max-w-full" }, () =>
				h("span", { class: "block truncate" }, name))
		}
	}
}

/**
 * Several sources: the time of each event, the source it came from, then every searched
 * source's own columns together, each key once (the first source to name it gives its label).
 * A source's column on its time field is left out: the first column already shows it.
 */
function multiSourceColumns(): DataTableColumns<EventSearchResult> {
	const [timestamp, ...defaults] = buildDefaultColumns()
	const seen = new Set<string>(["timestamp", "_source_name", ...(timeField.value ? [timeField.value] : [])])
	const merged: DataTableColumns<EventSearchResult> = []

	for (const source of props.eventSources) {
		const columns = source.displayed_columns?.length ? source.displayed_columns.map(buildColumnFromConfig) : defaults
		for (const column of columns) {
			const key = "key" in column ? String(column.key) : ""
			if (!key || seen.has(key)) continue
			seen.add(key)
			merged.push(column)
		}
	}

	return [timestamp, eventSourceColumn(), ...merged]
}

const columns = computed<DataTableColumns<EventSearchResult>>(() => {
	const dataColumns = normalizeColumns(multiSource.value ? multiSourceColumns() : sourceColumns(singleSource.value))

	return [
		...dataColumns,
		{
			title: "",
			key: "actions",
			width: 100,
			fixed: "right",
			render(row: EventSearchResult) {
				const eventRoute = eventDetailRoute(row)
				if (!eventRoute) {
					return h("span", { class: "text-tertiary text-xs" }, "—")
				}

				return h(
					"div",
					{ onClick: (e: Event) => e.stopPropagation() },
					h(EntityDetailsButton, {
						size: "tiny",
						route: eventRoute,
						onView: () => emit("row-select", row)
					})
				)
			}
		}
	]
})

/** The event's own page, under the source it came from (each row's own when several were searched). */
function eventDetailRoute(row: EventSearchResult): EntityRoute | undefined {
	const sourceName = multiSource.value ? row._source_name : singleSource.value?.name
	if (!row._id || !row._index || !props.customerCode || !sourceName) return undefined
	return routeEventSearchEvent(props.customerCode, sourceName, String(row._index), String(row._id))
}

const scrollX = computed(() =>
	columns.value.reduce(
		(sum, col) => sum + resolveColumnWidth(typeof col.width === "number" ? col.width : undefined),
		0
	)
)
</script>
