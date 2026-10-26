<template>
	<div class="flex flex-col gap-4">
		<n-alert v-if="showNoSourcesWarning" :title="$t('eventSearch.form.noSourcesTitle')" type="warning" closable>
			{{ $t("eventSearch.form.noSourcesText") }}
		</n-alert>

		<div class="@container flex w-full flex-col gap-3">
			<div class="flex flex-col gap-2">
				<div class="flex w-full flex-wrap items-center justify-between gap-2">
					<div class="flex items-center gap-2">
						{{ $t("eventSearch.form.queryLabel") }}
						<p class="text-secondary text-xs">{{ $t("eventSearch.form.autocompleteHint") }}</p>
					</div>
					<div class="flex items-center gap-2">
						<n-select
							v-model:value="selectedCustomerCode"
							data-testid="event-search-customer"
							:placeholder="$t('eventSearch.form.selectCustomer')"
							filterable
							size="tiny"
							:options="customerOptions"
							:render-label="renderCustomerLabel"
							:filter="filterCustomer"
							:consistent-menu-width="false"
							@update:value="onCustomerChange"
						/>

						<n-select
							v-model:value="selectedSourceName"
							data-testid="event-search-source"
							:placeholder="$t('eventSearch.form.selectSource')"
							filterable
							size="tiny"
							:options="eventSourceOptions"
							:disabled="!selectedCustomerCode"
							:loading="loadingEventSources"
							:consistent-menu-width="false"
						/>
					</div>
				</div>

				<n-mention
					v-model:value="query"
					data-testid="event-search-query"
					type="textarea"
					separator=" "
					:autosize="{ minRows: 3, maxRows: 8 }"
					:placeholder="$t('eventSearch.form.queryPlaceholder', { example: QUERY_EXAMPLE })"
					:options="suggestionOptions"
					:prefix="['#']"
					:loading="loadingFieldMappings"
					:render-label
					@select="onMentionSelect"
				>
					<template #empty>
						<n-spin :show="loadingFieldMappings">
							<div class="text-secondary text-xs">{{ $t("eventSearch.form.noFieldMappings") }}</div>
						</n-spin>
					</template>
				</n-mention>
			</div>

			<div class="flex flex-wrap justify-between gap-3">
				<div class="flex flex-wrap items-center gap-3">
					<EventSearchQueries
						:saved="memory.memory.value.saved"
						:recent="memory.memory.value.recent"
						:available="memory.available.value"
						:loading="memory.loading.value"
						:error="memory.error.value"
						:can-save="!!selectedSourceName"
						@restore="restore"
						@save="saveCurrent"
						@delete="removeSaved"
						@clear-recent="clearRecent"
						@retry="memory.reload"
					/>
					<span v-if="!selectedCustomerCode || !selectedSourceName" class="text-secondary text-xs">
						{{
							!selectedCustomerCode ? $t("eventSearch.form.customerNeeded") : $t("eventSearch.form.sourceNeeded")
						}}
					</span>
				</div>

				<div class="flex flex-wrap items-center justify-end gap-3">
					<n-input-group class="flex flex-1 items-center justify-end">
						<n-input-number
							v-if="timerangeMode === 'relative'"
							v-model:value="filterTimeRange.time"
							:show-button="false"
							:min="1"
							size="small"
							:placeholder="$t('eventSearch.form.time')"
							class="max-w-15! min-w-10! text-center"
						/>
						<n-select
							v-if="timerangeMode === 'relative'"
							v-model:value="filterTimeRange.unit"
							:options="unitOptions"
							class="max-w-25!"
							:placeholder="$t('eventSearch.form.timeUnit')"
							:consistent-menu-width="false"
							size="small"
						/>
						<n-date-picker
							v-if="timerangeMode === 'absolute'"
							v-model:value="daterange"
							type="datetimerange"
							class="min-w-70"
							clearable
							size="small"
						/>
						<n-button
							v-if="timerangeMode === 'relative'"
							secondary
							size="small"
							@click="timerangeMode = 'absolute'"
						>
							<template #icon>
								<Icon name="carbon:calendar" />
							</template>
						</n-button>
						<n-button
							v-if="timerangeMode === 'absolute'"
							secondary
							size="small"
							@click="timerangeMode = 'relative'"
						>
							<template #icon>
								<Icon name="carbon:reset" />
							</template>
						</n-button>
					</n-input-group>

					<n-select v-model:value="pageSize" :options="pageSizeOptions" size="small" class="w-33!" />

					<n-button
						secondary
						size="small"
						type="primary"
						:loading="loadingEvents"
						:disabled="!selectedCustomerCode || !selectedSourceName"
						data-testid="event-search-submit"
						@click="searchEvents"
					>
						<template #icon>
							<Icon name="carbon:search" />
						</template>
						{{ $t("common.actions.search") }}
					</n-button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { MentionOption } from "naive-ui"
