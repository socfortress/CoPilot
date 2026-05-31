<template>
	<div class="flex flex-col gap-6">
		<!-- Active columns -->
		<section class="flex min-w-0 flex-col gap-3">
			<div class="flex items-start justify-between gap-3">
				<div>
					<p class="text-secondary text-[10px] font-medium tracking-widest uppercase">Active columns</p>
					<p class="text-secondary mt-1 text-xs">Order matches table left-to-right</p>
				</div>
				<span class="text-default shrink-0 font-mono text-xs tabular-nums">{{ localColumns.length }}</span>
			</div>

			<n-empty
				v-if="!localColumns.length"
				size="small"
				description="No custom columns"
				class="border-border rounded-lg border border-dashed py-6"
			>
				<template #extra>
					<p class="text-secondary max-w-56 text-center text-xs">
						Default table columns will be shown until you add fields below.
					</p>
				</template>
			</n-empty>

			<div v-else class="flex flex-col gap-1.5">
				<div
					v-for="(col, idx) in localColumns"
					:key="col.key"
					class="bg-default hover:bg-hover-005 group flex items-center gap-2 rounded-md py-2 transition-colors"
				>
					<span class="text-secondary w-5 shrink-0 text-center font-mono text-[10px] tabular-nums">
						{{ idx + 1 }}
					</span>
					<n-input v-model:value="col.label" size="small" placeholder="Header label" />
					<span class="text-secondary min-w-0 flex-1 truncate font-mono text-xs" :title="col.key">
						{{ col.key }}
					</span>
					<div class="flex shrink-0 gap-0.5 opacity-60 transition-opacity group-hover:opacity-100">
						<n-button
							size="tiny"
							quaternary
							:disabled="idx === 0"
							title="Move up"
							@click="moveColumn(idx, -1)"
						>
							<template #icon>
								<Icon :name="ArrowUpIcon" :size="14" />
							</template>
						</n-button>
						<n-button
							size="tiny"
							quaternary
							:disabled="idx === localColumns.length - 1"
							title="Move down"
							@click="moveColumn(idx, 1)"
						>
							<template #icon>
								<Icon :name="ArrowDownIcon" :size="14" />
							</template>
						</n-button>
						<n-button size="tiny" quaternary type="error" title="Remove column" @click="removeColumn(idx)">
							<template #icon>
								<Icon :name="CloseIcon" :size="14" />
							</template>
						</n-button>
					</div>
				</div>
			</div>
		</section>

		<!-- Add column from available fields -->
		<section class="flex min-w-0 flex-col gap-3">
			<div>
				<p class="text-secondary text-[10px] font-medium tracking-widest uppercase">Add column</p>
				<p class="text-secondary mt-1 text-xs">Pick a mapped field not already in the table</p>
			</div>

			<n-input v-model:value="fieldFilter" placeholder="Filter fields…" clearable size="small">
				<template #prefix>
					<Icon :name="SearchIcon" :size="14" class="text-secondary" />
				</template>
			</n-input>

			<n-card embedded content-class="p-0!">
				<n-scrollbar
					v-if="filteredFields.length"
					class="max-h-72"
					trigger="none"
					content-class="flex flex-col gap-0 py-2"
				>
					<n-button
						v-for="field in filteredFields"
						:key="field.field"
						quaternary
						class="[&_.n-button\_\_content]:w-full"
						@click="addColumn(field.field)"
					>
						<div class="flex w-full items-center justify-between gap-3">
							<span class="text-default min-w-0 truncate font-mono text-xs">{{ field.field }}</span>
							<span class="text-secondary shrink-0 text-[10px] tracking-wider uppercase">
								{{ field.type }}
							</span>
						</div>
					</n-button>
				</n-scrollbar>

				<div v-else class="text-secondary px-3 py-6 text-center text-xs">
					{{ emptyFieldsMessage }}
				</div>
			</n-card>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { FieldMapping } from "@/types/events.d"
import type { DisplayColumn, EventSource } from "@/types/eventSources.d"
import { NButton, NCard, NEmpty, NInput, NScrollbar, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	open: boolean
	eventSource: EventSource | null
	fieldMappings: FieldMapping[]
	loadingFieldMappings?: boolean
}>()

const emit = defineEmits<{
	close: []
	saved: [columns: DisplayColumn[] | null]
}>()

const SearchIcon = "carbon:search"
const CloseIcon = "carbon:close"
const ArrowUpIcon = "carbon:arrow-up"
const ArrowDownIcon = "carbon:arrow-down"

const message = useMessage()

const localColumns = ref<DisplayColumn[]>([])
const fieldFilter = ref("")
const saving = ref(false)

watch(
	() => [props.open, props.eventSource?.id] as const,
	([open]) => {
		if (open && props.eventSource) {
			localColumns.value = (props.eventSource.displayed_columns ?? []).map(c => ({
				key: c.key,
				label: c.label,
				width: c.width ?? null
			}))
			fieldFilter.value = ""
		}
	},
	{ immediate: true }
)

const usedKeys = computed(() => new Set(localColumns.value.map(c => c.key)))

const filteredFields = computed(() => {
	const q = fieldFilter.value.trim().toLowerCase()
	const all = props.fieldMappings.filter(f => !usedKeys.value.has(f.field))
	if (!q) return all
	return all.filter(f => f.field.toLowerCase().includes(q))
})

const emptyFieldsMessage = computed(() => {
	if (props.loadingFieldMappings) return "Loading available fields…"
	if (!props.fieldMappings.length) return "No field mappings available for this source."
	if (fieldFilter.value.trim()) return "No fields match your filter."
	return "All mapped fields are already in the table."
})

function defaultLabelFor(fieldPath: string): string {
	const tail = fieldPath.split(".").pop() ?? fieldPath
	return tail.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())
}

function addColumn(fieldPath: string) {
	if (usedKeys.value.has(fieldPath)) return
	localColumns.value.push({
		key: fieldPath,
		label: defaultLabelFor(fieldPath),
		width: null
	})
}

function removeColumn(idx: number) {
	localColumns.value.splice(idx, 1)
}

function moveColumn(idx: number, delta: number) {
	const target = idx + delta
	if (target < 0 || target >= localColumns.value.length) return
	const [item] = localColumns.value.splice(idx, 1)
	localColumns.value.splice(target, 0, item)
}

function resetToDefaults() {
	localColumns.value = []
}

function onSave() {
	if (!props.eventSource) return
	saving.value = true

	const payload = localColumns.value.length ? localColumns.value : null

	Api.siem
		.updateEventSource(props.eventSource.id, { displayed_columns: payload })
		.then(res => {
			if (res.data.success) {
				message.success("Columns saved")
				emit("saved", payload)
				emit("close")
			} else {
				message.warning(res.data?.message || "Failed to save columns")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "Failed to save columns")
		})
		.finally(() => {
			saving.value = false
		})
}

defineExpose({
	saving,
	resetToDefaults,
	onSave
})
</script>
