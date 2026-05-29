<template>
	<div class="flex flex-col gap-4">
		<n-alert v-if="showNoSourcesWarning" title="No Event Sources Configured" type="warning" closable>
			No event sources are configured for this customer. Contact your administrator to set up event sources.
		</n-alert>

		<div class="@container flex w-full flex-col gap-3">
			<div class="flex flex-col gap-2">
				<div class="flex w-full flex-wrap items-center justify-between gap-2">
					<div class="flex items-center gap-2">
						Lucene Query
						<p class="text-secondary text-xs">type # to autocomplete</p>
					</div>
					<div class="flex items-center gap-2">
						<n-select
							v-model:value="selectedCustomerCode"
							placeholder="Select Customer"
							filterable
							size="tiny"
							:options="customersOptions"
							:consistent-menu-width="false"
							@update:value="onCustomerChange"
						/>

						<n-select
							v-model:value="selectedSourceName"
							placeholder="Select Source"
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
					:disabled="!selectedCustomerCode || !selectedSourceName"
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
</template>

<script setup lang="ts">
import type { MentionOption } from "naive-ui"
import type { VNodeChild } from "vue"
import type { ApiError } from "@/types/common"
import type { EventSearchQueryTimerange, EventSourceItem, FieldMapping } from "@/types/siem"
import { NAlert, NButton, NDatePicker, NInputGroup, NInputNumber, NMention, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, ref, watch } from "vue"
import { useRoute } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"

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
}>()

const query = defineModel<string>("query")

const TRAILING_WHITESPACE_RE = /\s$/

const route = useRoute()
const authStore = useAuthStore()
const customerFilterStore = useCustomerFilterStore()
const message = useMessage()

const customerCode = computed(() => authStore.userCustomerCode)
const customersOptions = computed(() => authStore.accessibleCustomerCodes.map(code => ({ label: code, value: code })))
// Seed the searched customer from the global filter when it resolves to a single
// customer, otherwise the user's primary / first accessible customer.
const selectedCustomerCode = ref(
	customerFilterStore.selectedCustomerCodes.length === 1
		? customerFilterStore.selectedCustomerCodes[0]
		: customerCode.value || authStore.accessibleCustomerCodes[0] || ""
)

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
const pageSize = ref(pageSizeOptions[1].value)

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
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load event sources")
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
	}
}

async function searchEvents() {
	if (!selectedCustomerCode.value || !selectedSourceName.value) return

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
	const qCustomer = (route.query.customer_code || selectedCustomerCode.value) as string
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

// Follow the global customer filter when it narrows to a single customer.
watch(
	() => customerFilterStore.selectedCustomerCodes,
	codes => {
		if (codes.length === 1 && codes[0] !== selectedCustomerCode.value) {
			selectedCustomerCode.value = codes[0]
			loadEventSources(codes[0])
		}
	},
	{ deep: true }
)

onBeforeMount(() => {
	applyRouteParams()
})
</script>