import type { VNodeChild } from "vue"
import type { ApiError } from "@/types/common"
import type { EventSearchQueryTimerange, EventSearchState, EventSourceItem, FieldMapping } from "@/types/siem"
import { NAlert, NButton, NDatePicker, NInputGroup, NInputNumber, NMention, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, h, nextTick, onBeforeMount, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useCustomerPrefill } from "@/composables/common/useCustomerPrefill"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import EventSearchQueries from "./EventSearchQueries.vue"
import { useEventSearchMemory } from "./useEventSearchMemory"

export interface SearchFormParams {
	customerCode: string
	sourceName: string | null
	query: string
	timerange: EventSearchQueryTimerange
	timeFrom: number | null
	timeTo: number | null
	timeMode: "relative" | "absolute"
	pageSize: number
}

export interface SearchFormLoad {
	customerCode: string
	eventSources: EventSourceItem[]
}

defineProps<{
	loadingEvents: boolean
}>()

const emit = defineEmits<{
	(e: "search", value: SearchFormParams): void
	(e: "loaded", value: SearchFormLoad): void
	/** The selected source's field list, for the column picker. */
	(e: "fields", value: FieldMapping[]): void
}>()

const query = defineModel<string>("query")

const TRAILING_WHITESPACE_RE = /\s$/
/** A Lucene query, shown as an example: the same in every language. */
const QUERY_EXAMPLE = "agent_name:web-server AND rule_level:>=10"

const route = useRoute()
const customerFilterStore = useCustomerFilterStore()
const message = useMessage()
const { t } = useI18n()

const { customerOptions, filterCustomer, renderCustomerLabel, initialCustomerCode } = useCustomerPrefill()
// Seeded by the same rule as the case and report forms: the global filter when it
// resolves to one customer, else the user's only customer, else the user chooses.
// (It used to fall back to the token's first code, an arbitrary one.)
const selectedCustomerCode = ref<string | null>(initialCustomerCode())

const eventSources = ref<EventSourceItem[]>([])
const loadingEventSources = ref(false)
const selectedSourceName = ref<string | null>(null)
const enabledSources = computed(() => eventSources.value.filter(s => s.enabled))
const eventSourceOptions = computed(() =>
	enabledSources.value.map(s => ({ label: `${s.name} (${s.event_type})`, value: s.name }))
)

const showNoSourcesWarning = computed(
	() => selectedCustomerCode.value && !loadingEventSources.value && eventSources.value.length === 0
)

const filterTimeRange = ref<{ unit: "h" | "d" | "w"; time: number }>({
	unit: "h",
	time: 24
})
const unitOptions = computed<{ label: string; value: "h" | "d" | "w" }[]>(() => [
	{ label: t("eventSearch.form.units.hours"), value: "h" },
	{ label: t("eventSearch.form.units.days"), value: "d" },
	{ label: t("eventSearch.form.units.weeks"), value: "w" }
])
const timerange = computed<EventSearchQueryTimerange>(
	() => `${filterTimeRange.value.time}${filterTimeRange.value.unit}`
)
const daterange = ref<[number, number]>([dayjs().subtract(1, "day").valueOf(), Date.now()])
const timerangeMode = ref<"relative" | "absolute">("relative")

