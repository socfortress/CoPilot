<template>
	<n-data-table
		size="small"
		:columns="tableColumns"
		:data="rows || []"
		:pagination="false"
		:bordered="false"
		:max-height="height"
		:scroll-x
		class="[&_.n-data-table-th\_\_title]:whitespace-nowrap"
	>
		<template #empty>
			<n-empty description="No events" />
		</template>
	</n-data-table>
</template>

<script setup lang="ts">
import type { DataTableColumns } from "naive-ui"
import type { PanelResult } from "@/types/dashboards"
import { NDataTable, NEmpty } from "naive-ui"
import { computed } from "vue"

type PanelTableRow = NonNullable<PanelResult["rows"]>[number]

const { columns, rows, height } = defineProps<{
	columns?: string[] | null
	rows?: PanelResult["rows"]
	height?: number
}>()

const MIN_COLUMN_WIDTH = 160

const tableColumns = computed<DataTableColumns<PanelTableRow>>(() =>
	(columns || []).map(key => ({
		title: key,
		key,
		minWidth: MIN_COLUMN_WIDTH,
		ellipsis: { tooltip: true },
		render: (row: PanelTableRow) => {
			const value = row[key]
			return value === null || value === undefined || value === "" ? "—" : String(value)
		}
	}))
)

// Horizontal scroll instead of squeezing columns: table panels usually project
// more fields than fit the panel width.
const scrollX = computed(() => (columns?.length || 0) * MIN_COLUMN_WIDTH)
</script>
