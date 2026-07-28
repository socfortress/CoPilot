<template>
	<div class="flex flex-col gap-2">
		<div class="flex flex-wrap gap-4">
			<n-form-item label="Title" required class="min-w-60 grow">
				<n-input v-model:value="form.title" placeholder="e.g. Events by Operation" clearable />
			</n-form-item>

			<n-form-item label="Widget type" required class="min-w-48">
				<n-select
					v-model:value="form.type"
					:options="panelTypeOptions"
					to="body"
					:consistent-menu-width="false"
				/>
			</n-form-item>
		</div>

		<n-form-item label="Filter (Lucene)">
			<n-input
				v-model:value="form.lucene"
				placeholder="* — or e.g. rule_level:>=12 AND data_operation:*"
				clearable
			/>
		</n-form-item>

		<n-form-item v-if="needsAggregationField" label="Aggregation field" required>
			<n-select
				v-model:value="form.field"
				:options="fieldOptions"
				:loading="loadingFields"
				placeholder="Select or type a field name"
				filterable
				tag
				clearable
			/>
		</n-form-item>

		<n-form-item v-if="isTable" label="Fields to display" required>
			<n-select
				v-model:value="form.fields"
				:options="fieldOptions"
				:loading="loadingFields"
				placeholder="Select or type the fields to show as columns"
				multiple
				filterable
				tag
				clearable
			/>
		</n-form-item>

		<div class="flex flex-wrap gap-4">
			<n-form-item :label="isTable ? 'Rows' : 'Top values'" class="min-w-32 grow">
				<n-input-number v-model:value="form.size" :min="1" :max="100" :disabled="!usesSize" class="w-full" />
			</n-form-item>

			<n-form-item label="Width (of 12 columns)" class="min-w-40 grow">
				<n-select v-model:value="form.w" :options="widthOptions" />
			</n-form-item>

			<n-form-item label="Height (px)" class="min-w-32 grow">
				<n-input-number v-model:value="form.h" :min="60" :max="1200" :step="20" class="w-full" />
			</n-form-item>
		</div>

		<div class="flex justify-between gap-4">
			<n-button @click="emit('close')">Cancel</n-button>
			<n-button type="primary" :disabled="!isValid" @click="submit()">
				{{ panel ? "Update widget" : "Add widget" }}
			</n-button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { SelectOption } from "naive-ui"
import type { CustomDashboardPanel, DashboardPanelType } from "@/types/dashboards"
import { NButton, NFormItem, NInput, NInputNumber, NSelect } from "naive-ui"
import { computed, reactive, watch } from "vue"

const { panel, fieldOptions, loadingFields } = defineProps<{
	/** Panel being edited; omitted when adding a new one. */
	panel?: CustomDashboardPanel | null
	fieldOptions: SelectOption[]
	loadingFields?: boolean
}>()

const emit = defineEmits<{
	submit: [panel: CustomDashboardPanel]
	close: []
}>()

const panelTypeOptions: { label: string; value: DashboardPanelType }[] = [
	{ label: "Stat — single number", value: "stat" },
	{ label: "Histogram — events over time", value: "histogram" },
	{ label: "Pie — distribution by field", value: "pie" },
	{ label: "Bar — top values by field", value: "bar_h" },
	{ label: "Table — latest events", value: "table" }
]

// Panel heights that read well per type: stats are one line, tables need room.
const DEFAULT_HEIGHT_BY_TYPE: Record<DashboardPanelType, number> = {
	stat: 100,
	histogram: 200,
	pie: 300,
	bar_h: 320,
	table: 400
}

const widthOptions = Array.from({ length: 12 }, (_, i) => ({
	label: `${i + 1} / 12`,
	value: i + 1
}))

const form = reactive<{
	title: string
	type: DashboardPanelType
	lucene: string
	field: string | null
	fields: string[]
	size: number
	w: number
	h: number
}>({
	title: panel?.title || "",
	type: panel?.type || "stat",
	lucene: panel?.lucene || "*",
	field: panel?.field || null,
	fields: panel?.fields || [],
	size: panel?.size || 10,
	w: panel?.w || 4,
	h: panel?.h || DEFAULT_HEIGHT_BY_TYPE[panel?.type || "stat"]
})

// Switching type re-applies that type's default height, unless the user has
// already set a height of their own.
watch(
	() => form.type,
	(type, previousType) => {
		if (form.h === DEFAULT_HEIGHT_BY_TYPE[previousType]) {
			form.h = DEFAULT_HEIGHT_BY_TYPE[type]
		}
	}
)

const needsAggregationField = computed(() => form.type === "pie" || form.type === "bar_h")
const isTable = computed(() => form.type === "table")
const usesSize = computed(() => needsAggregationField.value || isTable.value)

const isValid = computed(() => {
	if (!form.title.trim()) return false
	if (needsAggregationField.value && !form.field) return false
	if (isTable.value && !form.fields.length) return false
	return true
})

function submit() {
	if (!isValid.value) return

	emit("submit", {
		// Keep the id when editing so panel data keeps flowing into the same slot.
		id: panel?.id,
		title: form.title.trim(),
		type: form.type,
		lucene: form.lucene.trim() || "*",
		w: form.w,
		h: form.h,
		...(needsAggregationField.value ? { field: form.field || undefined } : {}),
		...(isTable.value ? { fields: form.fields } : {}),
		...(usesSize.value ? { size: form.size } : {})
	})
}
</script>
