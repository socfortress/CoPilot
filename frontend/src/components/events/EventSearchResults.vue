<template>
	<n-spin :show="loadingEvents">
		<n-card v-if="events.length || loadingEvents" size="small">
			<div class="flex justify-between gap-3">
				<div class="mb-2 flex items-center justify-between">
					<span class="text-sm opacity-60">
						{{ totalEvents }} event{{ totalEvents !== 1 ? "s" : "" }} found
					</span>
				</div>

				<n-button
					quaternary
					:disabled="!eventSource"
					title="Configure which columns to display for this event source"
					@click="emit('configure-columns')"
				>
					<template #icon>
						<Icon :name="SettingsIcon" :size="16" />
					</template>
					Columns
				</n-button>
			</div>
			<n-data-table
				:columns
				:data="events"
				:bordered="false"
				:single-line="false"
				size="small"
				:row-key="(row: EventSearchResult) => row._id || JSON.stringify(row)"
				:row-props
				max-height="calc(100vh - 360px)"
				virtual-scroll
			/>
			<div v-if="scrollId && events.length < totalEvents" class="mt-3 flex justify-center">
				<n-button :loading="loadingMore" @click="emit('load-more')">Load More</n-button>
			</div>
		</n-card>
		<n-empty
			v-else-if="!loadingEvents && hasSearched"
			description="No events found"
			class="h-48 justify-center"
		/>
	</n-spin>
</template>

<script setup lang="ts">
import type { DataTableColumns } from "naive-ui"
import type { EventSearchResult } from "@/types/events.d"
import type { DisplayColumn, EventSource } from "@/types/eventSources.d"
import { NButton, NCard, NDataTable, NEmpty, NSpin } from "naive-ui"
import { computed, h } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	events: EventSearchResult[]
	totalEvents: number
	loadingEvents: boolean
	loadingMore: boolean
	hasSearched: boolean
	scrollId: string | null
	eventSource: EventSource | null
}>()

const emit = defineEmits<{
	"load-more": []
	"configure-columns": []
	"row-select": [event: EventSearchResult]
}>()

const SettingsIcon = "carbon:settings"

const defaultColumns: DataTableColumns<EventSearchResult> = [
	{
		title: "Timestamp",
		key: "timestamp",
		width: 180,
		sorter: (a, b) => {
			const timeA = a.timestamp || a["@timestamp"] || ""
			const timeB = b.timestamp || b["@timestamp"] || ""
			return new Date(timeA).getTime() - new Date(timeB).getTime()
		},
		render(row) {
			const ts = row.timestamp || row["@timestamp"]
			if (!ts) return "-"
			return new Date(ts).toLocaleString()
		}
	},
	{
		title: "Source",
		key: "agent_name",
		width: 140,
		ellipsis: { tooltip: true },
		render(row) {
			return row.agent_name || row.source || "-"
		}
	},
	{
		title: "Rule",
		key: "rule_description",
		ellipsis: { tooltip: true },
		render(row) {
			return row.rule_description || row.rule_id || "-"
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
		ellipsis: { tooltip: true },
		render(row) {
			return row.full_log || row.data || row.message || "-"
		}
	}
]

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

function buildColumnFromConfig(col: DisplayColumn): DataTableColumns<EventSearchResult>[number] {
	return {
		title: col.label || col.key,
		key: col.key,
		width: col.width || undefined,
		ellipsis: { tooltip: true },
		render(row: EventSearchResult) {
			return formatCellValue(getNestedValue(row, col.key))
		}
	}
}

const columns = computed<DataTableColumns<EventSearchResult>>(() => {
	const configured = props.eventSource?.displayed_columns
	if (configured && configured.length > 0) {
		return configured.map(buildColumnFromConfig)
	}
	return defaultColumns
})

function rowProps(row: EventSearchResult) {
	return {
		style: "cursor: pointer",
		onClick: () => {
			emit("row-select", row)
		}
	}
}
</script>

<style scoped>
.level-error {
	color: var(--error-color, #e88080);
	font-weight: 600;
}

.level-warning {
	color: var(--warning-color, #f0a020);
	font-weight: 600;
}

.level-info {
	color: var(--info-color, #70c0e8);
}
</style>
