<template>
	<div class="flex flex-col gap-5" data-testid="column-picker">
		<section class="flex min-w-0 flex-col gap-2">
			<div class="flex items-baseline justify-between gap-3">
				<span :class="HEAD">{{ $t("eventSearch.picker.shown") }}</span>
				<span class="text-tertiary font-mono text-xs tabular-nums">{{ columns.length }}</span>
			</div>

			<p
				v-if="!columns.length"
				class="border-default text-tertiary m-0 rounded-md border border-dashed px-3 py-4 text-center text-xs"
			>
				{{ sourceColumns?.length ? $t("eventSearch.picker.noneSoc") : $t("eventSearch.picker.noneDefault") }}
			</p>
			<div
				v-else
				class="border-default divide-border @container flex flex-col divide-y overflow-hidden rounded-md border"
			>
				<div
					v-for="(column, index) of columns"
					:key="column.key"
					class="group hover:bg-secondary/50 flex items-center gap-2 px-2 py-1.5"
					data-testid="picked-column"
				>
					<span class="text-tertiary w-5 shrink-0 text-center font-mono text-xs tabular-nums">
						{{ index + 1 }}
					</span>
					<!-- The header beside the field it reads; stacked when the dialog is narrow. -->
					<div class="flex min-w-0 grow flex-col gap-1 @md:flex-row @md:items-center @md:gap-3">
						<n-input
							v-model:value="column.label"
							size="small"
							:placeholder="column.key"
							class="shrink-0 @md:w-44!"
							:aria-label="$t('eventSearch.picker.headerOf', { field: column.key })"
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
						<n-button
							size="tiny"
							quaternary
							:disabled="index === 0"
							:aria-label="$t('eventSearch.picker.moveLeft')"
							@click="move(index, -1)"
						>
							<template #icon><Icon name="carbon:arrow-up" :size="14" /></template>
						</n-button>
						<n-button
							size="tiny"
							quaternary
							:disabled="index === columns.length - 1"
							:aria-label="$t('eventSearch.picker.moveRight')"
							data-testid="picked-column-down"
							@click="move(index, 1)"
						>
							<template #icon><Icon name="carbon:arrow-down" :size="14" /></template>
						</n-button>
						<n-button
							size="tiny"
							quaternary
							type="error"
							:aria-label="$t('eventSearch.picker.remove', { field: column.key })"
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
			<span :class="HEAD">{{ $t("eventSearch.picker.addField") }}</span>
			<n-select
				:value="null"
				:options="addable"
				filterable
				size="small"
				:placeholder="fields.length ? $t('eventSearch.picker.searchFields') : $t('eventSearch.picker.noFields')"
				:disabled="!fields.length"
				data-testid="column-picker-add"
				@update:value="add"
			/>
		</section>

		<section class="@container flex min-w-0 flex-col gap-2" data-testid="column-templates">
			<div class="flex items-baseline justify-between gap-3">
				<span :class="HEAD">{{ $t("eventSearch.picker.templates") }}</span>
				<span class="text-tertiary font-mono text-xs tabular-nums">{{ templates.length }}</span>
			</div>
			<div
				v-if="templates.length"
				class="border-default divide-border flex max-h-48 flex-col divide-y overflow-y-auto rounded-md border"
			>
				<div
					v-for="template of templates"
					:key="template.id"
					class="group hover:bg-secondary/50 flex min-h-12 min-w-0 items-stretch"
					data-testid="column-template"
				>
					<TemplateDeleteConfirm
						v-if="confirmingId === template.id"
						:name="template.name"
						:loading="savingTemplate"
						@confirm="emit('deleteTemplate', template.id)"
						@cancel="confirmingId = null"
					/>
					<div v-else class="flex min-w-0 grow items-center gap-2 px-2 py-1.5">
						<div class="flex min-w-0 grow flex-col">
							<span class="text-default truncate text-sm">{{ template.name }}</span>
							<span class="text-tertiary truncate text-xs">{{ summary(template.columns) }}</span>
						</div>
						<n-button
							size="tiny"
							secondary
							:title="$t('eventSearch.picker.loadTitle', { name: template.name })"
							data-testid="column-template-load"
							@click="load(template)"
						>
							{{ $t("eventSearch.picker.load") }}
						</n-button>
						<n-button
							size="tiny"
							quaternary
							type="error"
							class="opacity-60 group-hover:opacity-100"
							:aria-label="$t('eventSearch.layouts.deleteTemplate', { name: template.name })"
							:disabled="savingTemplate"
							data-testid="column-template-delete"
							@click="confirmingId = template.id"
						>
							<template #icon><Icon name="carbon:trash-can" :size="14" /></template>
						</n-button>
					</div>
				</div>
			</div>
			<form
				class="flex min-w-0 flex-col gap-2 @md:flex-row @md:items-center"
				data-testid="column-template-form"
				@submit.prevent="saveTemplate"
			>
				<n-input
					v-model:value="templateName"
					size="small"
					:placeholder="$t('eventSearch.picker.templateNamePlaceholder')"
					:maxlength="80"
					class="min-w-0 grow"
					data-testid="column-template-name"
				/>
				<n-button
					size="small"
					secondary
					attr-type="submit"
					:disabled="!templateName.trim() || !columns.length"
					:loading="savingTemplate"
					data-testid="column-template-save"
				>
					<template #icon><Icon name="carbon:template" /></template>
					{{ $t("eventSearch.picker.saveTemplate") }}
				</n-button>
			</form>
			<span v-if="willReplace" class="text-warning text-xs">{{ $t("eventSearch.picker.willReplace") }}</span>
		</section>

		<footer class="border-default flex flex-wrap items-center justify-between gap-2 border-t pt-4">
			<n-button
				size="small"
				quaternary
				:disabled="!personal || saving"
				data-testid="column-picker-reset"
				@click="emit('save', null)"
			>
				<template #icon><Icon name="carbon:reset" /></template>
				{{ sourceColumns?.length ? $t("eventSearch.picker.backToSoc") : $t("eventSearch.picker.backToDefault") }}
			</n-button>
			<div class="flex gap-2">
				<n-button size="small" @click="emit('cancel')">{{ $t("common.actions.cancel") }}</n-button>
				<n-button size="small" type="primary" :loading="saving" data-testid="column-picker-save" @click="save">
					{{ $t("common.actions.apply") }}
				</n-button>
			</div>
		</footer>
	</div>