const PAGE_SIZES = [25, 50, 100, 250]
const pageSizeOptions = computed(() =>
	PAGE_SIZES.map(size => ({ label: t("eventSearch.form.perPage", { count: size }), value: size }))
)
const pageSize = ref(50)

const loadingFieldMappings = ref(false)
const fieldMappings = ref<FieldMapping[]>([])
const suggestionOptions = computed(() => {
	return fieldMappings.value.map(f => ({ label: f.field, type: f.type, value: f.field }))
})

function renderLabel(option: MentionOption): VNodeChild {
	const label = String(option.label ?? "")
	const type = String(option.type ?? "")

	return h("div", { class: "flex items-center gap-2 justify-between w-full" }, [
		h("div", { class: "text-sm font-medium" }, label),
		h("div", { class: "text-xs text-secondary" }, type)
	])
}

async function loadEventSources(customerCode: string) {
	loadingEventSources.value = true
	eventSources.value = []
	selectedSourceName.value = null
	fieldMappings.value = []

	try {
		const response = await Api.siem.getEventSources(customerCode)
		eventSources.value = response.data.event_sources
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || t("eventSearch.form.loadSourcesFailed"))
	} finally {
		loadingEventSources.value = false

		emit("loaded", {
			customerCode,
			eventSources: eventSources.value
		})
	}
}

function onCustomerChange(code: string) {
	// Reload event sources for the newly selected customer (resets source + fields).
	if (code) {
		loadEventSources(code)
	}
}

async function loadFieldMappings() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return

	loadingFieldMappings.value = true
	fieldMappings.value = []
	try {
		const response = await Api.siem.getFieldMappings(selectedCustomerCode.value, selectedSourceName.value)
		fieldMappings.value = response.data.fields
	} catch {
		fieldMappings.value = []
	} finally {
		loadingFieldMappings.value = false
		emit("fields", fieldMappings.value)
	}
}

// -- Saved and recent searches (#1258) --
const memory = useEventSearchMemory(selectedCustomerCode)

/** The search on screen, as it is remembered. */
function currentState(): EventSearchState | null {
	if (!selectedSourceName.value) return null
	const absolute = timerangeMode.value === "absolute"
	return {
		source_name: selectedSourceName.value,
		query: (query.value || "").trim(),
		time_mode: timerangeMode.value,
		time_amount: filterTimeRange.value.time,
		time_unit: filterTimeRange.value.unit,
		time_from: absolute ? new Date(daterange.value[0]).toISOString() : null,
		time_to: absolute ? new Date(daterange.value[1]).toISOString() : null,
		page_size: pageSize.value
	}
}

async function saveCurrent(name: string) {
	const state = currentState()
	if (!state) return
	try {
		const replaced = await memory.save(name, state)
		message.success(
			replaced
				? t("eventSearch.form.queryUpdated", { name: name.trim() })
				: t("eventSearch.form.querySaved", { name: name.trim() })
		)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || t("eventSearch.form.saveQueryFailed"))
	}
}

async function removeSaved(id: number) {
	try {
		await memory.remove(id)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || t("eventSearch.form.deleteQueryFailed"))
	}
}

async function clearRecent() {
	try {
		await memory.clearRecent()
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || t("eventSearch.form.clearRecentFailed"))
	}
}

