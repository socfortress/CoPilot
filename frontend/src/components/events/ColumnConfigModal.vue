<template>
	<n-modal
		v-model:show="showModel"
		preset="card"
		:title="`Configure columns: ${eventSource?.name ?? ''}`"
		style="width: 720px; max-width: 92vw"
		:bordered="false"
		:mask-closable="false"
	>
		<div class="flex flex-col gap-4">
			<!-- Active columns -->
			<div class="flex flex-col gap-2">
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium">Active columns ({{ localColumns.length }})</span>
					<span class="text-xs opacity-60">Order matches table left-to-right</span>
				</div>

				<div
					v-if="!localColumns.length"
					class="rounded border border-dashed p-4 text-center text-sm opacity-60"
				>
					No columns configured. Defaults from the table will be shown.
				</div>

				<div v-else class="flex flex-col gap-1">
					<div
						v-for="(col, idx) in localColumns"
						:key="col.key"
						class="bg-default flex items-center gap-2 rounded border px-2 py-1.5"
					>
						<span class="text-xs opacity-50" style="width: 24px">{{ idx + 1 }}</span>
						<n-input
							v-model:value="col.label"
							size="small"
							placeholder="Column header"
							style="flex: 1; max-width: 200px"
						/>
						<span
							class="font-mono text-xs opacity-60"
							style="
								flex: 1;
								min-width: 0;
								overflow: hidden;
								text-overflow: ellipsis;
								white-space: nowrap;
							"
						>
							{{ col.key }}
						</span>
						<n-button size="tiny" :disabled="idx === 0" @click="moveColumn(idx, -1)">
							<template #icon>
								<Icon :name="ArrowUpIcon" :size="14" />
							</template>
						</n-button>
						<n-button size="tiny" :disabled="idx === localColumns.length - 1" @click="moveColumn(idx, 1)">
							<template #icon>
								<Icon :name="ArrowDownIcon" :size="14" />
							</template>
						</n-button>
						<n-button size="tiny" type="error" quaternary @click="removeColumn(idx)">
							<template #icon>
								<Icon :name="CloseIcon" :size="14" />
							</template>
						</n-button>
					</div>
				</div>
			</div>

			<!-- Add column from available fields -->
			<div class="flex flex-col gap-2">
				<span class="text-sm font-medium">Add a column</span>
				<n-input v-model:value="fieldFilter" placeholder="Filter available fields..." clearable size="small">
					<template #prefix>
						<Icon :name="SearchIcon" :size="14" class="opacity-50" />
					</template>
				</n-input>
				<div class="max-h-60 overflow-y-auto rounded border">
					<div
						v-for="field in filteredFields"
						:key="field.field"
						class="hover:bg-hover-005 flex cursor-pointer items-center justify-between gap-2 px-2 py-1.5 text-sm"
						@click="addColumn(field.field)"
					>
						<span class="font-mono">{{ field.field }}</span>
						<span class="flex items-center gap-2">
							<span class="text-xs opacity-50">{{ field.type }}</span>
							<n-button size="tiny" quaternary>
								<template #icon>
									<Icon :name="AddIcon" :size="14" />
								</template>
							</n-button>
						</span>
					</div>
					<div v-if="!filteredFields.length" class="p-3 text-center text-sm opacity-60">
						{{ fieldMappings.length ? "No fields match your filter." : "Loading available fields..." }}
					</div>
				</div>
			</div>
		</div>

		<template #footer>
			<div class="flex items-center justify-between gap-2">
				<n-button quaternary type="warning" @click="resetToDefaults">Reset to defaults</n-button>
				<div class="flex gap-2">
					<n-button @click="showModel = false">Cancel</n-button>
					<n-button type="primary" :loading="saving" @click="onSave">Save</n-button>
				</div>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { FieldMapping } from "@/types/events.d"
import type { DisplayColumn, EventSource } from "@/types/eventSources.d"
import { NButton, NInput, NModal, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	show: boolean
	eventSource: EventSource | null
	fieldMappings: FieldMapping[]
}>()

const emit = defineEmits<{
	"update:show": [value: boolean]
	saved: [columns: DisplayColumn[] | null]
}>()

const SearchIcon = "carbon:search"
const AddIcon = "carbon:add"
const CloseIcon = "carbon:close"
const ArrowUpIcon = "carbon:arrow-up"
const ArrowDownIcon = "carbon:arrow-down"

const message = useMessage()

const showModel = computed({
	get: () => props.show,
	set: v => emit("update:show", v)
})

const localColumns = ref<DisplayColumn[]>([])
const fieldFilter = ref("")
const saving = ref(false)

// Re-seed when the modal opens or the source changes
watch(
	() => [props.show, props.eventSource?.id] as const,
	([show]) => {
		if (show && props.eventSource) {
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
	if (!q) return all.slice(0, 50)
	return all.filter(f => f.field.toLowerCase().includes(q)).slice(0, 50)
})

function defaultLabelFor(fieldPath: string): string {
	// Take the last dotted segment, replace _ with spaces, title-case
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

	// Empty list means "use defaults" — send null so the backend stores NULL.
	const payload = localColumns.value.length ? localColumns.value : null

	Api.siem
		.updateEventSource(props.eventSource.id, { displayed_columns: payload })
		.then(res => {
			if (res.data.success) {
				message.success("Columns saved")
				emit("saved", payload)
				showModel.value = false
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
</script>
