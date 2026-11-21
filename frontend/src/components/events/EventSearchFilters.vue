<template>
	<div class="flex flex-col gap-4">
		<n-alert v-if="showNoSourcesWarning" title="No Event Sources Configured" type="warning" closable>
			An Event Source needs to be defined for this customer before events can be searched. Go to the customer's
			<strong>Event Sources</strong>
			tab to configure one.
		</n-alert>

		<div class="@container flex w-full flex-col gap-3">
			<div class="flex flex-col gap-2">
				<div class="flex w-full flex-wrap items-center justify-between gap-2">
					<div class="flex items-center gap-2">
						Lucene Query
						<p class="text-secondary text-xs">type # to autocomplete</p>
					</div>
					<div class="flex flex-wrap items-center gap-2 @md:flex-nowrap">
						<n-select
							v-model:value="selectedCustomerCode"
							placeholder="Select Customer"
							filterable
							size="tiny"
							:options="customersOptions"
							:loading="loadingCustomers"
							:consistent-menu-width="false"
							@update:value="onCustomerChange"
						/>

						<n-select
							v-model:value="selectedSourceNames"
							multiple
							clearable
							placeholder="Select Sources"
							filterable
							size="tiny"
							max-tag-count="responsive"
							class="w-64! shrink-0 @3xl:w-80!"
							:options="eventSourceOptions"
							:render-tag="renderSourceTag"
							:disabled="!selectedCustomerCode"
							:loading="loadingEventSources"
							:consistent-menu-width="false"
						>
							<template #action>
								<p class="text-secondary text-xs">
									Pick up to {{ MAX_SOURCES }} sources to search them together, newest first.
								</p>
							</template>
						</n-select>
					</div>
				</div>

				<n-mention
					v-model:value="query"
					type="textarea"
					separator=" "
					:autosize="{ minRows: 3, maxRows: 8 }"
					placeholder="e.g. agent_name:web-server AND rule_level:>=10"
					:options="suggestionOptions"
					:prefix="['#']"
					:loading="loadingFieldMappings"
					:render-label
					@select="onMentionSelect"
				>
					<template #empty>
						<n-spin :show="loadingFieldMappings">
							<div class="text-secondary text-xs">No field mappings found</div>
						</n-spin>
					</template>
				</n-mention>

				<n-alert v-if="timeFieldProblem" type="warning" :bordered="false" class="text-sm">
					These sources use different time fields ({{ timeFieldProblem }}), so they can't be searched together.
					Search them one at a time.
				</n-alert>
				<n-alert v-else-if="conflictingFields.length" type="warning" :bordered="false" class="text-sm">
					<template v-for="(mapping, index) in conflictingFields" :key="mapping.field">
						<template v-if="index > 0">{{ index === conflictingFields.length - 1 ? " and " : ", " }}</template>
						<code class="font-mono">{{ mapping.field }}</code>
						<span class="text-secondary">({{ mapping.type }})</span>
					</template>
					{{ conflictingFields.length === 1 ? "has" : "have" }} a different type in some of these sources. The
					query can miss events from the sources where the type is different, without an error.
				</n-alert>
			</div>
			<div class="flex flex-wrap justify-between gap-3">
				<div class="text-secondary text-xs">
					{{
						!selectedCustomerCode
							? "Select a customer to search"
							: !selectedSourceNames.length
								? "Select a source to search"
								: ""
					}}
				</div>

				<div class="flex flex-wrap items-center justify-end gap-3">
					<n-input-group class="flex flex-1 items-center justify-end">
						<n-input-number
							v-if="timerangeMode === 'relative'"
							v-model:value="filterTimeRange.time"
							:show-button="false"
							:min="1"
							size="small"
							placeholder="Time"
							class="max-w-15! min-w-10! text-center"
						/>
						<n-select
							v-if="timerangeMode === 'relative'"
							v-model:value="filterTimeRange.unit"
							:options="unitOptions"
							class="max-w-25!"
							placeholder="Time unit"
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
						:disabled="!canSearch"
						@click="searchEvents"
					>
						<template #icon>
							<Icon name="carbon:search" />
						</template>
						Search
					</n-button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { MentionOption, SelectRenderTag } from "naive-ui"