/** Puts a remembered search back on the form and runs it, if its source is still there. */
async function restore(state: EventSearchState) {
	if (!enabledSources.value.some(s => s.name === state.source_name)) {
		message.warning(t("eventSearch.form.sourceGone", { source: state.source_name }))
		return
	}
	selectedSourceName.value = state.source_name
	query.value = state.query
	timerangeMode.value = state.time_mode
	filterTimeRange.value = { time: state.time_amount, unit: state.time_unit }
	if (state.time_mode === "absolute" && state.time_from && state.time_to) {
		daterange.value = [Date.parse(state.time_from), Date.parse(state.time_to)]
	}
	if (PAGE_SIZES.includes(state.page_size)) pageSize.value = state.page_size
	// `query` is the parent's model: it reads the new text only once the parent has rendered.
	await nextTick()
	searchEvents()
}

async function searchEvents() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return

	const state = currentState()
	if (state) memory.remember(state)

	emit("search", {
		customerCode: selectedCustomerCode.value,
		sourceName: selectedSourceName.value,
		query: query.value || "",
		timerange: timerange.value,
		timeFrom: timerangeMode.value === "absolute" ? daterange.value[0] : null,
		timeTo: timerangeMode.value === "absolute" ? daterange.value[1] : null,
		timeMode: timerangeMode.value,
		pageSize: pageSize.value
	})
}

function onMentionSelect(option: MentionOption, prefix: string) {
	// Current query text and the raw token as typed in the mention (e.g. "#field")
	const currentQuery = query.value || ""
	const target = `${prefix}${option.value}`

	// Find the last occurrence of the typed token to replace it
	const lastIndex = currentQuery.lastIndexOf(target)

	if (lastIndex === -1) {
		// If only the trigger is present (e.g. "... #"), replace the last trigger with "field:"
		const lastPrefixIndex = currentQuery.lastIndexOf(prefix)
		if (lastPrefixIndex !== -1) {
			const before = currentQuery.slice(0, lastPrefixIndex)
			const after = currentQuery.slice(lastPrefixIndex + prefix.length)
			const needsSpace = before.length > 0 && !TRAILING_WHITESPACE_RE.test(before)
			const replacement = `${needsSpace ? " " : ""}${option.value}:`
			query.value = `${before}${replacement}${after}`
			return
		}

		// If neither token nor trigger is found, append the field followed by ":" at the end of the query
		const needsSpace = currentQuery.length > 0 && !TRAILING_WHITESPACE_RE.test(currentQuery)
		query.value = `${currentQuery}${needsSpace ? " " : ""}${option.value}:`
		return
	}

	// Split query around the matched token
	const before = currentQuery.slice(0, lastIndex)
	const after = currentQuery.slice(lastIndex + target.length)

	// Rebuild query replacing the token with the plain field name followed by ":"
	const needsSpace = before.length > 0 && !TRAILING_WHITESPACE_RE.test(before)
	const replacement = `${needsSpace ? " " : ""}${option.value}:`

	query.value = `${before}${replacement}${after}`
}

// -- Lifecycle --
async function applyRouteParams() {
	const qCustomer = (route.query.customer_code as string | undefined) || selectedCustomerCode.value
	const qSource = route.query.source_name as string | undefined
	const qQuery = route.query.query as string | undefined

	if (!qCustomer) return

	selectedCustomerCode.value = qCustomer
	await loadEventSources(qCustomer)

	if (qSource) {
		const match = enabledSources.value.find(s => s.name === qSource)
		if (match) {
			selectedSourceName.value = match.name
		}
	}

	if (qQuery) {
		query.value = qQuery
	}

	if (selectedCustomerCode.value && selectedSourceName.value) {
		searchEvents()
	}
}

watch(
	selectedSourceName,
	val => {
		if (val) {
			loadFieldMappings()
		}
	},
	{ immediate: true }
)

// Follow the global customer filter when it narrows to a single customer. The store
// replaces the selection on every change, so no deep watch is needed.
watch(
	() => customerFilterStore.selectedCustomerCodes,
	codes => {
		const [only] = codes
		if (codes.length === 1 && only && only !== selectedCustomerCode.value) {
			selectedCustomerCode.value = only
			loadEventSources(only)
		}
	}
)

onBeforeMount(() => {
	applyRouteParams()
})
</script>
