<template>
	<div class="flex flex-col gap-1">
		<div class="flex items-end justify-between gap-3">
			<p class="py-1 text-sm">
				Showing
				<span class="font-semibold">{{ events.length }}</span>
				of
				<span class="font-semibold">{{ totalEvents }}</span>
				events
			</p>

			<div class="flex flex-wrap items-center gap-3">
				<n-button
					text
					:disabled="!eventSource"
					title="Configure which columns to display for this event source"
					@click="emit('configure-columns')"
				>
					<template #icon>
						<Icon :name="SettingsIcon" :size="15" />
					</template>
					Columns
				</n-button>
			</div>
		</div>

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
import { NButton, NDataTable, NEmpty } from "naive-ui"
import { computed, h } from "vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import ExpandableText from "@/components/common/ExpandableText.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	events: EventSearchResult[]
	totalEvents: number
	loadingEvents: boolean
	loadingMore: boolean
	hasSearched: boolean
	scrollId: string | null
	eventSource: EventSource | null
	customerCode: string | null
	sourceName: string | null
}>()

const emit = defineEmits<{
	"load-more": []
	"configure-columns": []
	"row-select": [event: EventSearchResult]
}>()

const MIN_COLUMN_WIDTH = 120
const SettingsIcon = "carbon:settings"

const { routeEventSearchEvent } = useNavigation()
const dFormats = useSettingsStore().dateFormat

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

const defaultColumns: DataTableColumns<EventSearchResult> = [
	{
		title: "Timestamp",
		key: "timestamp",
		width: 180,
		sorter: (a, b) => {
			const timeA = String(a.timestamp || a["@timestamp"] || "")
			const timeB = String(b.timestamp || b["@timestamp"] || "")
			return new Date(timeA).getTime() - new Date(timeB).getTime()
		},
		render(row) {
			const ts = row.timestamp || row["@timestamp"]
			if (!ts) return "-"
			return `${formatDate(`${ts}`, dFormats.datetime)}`
		}
	},
	{
		title: "Source",
		key: "agent_name",
		width: 140,
		ellipsis: { tooltip: true },
		render(row) {
			return formatCellValue(row.agent_name || row.source)
		}
	},
	{
		title: "Rule",
		key: "rule_description",
		width: 200,
		ellipsis: { tooltip: true },
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
	return {
		title: col.label || col.key,
		key: col.key,
		width: resolveColumnWidth(col.width),
		ellipsis: { tooltip: true },
		render(row: EventSearchResult) {
			return formatCellValue(getNestedValue(row, col.key))
		}
	}
}

const columns = computed<DataTableColumns<EventSearchResult>>(() => {
	const configured = props.eventSource?.displayed_columns
	const dataColumns =
		configured && configured.length > 0
			? normalizeColumns(configured.map(buildColumnFromConfig))
			: normalizeColumns(defaultColumns)

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

function eventDetailRoute(row: EventSearchResult): EntityRoute | undefined {
	if (!row._id || !row._index || !props.customerCode || !props.sourceName) return undefined
	return routeEventSearchEvent(props.customerCode, props.sourceName, String(row._index), String(row._id))
}

const scrollX = computed(() =>
	columns.value.reduce(
		(sum, col) => sum + resolveColumnWidth(typeof col.width === "number" ? col.width : undefined),
		0
	)
)
</script>