import type { VNodeChild } from "vue"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { EventSource } from "@/types/event-sources"
import type { FieldMapping } from "@/types/events"
import {
	NAlert,
	NButton,
	NDatePicker,
	NInputGroup,
	NInputNumber,
	NMention,
	NSelect,
	NSpin,
	NTag,
	useMessage
} from "naive-ui"
import { computed, h, onBeforeMount, ref, watch } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"
import {
	conflictingFieldsInQuery,
	MAX_SOURCES,
	resolveSourceForIndex,
	routeSourceNames,
	timeFieldMismatch
} from "./eventSearch.helpers"

export type EventSearchQueryTimerange = `${number}${"h" | "d" | "w"}`

export interface EventSearchFiltersParams {
	customerCode: string
	/** One source, or up to `MAX_SOURCES` searched together. */
	sourceNames: string[]
	query: string
	timerange: EventSearchQueryTimerange
	timeFrom: number | null
	timeTo: number | null
	timeMode: "relative" | "absolute"
	pageSize: number
	fieldMappings: FieldMapping[]
}

export interface EventSearchFiltersLoad {
	customerCode: string
	eventSources: EventSource[]
}

defineProps<{
	loadingEvents: boolean
}>()

const emit = defineEmits<{
	search: [params: EventSearchFiltersParams]
	loaded: [load: EventSearchFiltersLoad]
	"field-mappings": [mappings: FieldMapping[]]
	"field-mappings-loading": [loading: boolean]
}>()

const query = defineModel<string>("query", { default: "" })

const TRAILING_WHITESPACE_RE = /\s$/

const route = useRoute()
const message = useMessage()
const { globalCustomerCode, onGlobalCustomerFilterChange } = useGlobalCustomerFilter()

const filterTimeRange = ref<{ unit: "h" | "d" | "w"; time: number }>({
	unit: "h",
	time: 24
})
const unitOptions: { label: string; value: "h" | "d" | "w" }[] = [
	{ label: "Hours", value: "h" },
	{ label: "Days", value: "d" },
	{ label: "Weeks", value: "w" }
]
const timerange = computed<EventSearchQueryTimerange>(
	() => `${filterTimeRange.value.time}${filterTimeRange.value.unit}`
)
const daterange = ref<[number, number]>([dayjs().subtract(1, "day").valueOf(), Date.now()])
const timerangeMode = ref<"relative" | "absolute">("relative")

const pageSizeOptions = [
	{ label: "25 per page", value: 25 },
	{ label: "50 per page", value: 50 },
	{ label: "100 per page", value: 100 },
	{ label: "250 per page", value: 250 }
]

const loadingCustomers = ref(false)
const customersList = ref<Customer[]>([])
const loadingEventSources = ref(false)
const eventSources = ref<EventSource[]>([])
const selectedCustomerCode = ref<string | null>(null)
const selectedSourceNames = ref<string[]>([])
const pageSize = ref(pageSizeOptions[1].value)
const loadingFieldMappings = ref(false)
const fieldMappings = ref<FieldMapping[]>([])

const customersOptions = computed(() =>
	customersList.value.map(o => ({ label: `#${o.customer_code} - ${o.customer_name}`, value: o.customer_code }))
)

const eventSourceOptions = computed(() => {
	const full = selectedSourceNames.value.length >= MAX_SOURCES
	return eventSources.value
		.filter(s => s.enabled)
		.map(s => ({
			label: `${s.name} (${s.event_type})`,
			value: s.name,
			disabled: full && !selectedSourceNames.value.includes(s.name)
		}))
})

/** The selected sources, in the order they were picked. */
const selectedSources = computed(() =>
	selectedSourceNames.value
		.map(name => eventSources.value.find(s => s.name === name))
		.filter((s): s is EventSource => s !== undefined)
)

const timeFieldProblem = computed(() => timeFieldMismatch(selectedSources.value))

