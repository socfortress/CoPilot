<template>
	<div class="flex flex-wrap items-center gap-3" data-testid="alerts-filters">
		<n-input
			v-model:value="titleInput"
			data-testid="alerts-filter-title"
			placeholder="Search alert titles"
			clearable
			size="small"
			class="w-64!"
			@keydown.enter="applyTitle"
			@clear="applyTitle"
		>
			<template #prefix>
				<Icon name="carbon:search" :size="14" />
			</template>
		</n-input>

		<!-- Set by a link (the Activity page's), never from the menu: shown as they are, removable. -->
		<div v-for="type of linkTypes" :key="type" class="max-w-full">
			<n-input-group :data-testid="`alerts-filter-${type}`">
				<n-input-group-label size="small">{{ ALERTS_FILTER_LABELS[type] }}</n-input-group-label>
				<n-input-group-label
					size="small"
					class="max-w-80 truncate"
					:title="linkText(type)"
					:data-testid="`alerts-filter-${type}-value`"
				>
					{{ linkText(type) }}
				</n-input-group-label>
				<n-button
					size="small"
					secondary
					:aria-label="`Remove the ${ALERTS_FILTER_LABELS[type].toLowerCase()} filter`"
					:data-testid="`alerts-filter-${type}-remove`"
					@click="removeFilter(type)"
				>
					<template #icon>
						<Icon name="carbon:close" />
					</template>
				</n-button>
			</n-input-group>
		</div>

		<!-- Each group in its own box: an input group alone stretches to the whole row. -->
		<div v-for="type of shownTypes" :key="type" class="max-w-full">
			<n-input-group :data-testid="`alerts-filter-${type}`">
				<n-input-group-label size="small">{{ ALERTS_FILTER_LABELS[type] }}</n-input-group-label>

				<n-select
					v-if="type === 'status'"
					:value="filters.status"
					:options="statusOptions"
					placeholder="Any status"
					size="small"
					class="w-40!"
					:consistent-menu-width="false"
					@update:value="(status: AlertStatus | null) => change('status', { status })"
				/>

				<n-select
					v-else-if="type === 'source'"
					:value="filters.source"
					:options="toOptions(sources, filters.source)"
					:loading="loadingOptions"
					placeholder="Any source"
					filterable
					size="small"
					class="w-44!"
					:consistent-menu-width="false"
					@update:value="(source: string | null) => change('source', { source })"
				/>

				<n-select
					v-else-if="type === 'asset'"
					:value="filters.asset"
					:options="toOptions(assetResults, filters.asset)"
					:loading="searchingAssets"
					placeholder="Search assets"
					filterable
					remote
					size="small"
					class="w-48!"
					:consistent-menu-width="false"
					@search="onAssetSearch"
					@focus="searchAssets(null)"
					@update:value="(asset: string | null) => change('asset', { asset })"
				/>

				<n-select
					v-else-if="type === 'tag'"
					:value="filters.tags"
					:options="toOptions(tags, ...filters.tags)"
					:loading="loadingOptions"
					placeholder="Any of these tags"
					multiple
					filterable
					size="small"
					:max-tag-count="2"
					class="w-64!"
					:consistent-menu-width="false"
					@update:value="(tags: string[]) => change('tag', { tags })"
				/>

				<template v-else-if="type === 'date'">
					<n-date-picker
						:value="filters.from ? dayToTimestamp(filters.from) : null"
						data-testid="alerts-filter-from"
						type="date"
						placeholder="From"
						:format="pickerFormat"
						:is-date-disabled="(ts: number) => !!filters.to && timestampToDay(ts) > filters.to"
						clearable
						size="small"
						class="w-36!"
						@update:value="
							(ts: number | null) => change('date', { from: ts === null ? null : timestampToDay(ts) })
						"
					/>
					<n-date-picker
						:value="filters.to ? dayToTimestamp(filters.to) : null"
						data-testid="alerts-filter-to"
						type="date"
						placeholder="To"
						:format="pickerFormat"
						:is-date-disabled="(ts: number) => !!filters.from && timestampToDay(ts) < filters.from"
						clearable
						size="small"
						class="w-36!"
						@update:value="
							(ts: number | null) => change('date', { to: ts === null ? null : timestampToDay(ts) })
						"
					/>
				</template>

				<n-button
					size="small"
					secondary
					:aria-label="`Remove the ${ALERTS_FILTER_LABELS[type].toLowerCase()} filter`"
					:data-testid="`alerts-filter-${type}-remove`"
					@click="removeFilter(type)"
				>
					<template #icon>
						<Icon name="carbon:close" />
					</template>
				</n-button>
			</n-input-group>
		</div>

		<n-dropdown
			v-if="addableTypes.length"
			trigger="click"
			placement="bottom-start"
			:options="addableTypes.map(type => ({ key: type, label: ALERTS_FILTER_LABELS[type] }))"
			@select="(type: AlertsFilterType) => openFilter(type)"
		>
			<n-button size="small" dashed data-testid="alerts-filter-add">
				<template #icon>
					<Icon name="carbon:add" />
				</template>
				Add filter
			</n-button>
		</n-dropdown>

		<n-button
			v-if="hasFilters(filters)"
			size="small"
			quaternary
			data-testid="alerts-filter-clear"
			@click="clearAll"
		>
			Clear filters
		</n-button>
	</div>
</template>

<script setup lang="ts">
import type { AlertsFilters, AlertsFilterType, AlertsLinkFilterType } from "./alertsFilters"
import type { AlertStatus } from "@/types/alerts"
import type { ApiError } from "@/types/common"
import { refDebounced, useDebounceFn } from "@vueuse/core"
import { NButton, NDatePicker, NDropdown, NInput, NInputGroup, NInputGroupLabel, NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { WORKFLOW_STATUS_LABELS } from "@/utils/workflowStatus"
import {
	activeFilterTypes,
	ALERTS_FILTER_LABELS,
	ALERTS_FILTER_TYPES,
	dayToTimestamp,
	EMPTY_ALERTS_FILTERS,
	hasFilters,
	isLinkFilter,
	openedLabel,
	timestampToDay,
	withoutFilter
} from "./alertsFilters"

/**
 * The alerts list's filter bar (#1245), after the analyst frontend's: a title search that
 * is always there, then one group per filter in use, each with its own remove button, and
 * "Add filter" for the rest. Every change applies at once (typing is debounced); the
 * parent owns the filters, which live in the URL.
 */

const { filters } = defineProps<{ filters: AlertsFilters }>()

const emit = defineEmits<{
	(e: "change", patch: Partial<AlertsFilters>): void
}>()

const message = useMessage()

const statusOptions = Object.entries(WORKFLOW_STATUS_LABELS).map(([value, label]) => ({ value, label }))

// Date-fns tokens for the user's dayjs date format (MM/DD/YYYY → MM/dd/yyyy).
const pickerFormat = computed(() => useSettingsStore().dateFormat.date.replace("DD", "dd").replace("YYYY", "yyyy"))

/** Select options for `values`, plus any selected value the list does not carry (yet). */
function toOptions(values: string[], ...selected: (string | null)[]) {
	const all = [...new Set([...values, ...selected.filter((value): value is string => !!value)])]
	return all.map(value => ({ label: value, value }))
}

// ── title: typed, so debounced ────────────────────────────────────────────

const titleInput = ref<string | null>(filters.title)

// Enter and the clear button apply at once; the debounced copy catching up later finds
// nothing left to change.
function applyTitle() {
	const title = titleInput.value?.trim() || null
	if (title !== filters.title) emit("change", { title })
}

watch(refDebounced(titleInput, 300), applyTitle)

// The URL changed under us (back, a link, "Clear filters"): show what it says.
watch(
	() => filters.title,
	title => {
		if ((titleInput.value?.trim() || null) !== title) titleInput.value = title
	}
)

// ── which groups are shown ────────────────────────────────────────────────
// A filter in use is always shown; one just added from the menu, or just emptied in its
// own control, stays shown, empty, until its remove button.

const opened = ref<AlertsFilterType[]>([])
const shownTypes = computed(() => {
	const active = activeFilterTypes(filters)
	return ALERTS_FILTER_TYPES.filter(type => active.includes(type) || opened.value.includes(type))
})
const addableTypes = computed(() => ALERTS_FILTER_TYPES.filter(type => !shownTypes.value.includes(type)))
const linkTypes = computed(() => activeFilterTypes(filters).filter(isLinkFilter))

function linkText(type: AlertsLinkFilterType): string {
	if (type === "detection") return filters.detection ?? ""
	const datetime = useSettingsStore().dateFormat.datetime
	return openedLabel(filters, iso => String(formatDate(iso, datetime)))
}

function openFilter(type: AlertsFilterType) {
	opened.value = [...opened.value, type]
}

function change(type: AlertsFilterType, patch: Partial<AlertsFilters>) {
	if (!opened.value.includes(type)) openFilter(type)
	emit("change", patch)
}

function removeFilter(type: AlertsFilterType) {
	opened.value = opened.value.filter(item => item !== type)
	if (activeFilterTypes(filters).includes(type)) emit("change", withoutFilter(filters, type))
}

function clearAll() {
	opened.value = []
	titleInput.value = null
	emit("change", EMPTY_ALERTS_FILTERS)
}

// ── options ───────────────────────────────────────────────────────────────

const sources = ref<string[]>([])
const tags = ref<string[]>([])
const loadingOptions = ref(false)

async function loadOptions() {
	loadingOptions.value = true
	try {
		const options = (await Api.alerts.getAlertsFilters()).data
		sources.value = options.sources
		tags.value = options.tags
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loadingOptions.value = false
	}
}

// Asset names are too many to download (a large tenant has thousands): searched as typed.
const assetResults = ref<string[]>([])
const { loading: searchingAssets, run } = useLatestRequest()

function searchAssets(term: string | null) {
	return run(
		async signal => {
			assetResults.value = (await Api.alerts.searchAlertAssets(term, signal)).data.assets
		},
		err => message.error(getApiErrorMessage(err as ApiError))
	)
}

const onAssetSearch = useDebounceFn((term: string) => searchAssets(term), 300)

onBeforeMount(loadOptions)
</script>
