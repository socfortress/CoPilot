<template>
	<div class="flex flex-col gap-5" data-testid="column-picker">
		<section class="flex min-w-0 flex-col gap-2">
			<div class="flex items-baseline justify-between gap-3">
				<span :class="HEAD">Columns shown · left to right</span>
				<span class="text-tertiary font-mono text-xs tabular-nums">{{ columns.length }}</span>
			</div>

			<p v-if="!columns.length" class="border-default text-tertiary m-0 rounded-md border border-dashed px-3 py-4 text-center text-xs">
				No column picked: the table shows {{ sourceColumns?.length ? "the SOC's layout for this source" : "the default layout" }}.
			</p>
			<div v-else class="border-default divide-border @container flex flex-col divide-y overflow-hidden rounded-md border">
				<div
					v-for="(column, index) of columns"
					:key="column.key"
					class="group hover:bg-secondary/50 flex items-center gap-2 px-2 py-1.5"
					data-testid="picked-column"
				>
					<span class="text-tertiary w-5 shrink-0 text-center font-mono text-xs tabular-nums">{{ index + 1 }}</span>
					<!-- The header beside the field it reads; stacked when the dialog is narrow. -->
					<div class="flex min-w-0 grow flex-col gap-1 @md:flex-row @md:items-center @md:gap-3">
						<n-input
							v-model:value="column.label"
							size="small"
							:placeholder="column.key"
							class="shrink-0 @md:w-44!"
							:aria-label="`Header of ${column.key}`"
							data-testid="picked-column-label"
						/>
						<span
							class="text-tertiary min-w-0 truncate font-mono text-xs [font-variant-ligatures:none]"
							:title="column.key"
						>
							{{ column.key }}
						</span>
					</div>
					<div class="flex shrink-0 opacity-60 transition-opacity group-hover:opacity-100">
						<n-button size="tiny" quaternary :disabled="index === 0" aria-label="Move left" @click="move(index, -1)">
							<template #icon><Icon name="carbon:arrow-up" :size="14" /></template>
						</n-button>
						<n-button
							size="tiny"
							quaternary
							:disabled="index === columns.length - 1"
							aria-label="Move right"
							data-testid="picked-column-down"
							@click="move(index, 1)"
						>
							<template #icon><Icon name="carbon:arrow-down" :size="14" /></template>
						</n-button>
						<n-button
							size="tiny"
							quaternary
							type="error"
							:aria-label="`Remove ${column.key}`"
							data-testid="picked-column-remove"
							@click="columns.splice(index, 1)"
						>
							<template #icon><Icon name="carbon:close" :size="14" /></template>
						</n-button>
					</div>
				</div>
			</div>
		</section>

		<section class="flex min-w-0 flex-col gap-2">
			<span :class="HEAD">Add a field</span>
			<n-select
				:value="null"
				:options="addable"
				filterable
				size="small"
				:placeholder="fields.length ? 'Search the source\'s fields' : 'No field list for this source'"
				:disabled="!fields.length"
				data-testid="column-picker-add"
				@update:value="add"
			/>
		</section>

		<footer class="border-default flex flex-wrap items-center justify-between gap-2 border-t pt-4">
			<n-button size="small" quaternary :disabled="!personal" data-testid="column-picker-reset" @click="emit('save', null)">
				<template #icon><Icon name="carbon:reset" /></template>
				Back to {{ sourceColumns?.length ? "the SOC's layout" : "the default" }}
			</n-button>
			<div class="flex gap-2">
				<n-button size="small" @click="emit('cancel')">Cancel</n-button>
				<n-button size="small" type="primary" data-testid="column-picker-save" @click="save">Apply</n-button>
			</div>
		</footer>
	</div>
</template>

<script setup lang="ts">
import type { DisplayColumn, FieldMapping } from "@/types/siem"
import { NButton, NInput, NSelect } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"

/**
 * Picks the columns of event search for one source (#1258): which fields, in which order,
 * under which headers. It starts from what the table shows now; Apply hands the choice to
 * the parent, which keeps it per source, and "Back to…" drops it for the source's layout.
 */

const { current, personal, sourceColumns, fields } = defineProps<{
	/** The columns the table shows now, as fields. */
	current: DisplayColumn[]
	/** Whether `current` is the user's own choice (rather than the source's layout). */
	personal: boolean
	/** The SOC's layout for the source, if any. */
	sourceColumns?: DisplayColumn[] | null
	fields: FieldMapping[]
}>()

const emit = defineEmits<{
	(e: "save", value: DisplayColumn[] | null): void
	(e: "cancel"): void
}>()

const HEAD = "text-tertiary text-xxs font-medium tracking-[0.12em] uppercase"
const columns = ref<DisplayColumn[]>(current.map(c => ({ key: c.key, label: c.label })))

const addable = computed(() => {
	const shown = new Set(columns.value.map(c => c.key))
	return fields.filter(f => !shown.has(f.field)).map(f => ({ label: `${f.field} · ${f.type}`, value: f.field }))
})

function add(field: string | null) {
	if (field) columns.value.push({ key: field, label: field })
}

function move(index: number, step: -1 | 1) {
	const target = index + step
	if (target < 0 || target >= columns.value.length) return
	const [column] = columns.value.splice(index, 1)
	if (column) columns.value.splice(target, 0, column)
}

function save() {
	emit(
		"save",
		columns.value.map(c => ({ key: c.key, label: c.label.trim() || c.key }))
	)
}
</script>