const canSearch = computed(
	() => !!selectedCustomerCode.value && selectedSourceNames.value.length > 0 && !timeFieldProblem.value
)

/** Only one source's fields are all of one type per field; several sources' can differ. */
const conflictingFields = computed(() =>
	selectedSourceNames.value.length > 1 ? conflictingFieldsInQuery(query.value || "", fieldMappings.value) : []
)

const showNoSourcesWarning = computed(
	() => selectedCustomerCode.value && !loadingEventSources.value && eventSources.value.length === 0
)

const suggestionOptions = computed(() =>
	fieldMappings.value.map(f => ({ label: f.field, type: f.type, conflict: !!f.conflict, value: f.field }))
)

/** A selected source reads as its name alone (the menu also names its type), so several fit. */
const renderSourceTag: SelectRenderTag = ({ option, handleClose }) =>
	h(
		NTag,
		{
			size: "tiny",
			closable: true,
			title: String(option.label ?? option.value),
			onMousedown: (e: MouseEvent) => e.preventDefault(),
			onClose: (e: MouseEvent) => {
				e.stopPropagation()
				handleClose()
			}
		},
		{ default: () => String(option.value) }
	)

function renderLabel(option: MentionOption): VNodeChild {
	const label = String(option.label ?? "")
	const type = String(option.type ?? "")
	const conflict = option.conflict === true

	return h("div", { class: "flex w-full items-center justify-between gap-2" }, [
		h("div", { class: "text-sm font-medium font-mono" }, label),
		h(
			"div",
			{ class: conflict ? "text-warning text-xs" : "text-secondary text-xs" },
			conflict ? `${type} (differs by source)` : type
		)
	])
}

function getCustomers() {
	loadingCustomers.value = true
	return Api.customers
		.getCustomers({})
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCustomers.value = false
		})
}