</template>

<script setup lang="ts">
import type { DisplayColumn, EventSearchColumnTemplate, FieldMapping } from "@/types/siem"
import { NButton, NInput, NSelect } from "naive-ui"
import { computed, ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import TemplateDeleteConfirm from "./TemplateDeleteConfirm.vue"

/**
 * Picks the columns of event search for one source (#1258): which fields, in which order,
 * under which headers. It starts from what the table shows now; Apply hands the choice to
 * the parent, which keeps it per source on the server, and "Back to…" drops it for the
 * source's layout. The columns being edited can also be saved as a named template, a
 * template loaded back to start from, and one deleted once confirmed.
 */

const {
	current,
	personal,
	sourceColumns,
	fields,
	templates = [],
	saving = false,
	savingTemplate = false
} = defineProps<{
	/** The columns the table shows now, as fields. */
	current: DisplayColumn[]
	/** Whether `current` is the user's own choice (rather than the source's layout). */
	personal: boolean
	/** The SOC's layout for the source, if any. */
	sourceColumns?: DisplayColumn[] | null
	fields: FieldMapping[]
	/** The user's templates for this source. */
	templates?: EventSearchColumnTemplate[]
	/** The choice is being kept. */
	saving?: boolean
	/** A template is being saved or deleted. */
	savingTemplate?: boolean
}>()

const emit = defineEmits<{
	(e: "save", value: DisplayColumn[] | null): void
	(e: "cancel"): void
	(e: "saveTemplate", name: string, columns: DisplayColumn[]): void
	(e: "deleteTemplate", id: number): void
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

function picked(): DisplayColumn[] {
	return columns.value.map(c => ({ key: c.key, label: c.label.trim() || c.key }))
}

function save() {
	emit("save", picked())
}

const templateName = ref("")
const willReplace = computed(() => {
	const wanted = templateName.value.trim().toLowerCase()
	return !!wanted && templates.some(template => template.name.toLowerCase() === wanted)
})

function summary(list: DisplayColumn[]): string {
	const labels = list.slice(0, 4).map(column => column.label || column.key)
	return list.length > 4 ? `${labels.join(" · ")} · +${list.length - 4}` : labels.join(" · ")
}

function load(template: EventSearchColumnTemplate) {
	columns.value = template.columns.map(c => ({ key: c.key, label: c.label }))
}

function saveTemplate() {
	const name = templateName.value.trim()
	if (!name || !columns.value.length) return
	emit("saveTemplate", name, picked())
}

/** The template whose deletion is being confirmed. */
const confirmingId = ref<number | null>(null)

watch(
	() => templates,
	list => {
		// The name is cleared once the template is saved: the list then holds it.
		const name = templateName.value.trim().toLowerCase()
		if (name && list.some(template => template.name.toLowerCase() === name)) templateName.value = ""
		// A deleted template leaves nothing to confirm.
		if (confirmingId.value !== null && !list.some(template => template.id === confirmingId.value))
			confirmingId.value = null
	}
)
</script>