function getEventSources(customerCode: string) {
	loadingEventSources.value = true
	eventSources.value = []
	selectedSourceNames.value = []
	fieldMappings.value = []
	emit("field-mappings-loading", false)
	emit("field-mappings", [])

	return Api.siem
		.getEventSources(customerCode)
		.then(res => {
			if (res.data.success) {
				eventSources.value = res.data?.event_sources || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingEventSources.value = false
			emit("loaded", { customerCode, eventSources: eventSources.value })
		})
}

let fieldMappingsController: AbortController | null = null

/**
 * The fields of the selected sources: one source's from its own route, several sources' from
 * the route that reads them together and marks a field their indices type differently. A
 * selection changed while a load runs cancels it, so only the newest selection's fields land.
 */
async function loadFieldMappings() {
	fieldMappingsController?.abort()
	const controller = new AbortController()
	fieldMappingsController = controller

	const customerCode = selectedCustomerCode.value
	const names = [...selectedSourceNames.value]
	fieldMappings.value = []
	emit("field-mappings", [])

	if (!customerCode || !names.length) {
		loadingFieldMappings.value = false
		emit("field-mappings-loading", false)
		return
	}

	loadingFieldMappings.value = true
	emit("field-mappings-loading", true)

	let fields: FieldMapping[] = []
	try {
		const res =
			names.length === 1
				? await Api.siem.getFieldMappings(customerCode, names[0], controller.signal)
				: await Api.siem.getFieldMappingsMulti(customerCode, names, controller.signal)
		if (res.data.success) {
			fields = res.data.fields || []
		}
	} catch {
		fields = []
	}

	if (fieldMappingsController !== controller) return

	fieldMappings.value = fields
	loadingFieldMappings.value = false
	emit("field-mappings-loading", false)
	emit("field-mappings", fields)
}

function onCustomerChange(code: string) {
	if (code) {
		getEventSources(code)
	}
}

function searchEvents() {
	if (!canSearch.value || !selectedCustomerCode.value) return

	emit("search", {
		customerCode: selectedCustomerCode.value,
		sourceNames: [...selectedSourceNames.value],
		query: query.value || "",
		timerange: timerange.value,
		timeFrom: timerangeMode.value === "absolute" ? daterange.value[0] : null,
		timeTo: timerangeMode.value === "absolute" ? daterange.value[1] : null,
		timeMode: timerangeMode.value,
		pageSize: pageSize.value,
		fieldMappings: fieldMappings.value
	})
}

function onMentionSelect(option: MentionOption, prefix: string) {
	const currentQuery = query.value || ""
	const target = `${prefix}${option.value}`
	const lastIndex = currentQuery.lastIndexOf(target)

	if (lastIndex === -1) {
		const lastPrefixIndex = currentQuery.lastIndexOf(prefix)
		if (lastPrefixIndex !== -1) {
			const before = currentQuery.slice(0, lastPrefixIndex)
			const after = currentQuery.slice(lastPrefixIndex + prefix.length)
			const needsSpace = before.length > 0 && !TRAILING_WHITESPACE_RE.test(before)
			const replacement = `${needsSpace ? " " : ""}${option.value}:`
			query.value = `${before}${replacement}${after}`
			return
		}

		const needsSpace = currentQuery.length > 0 && !TRAILING_WHITESPACE_RE.test(currentQuery)
		query.value = `${currentQuery}${needsSpace ? " " : ""}${option.value}:`
		return
	}

	const before = currentQuery.slice(0, lastIndex)
	const after = currentQuery.slice(lastIndex + target.length)
	const needsSpace = before.length > 0 && !TRAILING_WHITESPACE_RE.test(before)
	const replacement = `${needsSpace ? " " : ""}${option.value}:`

	query.value = `${before}${replacement}${after}`
}

async function applyRouteParams() {
	const qp = route.query
	if (!qp.customer_code) return

	const code = String(qp.customer_code)
	selectedCustomerCode.value = code

	if (qp.query) {
		query.value = String(qp.query)
	}

	await getEventSources(code)

	// Explicitly named sources (`source_name`, repeated for several) are taken at their word:
	// the ones that exist and are enabled are selected, and if any is gone, disabled or past
	// the limit nothing runs, rather than quietly searching a different set than the link
	// names. `index_name` is the softer form — a caller that holds an index but not a source
	// name — so an index nothing claims falls through to the default below.
	const named = routeSourceNames(qp.source_name)
	if (named.length) {
		const found = named
			.slice(0, MAX_SOURCES)
			.filter(name => eventSources.value.some(s => s.name === name && s.enabled))
		selectedSourceNames.value = found

		if (named.length > MAX_SOURCES) {
			message.warning(`Event Search covers up to ${MAX_SOURCES} sources at once: pick the ones to search.`)
			return
		}
		const missing = named.filter(name => !found.includes(name))
		if (missing.length) {
			message.warning(`Not found or disabled for ${code}: ${missing.join(", ")}`)
			return
		}
	} else {
		const indexName = qp.index_name ? String(qp.index_name) : null
		const resolved = indexName ? resolveSourceForIndex(indexName, eventSources.value) : null

		if (resolved) {
			selectedSourceNames.value = [resolved.name]
		} else {
			const edr = eventSources.value.find(s => s.event_type === "EDR" && s.enabled)
			if (edr) {
				selectedSourceNames.value = [edr.name]
			}
		}
	}

	if (selectedSourceNames.value.length) {
		searchEvents()
	}
}

// Every change of selection reloads the fields, an emptied one included (which clears them).
watch(selectedSourceNames, () => loadFieldMappings(), { deep: true })

onBeforeMount(() => {
	getCustomers().then(() => {
		if (!route.query.customer_code) {
			const code = globalCustomerCode.value
			if (code) {
				selectedCustomerCode.value = code
				getEventSources(code)
			}
		}
		applyRouteParams()
	})
})

// An emptied global selection keeps the current customer — a search needs one to run at all.
onGlobalCustomerFilterChange(codes => {
	const code = codes[0] || null

	if (code && code !== selectedCustomerCode.value) {
		selectedCustomerCode.value = code
		onCustomerChange(code)
	}
})
</script>
